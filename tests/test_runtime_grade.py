import csv

import numpy as np

from autozuma.core.models import Point
from autozuma.runtime.grade import (
    FileGradeArchive,
    FileGameOverArchive,
    GameOverStats,
    GradeCaptureParams,
    GradeCaptureStatus,
    GradeStats,
    OcrReading,
    capture_completed_level,
    is_valid_grade,
    recognize_game_over_stats,
    recognize_grade_stats,
)


def test_campaign_grade_validation_matches_configured_chapter_sizes():
    assert is_valid_grade("1-1") is True
    assert is_valid_grade("3-5") is True
    assert is_valid_grade("4-6") is True
    assert is_valid_grade("7-7") is True
    assert is_valid_grade("12-7") is True
    assert is_valid_grade("13-1") is True

    assert is_valid_grade("1-6") is False
    assert is_valid_grade("4-7") is False
    assert is_valid_grade("7-8") is False
    assert is_valid_grade("13-2") is False
    assert is_valid_grade("14-1") is False


def test_recognize_grade_stats_uses_ok_relative_fields_and_validates_values():
    reader = _FakeOcrReader()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    result = recognize_grade_stats(
        frame_bgr=frame,
        ok_target=Point(x=390, y=390),
        ocr_reader=reader,
    )

    assert result == GradeStats(
        grade="1-1",
        points=8150,
        combos=7,
        coins=1,
        gaps=0,
        max_chain=2,
        max_combo=5,
        your_time_seconds=23,
        ace_time_seconds=25,
        bonus=2000,
        best_time_seconds=7,
        player_name="BIGORANGE",
        ocr_confidence=0.9,
    )
    assert set(reader.fields) == {
        "grade",
        "points",
        "combos",
        "coins",
        "gaps",
        "max_chain",
        "max_combo",
        "your_time",
        "ace_time",
        "bonus",
        "best_time",
        "player_name",
    }


def test_capture_completed_level_writes_independent_csv_and_screenshot(tmp_path):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[100:440, 100:550] = (20, 80, 40)
    params = GradeCaptureParams(root=tmp_path)

    result = capture_completed_level(
        frame_bgr=frame,
        ok_target=Point(x=326, y=386),
        level_id="spiral",
        raw_values={"n_fire_cooldown": 0.35},
        current_time=1_721_736_000.125,
        params=params,
        ocr_reader=_FakeOcrReader(),
    )

    assert result.status is GradeCaptureStatus.RECORDED
    assert result.archive is not None
    assert result.archive.csv_path == tmp_path / "1-1.csv"
    assert result.archive.screenshot_path is not None
    assert result.archive.screenshot_path.exists()

    with result.archive.csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
    assert tuple(rows[0]) == (
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
    assert rows[0]["points"] == "8150"
    assert rows[0]["your_time_seconds"] == "23"


def test_file_grade_archive_suppresses_recent_duplicate_but_appends_new_run(tmp_path):
    archive = FileGradeArchive(root=tmp_path, duplicate_window_seconds=60.0)
    stats = _stats()
    frame = np.zeros((10, 10, 3), dtype=np.uint8)

    first = archive.append(
        stats=stats,
        frame_bgr=frame,
        level_id="spiral",
        raw_values={},
        current_time=1_700_000_000.0,
        fingerprint="same",
    )
    duplicate = archive.append(
        stats=stats,
        frame_bgr=frame,
        level_id="spiral",
        raw_values={},
        current_time=1_700_000_010.0,
        fingerprint="same",
    )
    later_run = archive.append(
        stats=stats,
        frame_bgr=frame,
        level_id="spiral",
        raw_values={},
        current_time=1_700_000_100.0,
        fingerprint="same",
    )

    assert first.added is True
    assert duplicate.added is False
    assert later_run.added is True
    with (tmp_path / "1-1.csv").open("r", encoding="utf-8-sig", newline="") as file:
        assert len(list(csv.DictReader(file))) == 2


def test_recognize_game_over_stats_reads_score_level_and_summary():
    result = recognize_game_over_stats(
        frame_bgr=np.zeros((480, 640, 3), dtype=np.uint8),
        ok_target=Point(x=326, y=346),
        ocr_reader=_FakeOcrReader(game_over=True),
    )

    assert result == GameOverStats(
        grade="10-1",
        total_score=1190,
        total_time_seconds=40,
        combos=3,
        coins=0,
        gaps=1,
        max_chain=2,
        max_combo=2,
        ocr_confidence=0.9,
    )


def test_game_over_archive_uses_independent_per_level_table(tmp_path):
    archive = FileGameOverArchive(root=tmp_path)
    result = archive.append(
        stats=GameOverStats(
            grade="10-1",
            total_score=1190,
            total_time_seconds=40,
            combos=3,
            coins=0,
            gaps=1,
            max_chain=2,
            max_combo=2,
            ocr_confidence=0.9,
        ),
        frame_bgr=np.zeros((10, 10, 3), dtype=np.uint8),
        level_id="targetglyph",
        raw_values={"r_fire_cooldown": 0.52},
        current_time=1_700_000_000.0,
        fingerprint="game-over",
    )

    assert result.csv_path == tmp_path / "gameover" / "10-1.csv"
    assert result.screenshot_path is not None and result.screenshot_path.exists()
    with result.csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert tuple(rows[0]) == (
        "total_score",
        "total_time_seconds",
        "combos",
        "coins",
        "gaps",
        "max_chain",
        "max_combo",
    )
    assert rows[0]["total_score"] == "1190"
    assert rows[0]["total_time_seconds"] == "40"


def test_grade_archive_migrates_legacy_metadata_columns(tmp_path):
    csv_path = tmp_path / "1-1.csv"
    csv_path.write_text(
        "captured_at,grade,level_id,points,combos,coins,gaps,max_chain,max_combo,"
        "your_time_seconds,ace_time_seconds,bonus,best_time_seconds,player_name,"
        "screenshot_path,parameters_json\n"
        "2026-07-23T20:00:00,1-1,spiral,7000,3,0,1,2,3,40,25,,12,PLAYER,"
        'screenshots/1-1/a.png,\"{}\"\n',
        encoding="utf-8-sig",
    )

    FileGradeArchive(root=tmp_path, duplicate_window_seconds=0).append(
        stats=_stats(),
        frame_bgr=np.zeros((10, 10, 3), dtype=np.uint8),
        level_id="spiral",
        raw_values={},
        current_time=1_700_000_000.0,
        fingerprint="new",
    )

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 2
    assert "captured_at" not in rows[0]
    assert "grade" not in rows[0]
    assert "level_id" not in rows[0]
    assert "screenshot_path" not in rows[0]
    assert "parameters_json" not in rows[0]
    assert rows[0]["points"] == "7000"
    assert rows[1]["points"] == "8150"


def _stats() -> GradeStats:
    return GradeStats(
        grade="1-1",
        points=8150,
        combos=7,
        coins=0,
        gaps=0,
        max_chain=2,
        max_combo=5,
        your_time_seconds=23,
        ace_time_seconds=25,
        bonus=2000,
        best_time_seconds=7,
        player_name="BIGORANGE",
        ocr_confidence=0.9,
    )


class _FakeOcrReader:
    def __init__(self, game_over=False):
        self.fields = []
        self.game_over = game_over

    def recognize(self, image_bgr, *, field_name):
        self.fields.append(field_name)
        values = {
            "stats_title": "STATS",
            "game_over_title": "GAME OVER",
            "grade": "LVL 10-1" if self.game_over else "LVL H-1",
            "points": "8150",
            "combos": "7",
            "coins": "i",
            "gaps": "・",
            "max_chain": "2",
            "max_combo": "5",
            "your_time": "0:23",
            "ace_time": "0:25",
            "total_time": "0:40",
            "total_score": "1190",
            "bonus": "+2000",
            "best_time": "0:07",
            "player_name": "BIGORANGE",
        }
        if self.game_over:
            values.update(
                {
                    "combos": "3",
                    "coins": "o",
                    "gaps": "1",
                    "max_chain": "2",
                    "max_combo": "2",
                }
            )
        return OcrReading(values[field_name], 0.9)
