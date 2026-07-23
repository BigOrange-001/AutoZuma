"""STATS-screen recognition and per-level grade archives."""

from __future__ import annotations

import csv
import hashlib
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from autozuma.core.models import Point
from autozuma.project_paths import project_path


CSV_FIELDS = (
    "points",
    "combos",
    "coins",
    "gaps",
    "max_chain",
    "max_combo",
    "your_time_seconds",
    "ace_time_seconds",
    "bonus",
    "best_time_seconds",
    "player_name",
)

GAME_OVER_CSV_FIELDS = (
    "total_score",
    "total_time_seconds",
    "combos",
    "coins",
    "gaps",
    "max_chain",
    "max_combo",
)
_RECENT_ROWS: dict[Path, tuple[float, dict[str, str]]] = {}


class GradeRecognitionError(ValueError):
    """Raised when a STATS screen cannot be parsed safely."""


class GradeCaptureStatus(Enum):
    """Outcome of inspecting one detected OK screen."""

    NOT_STATS = "not_stats"
    RECORDED = "recorded"
    DUPLICATE = "duplicate"
    RETRYABLE_FAILURE = "retryable_failure"


@dataclass(frozen=True)
class OcrReading:
    """One OCR line and its model confidence."""

    text: str
    confidence: float


class StatsOcrReader(Protocol):
    """Small OCR boundary used by the fixed-layout STATS parser."""

    def recognize(self, image_bgr: np.ndarray, *, field_name: str) -> OcrReading:
        """Recognize a single already-cropped line."""


@dataclass(frozen=True)
class GradeStats:
    """Validated values read from a completed-level STATS screen."""

    grade: str
    points: int
    combos: int
    coins: int
    gaps: int
    max_chain: int
    max_combo: int
    your_time_seconds: int
    ace_time_seconds: int
    bonus: int | None = None
    best_time_seconds: int | None = None
    player_name: str = ""
    ocr_confidence: float = 0.0


@dataclass(frozen=True)
class GradeRecord:
    """One row persisted in a per-level CSV archive."""

    stats: GradeStats

    def as_csv_row(self) -> dict[str, object]:
        return {
            "points": self.stats.points,
            "combos": self.stats.combos,
            "coins": self.stats.coins,
            "gaps": self.stats.gaps,
            "max_chain": self.stats.max_chain,
            "max_combo": self.stats.max_combo,
            "your_time_seconds": self.stats.your_time_seconds,
            "ace_time_seconds": self.stats.ace_time_seconds,
            "bonus": "" if self.stats.bonus is None else self.stats.bonus,
            "best_time_seconds": (
                "" if self.stats.best_time_seconds is None else self.stats.best_time_seconds
            ),
            "player_name": self.stats.player_name,
        }


@dataclass(frozen=True)
class GradeArchiveResult:
    """Files affected by one archive attempt."""

    added: bool
    csv_path: Path
    screenshot_path: Path | None


@dataclass(frozen=True)
class GradeCaptureResult:
    """Result of inspecting and optionally archiving one OK screen."""

    status: GradeCaptureStatus
    fingerprint: str | None = None
    stats: GradeStats | None = None
    archive: GradeArchiveResult | None = None
    error: str | None = None


@dataclass(frozen=True)
class GameOverStats:
    """Validated values read from a GAME OVER screen."""

    grade: str
    total_score: int
    total_time_seconds: int
    combos: int
    coins: int
    gaps: int
    max_chain: int
    max_combo: int
    ocr_confidence: float = 0.0


@dataclass(frozen=True)
class GameOverRecord:
    """One row persisted in a per-level GAME OVER archive."""

    stats: GameOverStats

    def as_csv_row(self) -> dict[str, object]:
        return {
            "total_score": self.stats.total_score,
            "total_time_seconds": self.stats.total_time_seconds,
            "combos": self.stats.combos,
            "coins": self.stats.coins,
            "gaps": self.stats.gaps,
            "max_chain": self.stats.max_chain,
            "max_combo": self.stats.max_combo,
        }


@dataclass(frozen=True)
class GameOverCaptureResult:
    """Result of inspecting and optionally archiving one GAME OVER screen."""

    status: GradeCaptureStatus
    fingerprint: str | None = None
    stats: GameOverStats | None = None
    archive: GradeArchiveResult | None = None
    error: str | None = None


@dataclass(frozen=True)
class GradeCaptureState:
    """Session-local deduplication and retry state."""

    recorded_fingerprint: str | None = None
    retry_count: int = 0


@dataclass(frozen=True)
class GradeCaptureParams:
    """Output and retry settings for completed-level capture."""

    root: Path = field(default_factory=lambda: project_path("grade"))
    enabled: bool = True
    max_parse_attempts: int = 4
    retry_interval: float = 0.25
    duplicate_window_seconds: float = 60.0


class RapidStatsOcrReader:
    """RapidOCR adapter specialized for the fixed Zuma STATS layout."""

    _HIGH_SATURATION_FIELDS = frozenset(
        {"points", "combos", "coins", "gaps", "max_chain", "max_combo", "bonus"}
    )

    def __init__(self) -> None:
        from rapidocr import RapidOCR

        self._engine = RapidOCR()

    def recognize(self, image_bgr: np.ndarray, *, field_name: str) -> OcrReading:
        if image_bgr.size == 0:
            return OcrReading("", 0.0)
        prepared = self._prepare(image_bgr, field_name)
        output = self._engine(
            prepared,
            use_det=False,
            use_cls=False,
            use_rec=True,
        )
        texts = tuple(getattr(output, "txts", ()) or ())
        scores = tuple(getattr(output, "scores", ()) or ())
        if not texts:
            return OcrReading("", 0.0)
        return OcrReading(
            text=str(texts[0]).strip(),
            confidence=float(scores[0]) if scores else 0.0,
        )

    def _prepare(self, image_bgr: np.ndarray, field_name: str) -> np.ndarray:
        prepared = image_bgr
        if field_name in self._HIGH_SATURATION_FIELDS:
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
            foreground = (hsv[:, :, 1] > 90) & (hsv[:, :, 2] > 110)
            binary = np.where(foreground, 255, 0).astype(np.uint8)
            prepared = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
            interpolation = cv2.INTER_NEAREST
        else:
            interpolation = cv2.INTER_CUBIC
        return cv2.resize(
            prepared,
            None,
            fx=4.0,
            fy=4.0,
            interpolation=interpolation,
        )


@dataclass(frozen=True)
class FileGradeArchive:
    """Append records to independent per-level CSV files."""

    root: Path
    duplicate_window_seconds: float = 60.0

    def append(
        self,
        *,
        stats: GradeStats,
        frame_bgr: np.ndarray,
        level_id: str | None,
        raw_values: Mapping[str, float],
        current_time: float,
        fingerprint: str,
    ) -> GradeArchiveResult:
        if not is_valid_grade(stats.grade):
            raise GradeRecognitionError(f"invalid grade identifier: {stats.grade!r}")

        self.root.mkdir(parents=True, exist_ok=True)
        csv_path = self.root / f"{stats.grade}.csv"
        row = GradeRecord(stats=stats).as_csv_row()
        duplicate = _recent_duplicate(
            csv_path=csv_path,
            row=row,
            current_time=current_time,
            window_seconds=self.duplicate_window_seconds,
        )
        if duplicate:
            return GradeArchiveResult(added=False, csv_path=csv_path, screenshot_path=None)

        screenshot_path = _unique_screenshot_path(
            root=self.root,
            grade=stats.grade,
            current_time=current_time,
        )
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        _write_bgr_image(screenshot_path, frame_bgr)
        _append_csv_row(csv_path, row)
        _remember_row(csv_path, row, current_time)
        return GradeArchiveResult(
            added=True,
            csv_path=csv_path,
            screenshot_path=screenshot_path,
        )

    def save_failure(
        self,
        *,
        frame_bgr: np.ndarray,
        current_time: float,
        error: str,
    ) -> Path:
        failure_root = self.root / "failed"
        failure_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.fromtimestamp(current_time).strftime("%Y%m%d_%H%M%S")
        milliseconds = int((current_time % 1.0) * 1000)
        image_path = _unique_path(failure_root / f"{timestamp}_{milliseconds:03d}.png")
        _write_bgr_image(image_path, frame_bgr)
        error_path = image_path.with_suffix(".txt")
        error_path.write_text(error, encoding="utf-8")
        return image_path


@dataclass(frozen=True)
class FileGameOverArchive:
    """Append GAME OVER records to independent per-level CSV files."""

    root: Path
    duplicate_window_seconds: float = 60.0

    def append(
        self,
        *,
        stats: GameOverStats,
        frame_bgr: np.ndarray,
        level_id: str | None,
        raw_values: Mapping[str, float],
        current_time: float,
        fingerprint: str,
    ) -> GradeArchiveResult:
        if not is_valid_grade(stats.grade):
            raise GradeRecognitionError(f"invalid grade identifier: {stats.grade!r}")

        game_over_root = self.root / "gameover"
        game_over_root.mkdir(parents=True, exist_ok=True)
        csv_path = game_over_root / f"{stats.grade}.csv"
        row = GameOverRecord(stats=stats).as_csv_row()
        duplicate = _recent_duplicate(
            csv_path=csv_path,
            row=row,
            current_time=current_time,
            window_seconds=self.duplicate_window_seconds,
        )
        if duplicate:
            return GradeArchiveResult(added=False, csv_path=csv_path, screenshot_path=None)

        screenshot_path = _unique_game_over_screenshot_path(
            root=game_over_root,
            grade=stats.grade,
            current_time=current_time,
        )
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        _write_bgr_image(screenshot_path, frame_bgr)
        _append_csv_row(
            csv_path,
            row,
            fieldnames=GAME_OVER_CSV_FIELDS,
        )
        _remember_row(csv_path, row, current_time)
        return GradeArchiveResult(
            added=True,
            csv_path=csv_path,
            screenshot_path=screenshot_path,
        )


_RELATIVE_FIELD_ROIS: dict[str, tuple[int, int, int, int]] = {
    "stats_title": (-80, 40, -245, -205),
    "points": (-70, -5, -194, -176),
    "combos": (-70, -25, -175, -157),
    "coins": (-70, -25, -156, -138),
    "gaps": (-70, -25, -137, -119),
    "max_chain": (-70, -25, -118, -100),
    "max_combo": (-70, -25, -99, -81),
    "your_time": (118, 170, -194, -176),
    "ace_time": (118, 170, -175, -157),
    "bonus": (80, 170, -156, -138),
    "best_time": (118, 170, -118, -100),
    "player_name": (10, 170, -99, -81),
}
_GAME_OVER_FIELD_ROIS: dict[str, tuple[int, int, int, int]] = {
    "game_over_title": (-125, 125, -215, -165),
    "total_time": (-75, -15, -158, -140),
    "combos": (-75, -35, -138, -120),
    "coins": (-75, -35, -118, -100),
    "gaps": (140, 175, -158, -140),
    "max_chain": (140, 175, -138, -120),
    "max_combo": (140, 175, -118, -100),
}
_PANEL_FINGERPRINT_ROI = (-230, 230, -300, 60)
_LEVEL_ROI_640X480 = (167, 232, 0, 22)
_SCORE_ROI_640X480 = (300, 380, 0, 25)
_ZERO_LIKE_TEXT = frozenset({"O", "o", "〇", "○", "。", "·", "・", "ãƒ»"})


def capture_completed_level(
    *,
    frame_bgr: np.ndarray,
    ok_target: Point,
    level_id: str | None,
    raw_values: Mapping[str, float],
    current_time: float,
    params: GradeCaptureParams,
    recorded_fingerprint: str | None = None,
    ocr_reader: StatsOcrReader | None = None,
) -> GradeCaptureResult:
    """Recognize and archive a draggable STATS panel anchored by its OK button."""
    if not params.enabled:
        return GradeCaptureResult(status=GradeCaptureStatus.NOT_STATS)

    reader = ocr_reader or default_ocr_reader()
    try:
        title_crop = _relative_crop(frame_bgr, ok_target, _RELATIVE_FIELD_ROIS["stats_title"])
        title = reader.recognize(title_crop, field_name="stats_title")
    except Exception as exc:  # noqa: BLE001 - OCR errors must not terminate the game loop.
        return GradeCaptureResult(
            status=GradeCaptureStatus.RETRYABLE_FAILURE,
            error=f"STATS title OCR failed: {exc}",
        )

    normalized_title = re.sub(r"[^A-Z]", "", title.text.upper())
    if "STAT" not in normalized_title:
        return GradeCaptureResult(status=GradeCaptureStatus.NOT_STATS)

    fingerprint = stats_screen_fingerprint(frame_bgr, ok_target)
    if fingerprint == recorded_fingerprint:
        return GradeCaptureResult(
            status=GradeCaptureStatus.DUPLICATE,
            fingerprint=fingerprint,
        )

    try:
        stats = recognize_grade_stats(
            frame_bgr=frame_bgr,
            ok_target=ok_target,
            ocr_reader=reader,
        )
        archive = FileGradeArchive(
            root=params.root,
            duplicate_window_seconds=params.duplicate_window_seconds,
        ).append(
            stats=stats,
            frame_bgr=frame_bgr,
            level_id=level_id,
            raw_values=raw_values,
            current_time=current_time,
            fingerprint=fingerprint,
        )
    except (GradeRecognitionError, OSError, ValueError) as exc:
        return GradeCaptureResult(
            status=GradeCaptureStatus.RETRYABLE_FAILURE,
            fingerprint=fingerprint,
            error=str(exc),
        )

    return GradeCaptureResult(
        status=GradeCaptureStatus.RECORDED if archive.added else GradeCaptureStatus.DUPLICATE,
        fingerprint=fingerprint,
        stats=stats,
        archive=archive,
    )


def capture_game_over(
    *,
    frame_bgr: np.ndarray,
    ok_target: Point,
    level_id: str | None,
    raw_values: Mapping[str, float],
    current_time: float,
    params: GradeCaptureParams,
    recorded_fingerprint: str | None = None,
    ocr_reader: StatsOcrReader | None = None,
) -> GameOverCaptureResult:
    """Recognize and archive a draggable GAME OVER panel anchored by its OK button."""
    if not params.enabled:
        return GameOverCaptureResult(status=GradeCaptureStatus.NOT_STATS)

    reader = ocr_reader or default_ocr_reader()
    try:
        title_crop = _relative_crop(
            frame_bgr,
            ok_target,
            _GAME_OVER_FIELD_ROIS["game_over_title"],
        )
        title = reader.recognize(title_crop, field_name="game_over_title")
    except Exception as exc:  # noqa: BLE001 - OCR errors must not terminate the game loop.
        return GameOverCaptureResult(
            status=GradeCaptureStatus.RETRYABLE_FAILURE,
            error=f"GAME OVER title OCR failed: {exc}",
        )

    normalized_title = re.sub(r"[^A-Z]", "", title.text.upper())
    if "GAMEOVER" not in normalized_title:
        return GameOverCaptureResult(status=GradeCaptureStatus.NOT_STATS)

    fingerprint = stats_screen_fingerprint(frame_bgr, ok_target)
    if fingerprint == recorded_fingerprint:
        return GameOverCaptureResult(
            status=GradeCaptureStatus.DUPLICATE,
            fingerprint=fingerprint,
        )

    try:
        stats = recognize_game_over_stats(
            frame_bgr=frame_bgr,
            ok_target=ok_target,
            ocr_reader=reader,
        )
        archive = FileGameOverArchive(
            root=params.root,
            duplicate_window_seconds=params.duplicate_window_seconds,
        ).append(
            stats=stats,
            frame_bgr=frame_bgr,
            level_id=level_id,
            raw_values=raw_values,
            current_time=current_time,
            fingerprint=fingerprint,
        )
    except (GradeRecognitionError, OSError, ValueError) as exc:
        return GameOverCaptureResult(
            status=GradeCaptureStatus.RETRYABLE_FAILURE,
            fingerprint=fingerprint,
            error=str(exc),
        )

    return GameOverCaptureResult(
        status=GradeCaptureStatus.RECORDED if archive.added else GradeCaptureStatus.DUPLICATE,
        fingerprint=fingerprint,
        stats=stats,
        archive=archive,
    )


def recognize_grade_stats(
    *,
    frame_bgr: np.ndarray,
    ok_target: Point,
    ocr_reader: StatsOcrReader | None = None,
) -> GradeStats:
    """Read all validated values from a draggable STATS panel."""
    reader = ocr_reader or default_ocr_reader()
    readings: dict[str, OcrReading] = {}
    for field_name, roi in _RELATIVE_FIELD_ROIS.items():
        if field_name == "stats_title":
            continue
        readings[field_name] = reader.recognize(
            _relative_crop(frame_bgr, ok_target, roi),
            field_name=field_name,
        )

    level_reading = reader.recognize(_level_crop(frame_bgr), field_name="grade")
    grade = _parse_grade(level_reading.text)
    if not is_valid_grade(grade):
        raise GradeRecognitionError(
            f"recognized grade {grade!r} is outside the configured campaign layout"
        )

    required_names = (
        "points",
        "combos",
        "coins",
        "gaps",
        "max_chain",
        "max_combo",
        "your_time",
        "ace_time",
    )
    values = {
        name: (
            _parse_time(readings[name].text, name)
            if name.endswith("_time")
            else _parse_non_negative_int(readings[name].text, name)
        )
        for name in required_names
    }
    confidences = [level_reading.confidence]
    confidences.extend(readings[name].confidence for name in required_names)
    return GradeStats(
        grade=grade,
        points=values["points"],
        combos=values["combos"],
        coins=values["coins"],
        gaps=values["gaps"],
        max_chain=values["max_chain"],
        max_combo=values["max_combo"],
        your_time_seconds=values["your_time"],
        ace_time_seconds=values["ace_time"],
        bonus=_parse_optional_signed_int(readings["bonus"].text),
        best_time_seconds=_parse_optional_time(readings["best_time"].text),
        player_name=_normalize_player_name(readings["player_name"].text),
        ocr_confidence=round(sum(confidences) / len(confidences), 6),
    )


def recognize_game_over_stats(
    *,
    frame_bgr: np.ndarray,
    ok_target: Point,
    ocr_reader: StatsOcrReader | None = None,
) -> GameOverStats:
    """Read all validated values from a draggable GAME OVER panel."""
    reader = ocr_reader or default_ocr_reader()
    readings: dict[str, OcrReading] = {}
    for field_name, roi in _GAME_OVER_FIELD_ROIS.items():
        if field_name == "game_over_title":
            continue
        readings[field_name] = reader.recognize(
            _relative_crop(frame_bgr, ok_target, roi),
            field_name=field_name,
        )
    level_reading = reader.recognize(_level_crop(frame_bgr), field_name="grade")
    score_reading = reader.recognize(_score_crop(frame_bgr), field_name="total_score")
    grade = _parse_grade(level_reading.text)
    if not is_valid_grade(grade):
        raise GradeRecognitionError(
            f"recognized grade {grade!r} is outside the configured campaign layout"
        )

    required_names = ("combos", "coins", "gaps", "max_chain", "max_combo")
    values = {
        name: _parse_non_negative_int(readings[name].text, name)
        for name in required_names
    }
    confidences = [level_reading.confidence, score_reading.confidence]
    confidences.extend(readings[name].confidence for name in required_names)
    confidences.append(readings["total_time"].confidence)
    return GameOverStats(
        grade=grade,
        total_score=_parse_non_negative_int(score_reading.text, "total_score"),
        total_time_seconds=_parse_time(readings["total_time"].text, "total_time"),
        combos=values["combos"],
        coins=values["coins"],
        gaps=values["gaps"],
        max_chain=values["max_chain"],
        max_combo=values["max_combo"],
        ocr_confidence=round(sum(confidences) / len(confidences), 6),
    )


def stats_screen_fingerprint(frame_bgr: np.ndarray, ok_target: Point) -> str:
    """Return a stable fingerprint for duplicate suppression within one result screen."""
    panel = _relative_crop(frame_bgr, ok_target, _PANEL_FINGERPRINT_ROI)
    gray = cv2.cvtColor(panel, cv2.COLOR_BGR2GRAY)
    normalized = cv2.resize(gray, (230, 180), interpolation=cv2.INTER_AREA)
    return hashlib.sha256(normalized.tobytes()).hexdigest()


def is_valid_grade(grade: str) -> bool:
    """Validate Zuma's chapter/level campaign layout supplied for grade archives."""
    match = re.fullmatch(r"(\d{1,2})-(\d{1,2})", grade)
    if match is None:
        return False
    chapter, level = (int(value) for value in match.groups())
    if 1 <= chapter <= 3:
        return 1 <= level <= 5
    if 4 <= chapter <= 6:
        return 1 <= level <= 6
    if 7 <= chapter <= 12:
        return 1 <= level <= 7
    return chapter == 13 and level == 1


@lru_cache(maxsize=1)
def default_ocr_reader() -> RapidStatsOcrReader:
    return RapidStatsOcrReader()


def _relative_crop(
    frame_bgr: np.ndarray,
    anchor: Point,
    roi: tuple[int, int, int, int],
) -> np.ndarray:
    x1_offset, x2_offset, y1_offset, y2_offset = roi
    x1 = int(round(anchor.x)) + x1_offset
    x2 = int(round(anchor.x)) + x2_offset
    y1 = int(round(anchor.y)) + y1_offset
    y2 = int(round(anchor.y)) + y2_offset
    height, width = frame_bgr.shape[:2]
    if x1 < 0 or y1 < 0 or x2 > width or y2 > height or x1 >= x2 or y1 >= y2:
        raise GradeRecognitionError(
            f"STATS field crop falls outside frame: {(x1, y1, x2, y2)} vs {(width, height)}"
        )
    return frame_bgr[y1:y2, x1:x2]


def _level_crop(frame_bgr: np.ndarray) -> np.ndarray:
    height, width = frame_bgr.shape[:2]
    base_x1, base_x2, base_y1, base_y2 = _LEVEL_ROI_640X480
    x1 = max(0, round(base_x1 * width / 640))
    x2 = min(width, round(base_x2 * width / 640))
    y1 = max(0, round(base_y1 * height / 480))
    y2 = min(height, round(base_y2 * height / 480))
    if x1 >= x2 or y1 >= y2:
        raise GradeRecognitionError("level label crop is empty")
    return frame_bgr[y1:y2, x1:x2]


def _score_crop(frame_bgr: np.ndarray) -> np.ndarray:
    return _scaled_frame_crop(frame_bgr, _SCORE_ROI_640X480, "score")


def _scaled_frame_crop(
    frame_bgr: np.ndarray,
    roi: tuple[int, int, int, int],
    field_name: str,
) -> np.ndarray:
    height, width = frame_bgr.shape[:2]
    base_x1, base_x2, base_y1, base_y2 = roi
    x1 = max(0, round(base_x1 * width / 640))
    x2 = min(width, round(base_x2 * width / 640))
    y1 = max(0, round(base_y1 * height / 480))
    y2 = min(height, round(base_y2 * height / 480))
    if x1 >= x2 or y1 >= y2:
        raise GradeRecognitionError(f"{field_name} crop is empty")
    return frame_bgr[y1:y2, x1:x2]


def _parse_grade(text: str) -> str:
    compact = re.sub(r"\s+", "", text.upper())
    compact = compact.replace("—", "-").replace("–", "-").replace("_", "-")
    compact = re.sub(r"^[I1L]V[I1L]", "", compact)
    normalized = compact.translate(
        str.maketrans({"I": "1", "L": "1", "H": "1", "O": "0"})
    )
    match = re.search(r"(\d{1,2})-(\d{1,2})$", normalized)
    if match is None:
        raise GradeRecognitionError(f"could not parse grade from OCR text {text!r}")
    return f"{int(match.group(1))}-{int(match.group(2))}"


def _parse_non_negative_int(text: str, field_name: str) -> int:
    stripped = text.strip()
    translated = stripped.translate(
        str.maketrans(
            {"O": "0", "o": "0", "I": "1", "i": "1", "l": "1", "S": "5"}
        )
    )
    digits = re.findall(r"\d+", translated)
    if digits:
        return int("".join(digits))
    if stripped in _ZERO_LIKE_TEXT:
        return 0
    raise GradeRecognitionError(f"could not parse {field_name} from OCR text {text!r}")


def _parse_time(text: str, field_name: str) -> int:
    translated = text.strip().translate(
        str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", ".": ":", ";": ":"})
    )
    match = re.search(r"(\d{1,3}):(\d{2})", translated)
    if match is None:
        raise GradeRecognitionError(f"could not parse {field_name} from OCR text {text!r}")
    minutes, seconds = (int(value) for value in match.groups())
    if seconds >= 60:
        raise GradeRecognitionError(f"{field_name} has invalid seconds in {text!r}")
    return minutes * 60 + seconds


def _parse_optional_time(text: str) -> int | None:
    if not text.strip():
        return None
    try:
        return _parse_time(text, "best_time")
    except GradeRecognitionError:
        return None


def _parse_optional_signed_int(text: str) -> int | None:
    if not text.strip():
        return None
    translated = text.translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1"}))
    match = re.search(r"[-+]?\d+", translated)
    return int(match.group(0)) if match is not None else None


def _normalize_player_name(text: str) -> str:
    return re.sub(r"[^A-Z0-9_.-]", "", text.upper())


def _append_csv_row(
    path: Path,
    row: Mapping[str, object],
    *,
    fieldnames: tuple[str, ...] = CSV_FIELDS,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _migrate_csv_schema(path, fieldnames)
    is_new = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
        file.flush()
        os.fsync(file.fileno())


def _recent_duplicate(
    *,
    csv_path: Path,
    row: Mapping[str, object],
    current_time: float,
    window_seconds: float,
) -> bool:
    remembered = _RECENT_ROWS.get(csv_path.resolve())
    if remembered is not None:
        recorded_at, recorded_row = remembered
        return (
            abs(current_time - recorded_at) <= max(0.0, window_seconds)
            and recorded_row == _normalized_csv_row(row)
        )
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return False
    if abs(current_time - csv_path.stat().st_mtime) > max(0.0, window_seconds):
        return False
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
    except (OSError, csv.Error):
        return False
    if not rows:
        return False
    last = rows[-1]
    return all(last.get(key, "") == _csv_text(value) for key, value in row.items())


def _remember_row(path: Path, row: Mapping[str, object], current_time: float) -> None:
    _RECENT_ROWS[path.resolve()] = (current_time, _normalized_csv_row(row))


def _normalized_csv_row(row: Mapping[str, object]) -> dict[str, str]:
    return {str(key): _csv_text(value) for key, value in row.items()}


def _migrate_csv_schema(path: Path, fieldnames: tuple[str, ...]) -> None:
    """Drop legacy metadata columns without losing recognized result rows."""
    if not path.exists() or path.stat().st_size == 0:
        return
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            existing_fields = tuple(reader.fieldnames or ())
            rows = list(reader)
    except (OSError, csv.Error):
        return
    if existing_fields == fieldnames:
        return

    migrated_rows = [
        {field_name: row.get(field_name, "") for field_name in fieldnames}
        for row in rows
    ]
    temporary_path = _unique_path(path.with_suffix(f"{path.suffix}.tmp"))
    try:
        with temporary_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(migrated_rows)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _csv_text(value: object) -> str:
    return "" if value is None else str(value)


def _unique_screenshot_path(root: Path, grade: str, current_time: float) -> Path:
    timestamp = datetime.fromtimestamp(current_time).strftime("%Y%m%d_%H%M%S")
    milliseconds = int((current_time % 1.0) * 1000)
    return _unique_path(
        root / "screenshots" / grade / f"{timestamp}_{milliseconds:03d}_{grade}.png"
    )


def _unique_game_over_screenshot_path(
    root: Path,
    grade: str,
    current_time: float,
) -> Path:
    timestamp = datetime.fromtimestamp(current_time).strftime("%Y%m%d_%H%M%S")
    milliseconds = int((current_time % 1.0) * 1000)
    return _unique_path(
        root / "screenshots" / grade / f"{timestamp}_{milliseconds:03d}_{grade}_gameover.png"
    )


def _unique_path(path: Path) -> Path:
    candidate = path
    suffix = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{suffix:02d}{path.suffix}")
        suffix += 1
    return candidate


def _write_bgr_image(path: Path, image_bgr: np.ndarray) -> None:
    ok, buffer = cv2.imencode(path.suffix, image_bgr)
    if not ok:
        raise ValueError(f"could not encode grade screenshot: {path}")
    buffer.tofile(path)
