"""PySide6 tuning-panel mockup for AutoZuma Next."""

from __future__ import annotations

import sys
from collections import defaultdict

from autozuma.gui.controller import GuiRuntimeController, GuiRuntimeSettings
from autozuma.gui.schema import (
    GuiParameterDefinition,
    GuiParameterKind,
    GuiParameterMode,
    build_gui_parameter_schema,
)
from autozuma.gui.i18n import SUPPORTED_LANGUAGES, translate
from autozuma.gui.settings import (
    GuiHotkeySettings,
    GuiSettings,
    load_gui_settings,
    save_gui_settings,
)
from autozuma.control.hotkeys import HotkeyControlState, Win32HotkeyReader, poll_hotkeys
from autozuma.runtime.config import DEFAULT_RUNTIME_VALUES, load_runtime_values, save_runtime_values_to_ini


def main(argv: list[str] | None = None) -> int:
    """Launch the disconnected GUI shell."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        raise SystemExit(
            "AutoZuma GUI requires PySide6. Install the gui extra, for example: "
            "pip install -e .[gui]"
        ) from exc

    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    app.setStyle("Fusion")
    window = AutoZumaGuiWindow()
    window.show()
    return app.exec()


class AutoZumaGuiWindow:
    """Create a compact tuning-first PySide window lazily."""

    def __new__(cls):
        from PySide6.QtCore import QTimer, Qt
        from PySide6.QtGui import QFont, QImage, QKeySequence, QPixmap, QShortcut
        from PySide6.QtWidgets import (
            QCheckBox,
            QComboBox,
            QDoubleSpinBox,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QFileDialog,
            QMainWindow,
            QPushButton,
            QKeySequenceEdit,
            QScrollArea,
            QSizePolicy,
            QSpinBox,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )

        class _Window(QMainWindow):
            def __init__(self) -> None:
                super().__init__()
                self.setWindowTitle("AutoZuma Next")
                self.resize(1180, 780)
                self.setMinimumSize(980, 680)
                self.setStyleSheet(_STYLE)
                self.controller = GuiRuntimeController()
                self.runtime_values = load_runtime_values()
                self.gui_settings = load_gui_settings()
                self.language = self.gui_settings.language
                self.parameter_controls: dict[str, QWidget] = {}
                self.hotkey_controls: dict[str, QKeySequenceEdit] = {}
                self.shortcuts: dict[str, QShortcut] = {}
                self.status_values: dict[str, QLabel] = {}
                self.execution_toggle: QCheckBox | None = None
                self.preview_label: QLabel | None = None
                self.language_selector: QComboBox | None = None
                self.hotkey_state = HotkeyControlState()
                self.hotkey_reader = Win32HotkeyReader()
                self.localized_widgets: dict[str, list[QWidget]] = defaultdict(list)
                self.localized_tabs: list[tuple[QTabWidget, int, str]] = []
                self.log_label: QLabel | None = None
                self.log_lines: list[str] = []
                self.timer = QTimer(self)
                self.timer.setInterval(100)
                self.timer.timeout.connect(self._tick)
                self.hotkey_timer = QTimer(self)
                self.hotkey_timer.setInterval(50)
                self.hotkey_timer.timeout.connect(self._poll_global_hotkeys)

                schema = build_gui_parameter_schema(self.runtime_values)

                root = QWidget()
                layout = QVBoxLayout(root)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)
                layout.addWidget(_title_bar(self))
                layout.addWidget(_main_area(self, schema), 1)
                self.setCentralWidget(root)
                self._retranslate()
                self._sync_execution_mode()
                self._install_shortcuts()
                self.hotkey_timer.start()
                self._append_log("GUI connected in dry-run mode")

            def _t(self, key: str) -> str:
                return translate(self.language, key)

            def _localized_label(self, key: str, object_name: str | None = None) -> QLabel:
                label = QLabel()
                if object_name is not None:
                    label.setObjectName(object_name)
                self.localized_widgets[key].append(label)
                return label

            def _localized_button(self, key: str, object_name: str) -> QPushButton:
                button = QPushButton()
                button.setObjectName(object_name)
                self.localized_widgets[key].append(button)
                return button

            def _set_language(self, language: str) -> None:
                if language in SUPPORTED_LANGUAGES:
                    self.language = language
                    self._retranslate()
                    self._save_gui_settings()

            def _retranslate(self) -> None:
                self.setWindowTitle(self._t("app_title"))
                for key, widgets in self.localized_widgets.items():
                    for widget in widgets:
                        widget.setText(self._t(key))
                for tabs, index, key in self.localized_tabs:
                    tabs.setTabText(index, self._t(key))
                self._sync_execution_mode()
                if self.log_label is not None and not self.log_lines:
                    self.log_label.setText(
                        "16:55:03  "
                        + self._t("log_config_loaded")
                        + "\n16:55:03  "
                        + self._t("log_gui_idle")
                        + "\n16:55:03  "
                        + self._t("log_disconnected")
                    )

            def _arm(self) -> None:
                self.controller.arm()
                self.timer.start()
                self._set_status("state", "armed")
                self._append_log(f"armed live loop ({self._execution_mode_text()})")

            def _toggle_arm(self) -> None:
                if self.controller.is_armed:
                    self._safe()
                else:
                    self._arm()

            def _safe(self) -> None:
                self.timer.stop()
                self.controller.safe()
                self._set_status("state", "safe")
                self._append_log("safe")

            def _snapshot(self) -> None:
                self._run_step(debug_snapshot=True)

            def _poll_global_hotkeys(self) -> None:
                try:
                    poll_result = poll_hotkeys(self.hotkey_state, self.hotkey_reader)
                except Exception as exc:  # noqa: BLE001 - GUI boundary reports hotkey failures.
                    self.hotkey_timer.stop()
                    self._append_log(f"global hotkeys unavailable: {exc}")
                    return

                self.hotkey_state = poll_result.state
                if poll_result.events.toggled_arm:
                    self._toggle_arm()
                if poll_result.events.debug_requested:
                    self._snapshot()
                if poll_result.events.forced_safe:
                    self._safe()

            def _tick(self) -> None:
                self._run_step(debug_snapshot=False)

            def _run_step(self, *, debug_snapshot: bool) -> None:
                try:
                    result = self.controller.step(
                        self._settings(),
                        debug_snapshot=debug_snapshot,
                    )
                except Exception as exc:  # noqa: BLE001 - GUI boundary reports runtime failures.
                    self._append_log(f"error: {exc}")
                    return

                self._set_status("level", result.level_id or "none")
                self._set_status("command", result.command_type)
                self._set_status("mode", result.mode or "detecting")
                if result.preview_bgr is not None:
                    self._set_preview(result.preview_bgr)
                dispatch = (
                    f"executed/{result.mouse_mode}"
                    if result.commands_enabled and result.command_type.lower() != "no_op"
                    else "planned"
                )
                self._append_log(f"{result.message}: {result.command_type} ({dispatch})")

            def _settings(self) -> GuiRuntimeSettings:
                return GuiRuntimeSettings(
                    raw_values=self._current_values(),
                    execute_commands=self._execution_enabled(),
                )

            def _execution_enabled(self) -> bool:
                return bool(self.execution_toggle is not None and self.execution_toggle.isChecked())

            def _execution_mode_text(self) -> str:
                return "execution enabled" if self._execution_enabled() else "dry-run"

            def _set_execution_enabled(self, enabled: bool) -> None:
                self._sync_execution_mode()
                self._append_log("mouse execution enabled" if enabled else "dry-run mode enabled")

            def _sync_execution_mode(self) -> None:
                label = self.status_values.get("execution_mode")
                if label is None:
                    return
                if self._execution_enabled():
                    label.setText(self._t("execution_enabled"))
                    _set_object_name(label, "DangerPill")
                else:
                    label.setText(self._t("dry_run"))
                    _set_object_name(label, "InfoPill")

            def _current_values(self) -> dict[str, float]:
                values = dict(self.runtime_values)
                for key, control in self.parameter_controls.items():
                    if isinstance(control, QCheckBox):
                        values[key] = 1.0 if control.isChecked() else 0.0
                    elif isinstance(control, (QSpinBox, QDoubleSpinBox)):
                        values[key] = float(control.value())
                return values

            def _load_ini(self) -> None:
                path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Load strategy INI",
                    "config",
                    "INI files (*.ini);;All files (*)",
                )
                if not path:
                    return
                try:
                    self.runtime_values = load_runtime_values(path)
                    self._apply_runtime_values(self.runtime_values)
                    self._append_log(f"loaded ini: {path}")
                except Exception as exc:  # noqa: BLE001 - GUI boundary reports file failures.
                    self._append_log(f"load failed: {exc}")

            def _save_preset(self) -> None:
                path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Save strategy preset",
                    "config/strategy_gui_saved.ini",
                    "INI files (*.ini);;All files (*)",
                )
                if not path:
                    return
                try:
                    save_runtime_values_to_ini(path, self._current_values())
                    self._save_gui_settings()
                    self._append_log(f"saved preset: {path}")
                except Exception as exc:  # noqa: BLE001 - GUI boundary reports file failures.
                    self._append_log(f"save failed: {exc}")

            def _reset_defaults(self) -> None:
                self.runtime_values = dict(DEFAULT_RUNTIME_VALUES)
                self._apply_runtime_values(self.runtime_values)
                self.gui_settings = GuiSettings()
                self.language = self.gui_settings.language
                self._apply_language_setting()
                self._apply_hotkey_settings(self.gui_settings.hotkeys)
                self._save_gui_settings()
                self._append_log("reset defaults")

            def _apply_language_setting(self) -> None:
                if self.language_selector is None:
                    return
                index = self.language_selector.findData(self.language)
                if index >= 0:
                    self.language_selector.blockSignals(True)
                    self.language_selector.setCurrentIndex(index)
                    self.language_selector.blockSignals(False)
                self._retranslate()

            def _apply_runtime_values(self, values: dict[str, float]) -> None:
                for key, value in values.items():
                    control = self.parameter_controls.get(key)
                    if isinstance(control, QCheckBox):
                        control.setChecked(value >= 0.5)
                    elif isinstance(control, (QSpinBox, QDoubleSpinBox)):
                        control.setValue(float(value))

            def _apply_hotkey_settings(self, hotkeys: GuiHotkeySettings) -> None:
                for name, key_sequence in (
                    ("toggle_arm", hotkeys.toggle_arm),
                    ("snapshot", hotkeys.snapshot),
                    ("safe", hotkeys.safe),
                ):
                    control = self.hotkey_controls.get(name)
                    if control is not None:
                        control.setKeySequence(QKeySequence(key_sequence))
                self._install_shortcuts()

            def _save_gui_settings(self) -> None:
                self.gui_settings = GuiSettings(
                    language=self.language,
                    hotkeys=GuiHotkeySettings(
                        toggle_arm=self._hotkey_text("toggle_arm"),
                        snapshot=self._hotkey_text("snapshot"),
                        safe=self._hotkey_text("safe"),
                    )
                )
                save_gui_settings(self.gui_settings)
                self._install_shortcuts()

            def _hotkey_text(self, name: str) -> str:
                control = self.hotkey_controls.get(name)
                if control is None:
                    return getattr(GuiHotkeySettings(), name)
                return control.keySequence().toString() or getattr(GuiHotkeySettings(), name)

            def _install_shortcuts(self) -> None:
                for shortcut in self.shortcuts.values():
                    shortcut.setParent(None)
                self.shortcuts = {}

                for name, callback in (
                    ("toggle_arm", self._toggle_arm),
                    ("snapshot", self._snapshot),
                    ("safe", self._safe),
                ):
                    key_text = self._hotkey_text(name)
                    if key_text.upper() in {"F1", "F2", "F3"}:
                        continue
                    shortcut = QShortcut(QKeySequence(key_text), self)
                    shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
                    shortcut.activated.connect(callback)
                    self.shortcuts[name] = shortcut

            def _set_status(self, key: str, value: str) -> None:
                label = self.status_values.get(key)
                if label is not None:
                    label.setText(value)

            def _set_preview(self, image_bgr) -> None:
                if self.preview_label is None:
                    return
                pixmap = _bgr_to_pixmap(image_bgr)
                target_size = self.preview_label.size()
                if target_size.width() > 0 and target_size.height() > 0:
                    pixmap = pixmap.scaled(
                        target_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                self.preview_label.setPixmap(pixmap)

            def _append_log(self, line: str) -> None:
                self.log_lines.append(line)
                self.log_lines = self.log_lines[-40:]
                if self.log_label is not None:
                    self.log_label.setText("\n".join(self.log_lines))

        def _title_bar(window: _Window) -> QWidget:
            bar = QFrame()
            bar.setObjectName("TitleBar")
            layout = QHBoxLayout(bar)
            layout.setContentsMargins(16, 10, 16, 10)
            layout.setSpacing(10)

            badge = QLabel("AZ")
            badge.setObjectName("Badge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(badge)

            title = window._localized_label("app_title", "AppTitle")
            title.setObjectName("AppTitle")
            layout.addWidget(title)
            layout.addStretch()

            for text, object_name in (
                ("safe", "SafePill"),
                ("config_loaded", "InfoPill"),
            ):
                pill = window._localized_label(text)
                pill.setObjectName(object_name)
                layout.addWidget(pill)

            execution_pill = window._localized_label("dry_run")
            execution_pill.setObjectName("InfoPill")
            window.status_values["execution_mode"] = execution_pill
            layout.addWidget(execution_pill)

            language_label = window._localized_label("language", "Muted")
            layout.addWidget(language_label)
            language = QComboBox()
            language.addItem("English", "en")
            language.addItem("中文", "zh")
            index = language.findData(window.language)
            if index >= 0:
                language.setCurrentIndex(index)
            language.currentIndexChanged.connect(
                lambda: window._set_language(language.currentData())
            )
            window.language_selector = language
            layout.addWidget(language)
            return bar

        def _main_area(window: _Window, schema: tuple[GuiParameterDefinition, ...]) -> QWidget:
            body = QWidget()
            layout = QHBoxLayout(body)
            layout.setContentsMargins(14, 14, 14, 14)
            layout.setSpacing(12)
            layout.addWidget(_left_panel(window))
            layout.addWidget(_parameter_tabs(window, schema), 1)
            layout.addWidget(_right_panel(window))
            return body

        def _left_panel(window: _Window) -> QWidget:
            panel = QWidget()
            panel.setFixedWidth(250)
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)

            controls = _card(window, "controls")
            arm = window._localized_button("arm", "PrimaryButton")
            safe = window._localized_button("safe_button", "GhostButton")
            snapshot = window._localized_button("snapshot", "GhostButton")
            arm.clicked.connect(window._arm)
            safe.clicked.connect(window._safe)
            snapshot.clicked.connect(window._snapshot)
            controls.layout().addWidget(arm)
            controls.layout().addWidget(safe)
            controls.layout().addWidget(snapshot)
            execution = QCheckBox()
            execution.setObjectName("ExecutionToggle")
            execution.setToolTip("Allow the GUI loop to dispatch planned mouse commands.")
            execution.toggled.connect(window._set_execution_enabled)
            window.localized_widgets["enable_execution"].append(execution)
            window.execution_toggle = execution
            controls.layout().addWidget(execution)
            layout.addWidget(controls)

            runtime = _card(window, "runtime")
            for label, value in (
                ("window", "zuma deluxe"),
                ("state", "safe"),
                ("level", "none"),
                ("mode", "normal"),
                ("command", "NO_OP"),
            ):
                runtime.layout().addWidget(_key_value(window, label, value))
            layout.addWidget(runtime)

            presets = _card(window, "presets")
            for text, callback in (
                ("load_ini", window._load_ini),
                ("save_preset", window._save_preset),
                ("reset_defaults", window._reset_defaults),
            ):
                button = window._localized_button(text, "GhostButton")
                button.clicked.connect(callback)
                presets.layout().addWidget(button)
            layout.addWidget(presets)

            hotkeys = _card(window, "hotkeys")
            for label, name, value in (
                ("toggle_arm", "toggle_arm", window.gui_settings.hotkeys.toggle_arm),
                ("snapshot_key", "snapshot", window.gui_settings.hotkeys.snapshot),
                ("safe_key", "safe", window.gui_settings.hotkeys.safe),
            ):
                hotkeys.layout().addWidget(_hotkey_row(window, label, name, value))
            layout.addWidget(hotkeys)

            layout.addStretch()
            return panel

        def _right_panel(window: _Window) -> QWidget:
            panel = QWidget()
            panel.setFixedWidth(310)
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)

            preview = _card(window, "preview")
            placeholder = QLabel()
            placeholder.setObjectName("Preview")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setText(window._t("preview_placeholder"))
            placeholder.setMinimumHeight(300)
            placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            window.preview_label = placeholder
            preview.layout().addWidget(placeholder, 1)
            layout.addWidget(preview, 1)

            log = _card(window, "event_log")
            log_text = QLabel()
            window.log_label = log_text
            log_text.setObjectName("LogText")
            log_text.setFont(QFont("Consolas", 10))
            log_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            log.layout().addWidget(log_text, 1)
            layout.addWidget(log, 1)
            return panel

        def _parameter_tabs(window: _Window, schema: tuple[GuiParameterDefinition, ...]) -> QWidget:
            tabs = QTabWidget()
            tabs.setObjectName("ParamTabs")
            for key, mode in (
                ("tab_general", GuiParameterMode.GENERAL),
                ("tab_normal", GuiParameterMode.NORMAL),
                ("tab_rescue", GuiParameterMode.RESCUE),
                ("tab_endgame", GuiParameterMode.ENDGAME),
            ):
                index = tabs.addTab(_parameter_page(window, _filter(schema, mode)), "")
                window.localized_tabs.append((tabs, index, key))
            return tabs

        def _parameter_page(
            window: _Window,
            parameters: tuple[GuiParameterDefinition, ...],
        ) -> QWidget:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setObjectName("ParamScroll")
            content = QWidget()
            layout = QVBoxLayout(content)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(12)

            grouped: dict[str, list[GuiParameterDefinition]] = defaultdict(list)
            for parameter in parameters:
                grouped[parameter.section].append(parameter)

            for section, items in grouped.items():
                section_card = _card(window, section)
                for parameter in items:
                    section_card.layout().addWidget(_parameter_row(window, parameter))
                layout.addWidget(section_card)
            layout.addStretch()
            scroll.setWidget(content)
            return scroll

        def _parameter_row(window: _Window, parameter: GuiParameterDefinition) -> QWidget:
            row = QFrame()
            row.setObjectName("ParamRow")
            layout = QGridLayout(row)
            layout.setContentsMargins(0, 6, 0, 6)
            layout.setHorizontalSpacing(12)
            layout.setColumnStretch(0, 3)
            layout.setColumnStretch(1, 2)

            label = QLabel(parameter.label)
            label.setObjectName("ParamLabel")
            label.setToolTip(parameter.description)
            layout.addWidget(label, 0, 0)

            key = QLabel(parameter.key)
            key.setObjectName("ParamKey")
            layout.addWidget(key, 1, 0)

            if parameter.kind is GuiParameterKind.TOGGLE:
                control = QCheckBox()
                control.setChecked(parameter.default >= 0.5)
                layout.addWidget(control, 0, 1, 2, 1, Qt.AlignmentFlag.AlignRight)
                window.parameter_controls[parameter.key] = control
            elif parameter.kind is GuiParameterKind.RANK:
                spin = QSpinBox()
                spin.setRange(int(parameter.minimum), int(parameter.maximum))
                spin.setSingleStep(int(parameter.step))
                spin.setValue(int(round(parameter.default)))
                layout.addWidget(spin, 0, 1, 2, 1)
                window.parameter_controls[parameter.key] = spin
            else:
                spin = QDoubleSpinBox()
                spin.setRange(parameter.minimum, parameter.maximum)
                spin.setSingleStep(parameter.step)
                spin.setDecimals(3)
                spin.setValue(parameter.default)
                layout.addWidget(spin, 0, 1, 2, 1)
                window.parameter_controls[parameter.key] = spin
            return row

        def _filter(
            schema: tuple[GuiParameterDefinition, ...],
            mode: GuiParameterMode,
        ) -> tuple[GuiParameterDefinition, ...]:
            return tuple(parameter for parameter in schema if parameter.mode is mode)

        def _card(window: _Window, title_key: str) -> QFrame:
            card = QFrame()
            card.setObjectName("Card")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 14)
            layout.setSpacing(9)
            header = window._localized_label(title_key, "CardTitle")
            header.setObjectName("CardTitle")
            layout.addWidget(header)
            return card

        def _key_value(window: _Window, label_key: str, value: str) -> QWidget:
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            name = window._localized_label(label_key, "Muted")
            name.setObjectName("Muted")
            data = QLabel(value)
            data.setObjectName("Value")
            window.status_values[label_key] = data
            layout.addWidget(name)
            layout.addStretch()
            layout.addWidget(data)
            return row

        def _set_object_name(widget: QWidget, object_name: str) -> None:
            widget.setObjectName(object_name)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        def _bgr_to_pixmap(image_bgr) -> QPixmap:
            rgb = image_bgr[:, :, ::-1].copy()
            height, width, channels = rgb.shape
            qimage = QImage(
                rgb.data,
                width,
                height,
                channels * width,
                QImage.Format.Format_RGB888,
            ).copy()
            return QPixmap.fromImage(qimage)

        def _hotkey_row(
            window: _Window,
            label_key: str,
            name: str,
            value: str,
        ) -> QWidget:
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            label = window._localized_label(label_key, "Muted")
            edit = QKeySequenceEdit(QKeySequence(value))
            edit.editingFinished.connect(window._save_gui_settings)
            window.hotkey_controls[name] = edit
            layout.addWidget(label)
            layout.addStretch()
            layout.addWidget(edit)
            return row

        return _Window()


_STYLE = """
QWidget {
    background: #25282d;
    color: #f0f3f8;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 14px;
}
#TitleBar {
    background: #1e2126;
    border-bottom: 1px solid #15181c;
}
#Badge {
    background: #756dd6;
    border-radius: 16px;
    min-width: 32px;
    min-height: 32px;
    max-width: 32px;
    max-height: 32px;
    font-weight: 800;
}
#AppTitle {
    font-size: 17px;
    font-weight: 800;
}
#Muted, #ParamKey {
    color: #aab3c2;
}
#Value {
    color: #f7d36c;
    font-weight: 700;
}
#SafePill, #InfoPill {
    border-radius: 13px;
    padding: 5px 10px;
    font-weight: 800;
}
#SafePill {
    background: #233a2b;
    color: #78e08f;
}
#InfoPill {
    background: #30344d;
    color: #c8c4ff;
}
#Card {
    background: #2b2f35;
    border: 1px solid #171a1f;
    border-radius: 9px;
}
#CardTitle {
    color: #ffffff;
    font-size: 17px;
    font-weight: 800;
}
QPushButton#PrimaryButton {
    background: #756dd6;
    border: 0;
    border-radius: 16px;
    padding: 9px 14px;
    font-weight: 800;
}
QPushButton#GhostButton {
    background: #282c32;
    border: 1px solid #737b8c;
    border-radius: 16px;
    padding: 8px 14px;
    font-weight: 700;
}
QPushButton#GhostButton:hover, QPushButton#PrimaryButton:hover {
    background: #837be8;
}
#Preview, #LogText {
    background: #20242a;
    border: 1px solid #414852;
    border-radius: 8px;
    padding: 12px;
}
#Preview {
    color: #87909f;
    font-size: 18px;
}
#LogText {
    color: #cbd4e0;
}
QTabWidget::pane {
    border: 1px solid #171a1f;
    border-radius: 9px;
    background: #2b2f35;
}
QTabBar::tab {
    background: #20242a;
    color: #cbd4e0;
    padding: 9px 18px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #756dd6;
    color: white;
    font-weight: 800;
}
QScrollArea#ParamScroll {
    border: 0;
}
#ParamRow {
    background: #30343b;
    border-radius: 7px;
}
#ParamLabel {
    font-weight: 750;
}
QDoubleSpinBox, QSpinBox {
    background: #20242a;
    border: 1px solid #4b5360;
    border-radius: 7px;
    padding: 5px 8px;
    min-width: 96px;
}
QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #8b84ef;
}
QCheckBox::indicator {
    width: 38px;
    height: 20px;
}
"""


if __name__ == "__main__":
    raise SystemExit(main())
