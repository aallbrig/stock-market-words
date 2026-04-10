"""
Tests for the translate module.

Ollama HTTP calls are mocked so tests run without a local Ollama instance.
DB operations use a temporary SQLite file (patching stock_ticker.config.DB_PATH
so all get_connection() calls resolve to the temp file).
"""

import json
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stock_ticker.translate import (
    SYSTEM_PROMPT,
    TranslateConfig,
    _fmt_duration,
    _has_non_empty_body,
    _insert_job_rows,
    _insert_run,
    build_job_list,
    fetch_heuristics,
    run_translate,
    split_frontmatter,
    translate_job,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures & helpers
# ──────────────────────────────────────────────────────────────────────────────

SAMPLE_FRONTMATTER = """\
---
title: "Test Page"
description: "A test page"
date: 2026-01-01
layout: "page"
---"""

SAMPLE_BODY = """\
## Introduction

This is a test article about stock markets.

- RSI is a momentum indicator
- Ticker AAPL is a well-known company
- {{< shortcode param="value" >}}

```python
code = "is not translated"
```"""

SAMPLE_MD = SAMPLE_FRONTMATTER + "\n\n" + SAMPLE_BODY

TRANSLATED_BODY = """\
## 介绍

这是一篇关于股票市场的测试文章。

- 相对强弱指标 (RSI) 是动量指标
- AAPL 是一家知名公司
- {{< shortcode param="value" >}}

```python
code = "is not translated"
```"""


@pytest.fixture()
def temp_db(tmp_path):
    """Temporary SQLite DB with translate tables; patches config.DB_PATH globally."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE translate_runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          TEXT    NOT NULL UNIQUE,
            started_at      REAL    NOT NULL,
            completed_at    REAL,
            status          TEXT    NOT NULL DEFAULT 'running',
            languages       TEXT    NOT NULL,
            model           TEXT    NOT NULL,
            backend         TEXT    NOT NULL,
            workers         INTEGER NOT NULL,
            total_files     INTEGER NOT NULL,
            completed_files INTEGER NOT NULL DEFAULT 0,
            failed_files    INTEGER NOT NULL DEFAULT 0,
            skipped_files   INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE translate_file_jobs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id           TEXT    NOT NULL,
            source_path      TEXT    NOT NULL,
            target_path      TEXT    NOT NULL,
            language         TEXT    NOT NULL,
            model            TEXT    NOT NULL,
            worker_id        INTEGER,
            queued_at        REAL    NOT NULL,
            started_at       REAL,
            completed_at     REAL,
            status           TEXT    NOT NULL DEFAULT 'queued',
            duration_seconds REAL,
            input_chars      INTEGER,
            output_chars     INTEGER,
            attempt          INTEGER NOT NULL DEFAULT 1,
            error_message    TEXT
        );
    """)
    conn.commit()
    conn.close()

    # Patch DB_PATH everywhere it is imported so get_connection() resolves correctly
    with patch("stock_ticker.config.DB_PATH", db_path), \
         patch("stock_ticker.translate.DB_PATH", db_path), \
         patch("stock_ticker.database.DB_PATH", db_path):
        yield db_path


def _mock_ollama_response(translated_text: str) -> MagicMock:
    """Return a context-manager mock that simulates a successful Ollama HTTP response."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"response": translated_text}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_job(src: Path, target: Path, project_root: Path, lang: str = "zh-cn") -> dict:
    return {
        "source_path": str(src.relative_to(project_root)),
        "target_path": str(target.relative_to(project_root)),
        "language": lang,
        "action": "translate",
        "queued_at": time.time(),
        "source_abs": str(src),
        "target_abs": str(target),
    }


# ──────────────────────────────────────────────────────────────────────────────
# split_frontmatter
# ──────────────────────────────────────────────────────────────────────────────

class TestSplitFrontmatter:
    def test_splits_yaml_frontmatter(self):
        fm, body = split_frontmatter(SAMPLE_MD)
        assert fm == SAMPLE_FRONTMATTER
        assert body.startswith("## Introduction")

    def test_no_frontmatter(self):
        text = "## Just a body\n\nNo frontmatter here."
        fm, body = split_frontmatter(text)
        assert fm == ""
        assert body == text

    def test_empty_frontmatter(self):
        text = "---\n---\n\n## Body"
        fm, body = split_frontmatter(text)
        assert fm == "---\n---"
        assert body == "## Body"

    def test_frontmatter_preserved_exactly(self):
        """Full round-trip: frontmatter + body reassembles to original."""
        fm, body = split_frontmatter(SAMPLE_MD)
        reconstructed = fm + "\n\n" + body
        assert reconstructed == SAMPLE_MD


# ──────────────────────────────────────────────────────────────────────────────
# _has_non_empty_body
# ──────────────────────────────────────────────────────────────────────────────

class TestHasNonEmptyBody:
    def test_missing_file(self, tmp_path):
        assert _has_non_empty_body(tmp_path / "missing.zh-cn.md") is False

    def test_empty_body(self, tmp_path):
        f = tmp_path / "empty.zh-cn.md"
        f.write_text(SAMPLE_FRONTMATTER + "\n\n   \n", encoding="utf-8")
        assert _has_non_empty_body(f) is False

    def test_has_body(self, tmp_path):
        f = tmp_path / "with-body.zh-cn.md"
        f.write_text(SAMPLE_MD, encoding="utf-8")
        assert _has_non_empty_body(f) is True


# ──────────────────────────────────────────────────────────────────────────────
# TranslateConfig.effective_workers
# ──────────────────────────────────────────────────────────────────────────────

class TestEffectiveWorkers:
    def test_explicit_workers(self):
        cfg = TranslateConfig(workers=3)
        assert cfg.effective_workers() == 3

    def test_utilization(self):
        cfg = TranslateConfig(utilization=0.5)
        with patch("os.cpu_count", return_value=8):
            assert cfg.effective_workers() == 4

    def test_default_75_percent(self):
        cfg = TranslateConfig()
        with patch("os.cpu_count", return_value=8):
            assert cfg.effective_workers() == 6

    def test_minimum_one_worker(self):
        cfg = TranslateConfig()
        with patch("os.cpu_count", return_value=1):
            assert cfg.effective_workers() == 1


# ──────────────────────────────────────────────────────────────────────────────
# build_job_list
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildJobList:
    def test_finds_untranslated_files(self, tmp_path):
        content_dir = tmp_path / "hugo" / "site" / "content"
        content_dir.mkdir(parents=True)
        (content_dir / "article.md").write_text(SAMPLE_MD, encoding="utf-8")

        cfg = TranslateConfig(languages=["zh-cn"])
        with patch("stock_ticker.translate.CONTENT_DIR", content_dir), \
             patch("stock_ticker.translate.PROJECT_ROOT", tmp_path):
            jobs = build_job_list(cfg)

        translate_jobs = [j for j in jobs if j["action"] == "translate"]
        assert len(translate_jobs) == 1
        assert translate_jobs[0]["language"] == "zh-cn"
        assert translate_jobs[0]["target_path"].endswith("article.zh-cn.md")

    def test_skips_existing_translation(self, tmp_path):
        content_dir = tmp_path / "hugo" / "site" / "content"
        content_dir.mkdir(parents=True)
        (content_dir / "article.md").write_text(SAMPLE_MD, encoding="utf-8")
        (content_dir / "article.zh-cn.md").write_text(SAMPLE_MD, encoding="utf-8")

        cfg = TranslateConfig(languages=["zh-cn"])
        with patch("stock_ticker.translate.CONTENT_DIR", content_dir), \
             patch("stock_ticker.translate.PROJECT_ROOT", tmp_path):
            jobs = build_job_list(cfg)

        assert sum(1 for j in jobs if j["action"] == "skip") == 1
        assert sum(1 for j in jobs if j["action"] == "translate") == 0

    def test_force_re_queues_existing(self, tmp_path):
        content_dir = tmp_path / "hugo" / "site" / "content"
        content_dir.mkdir(parents=True)
        (content_dir / "article.md").write_text(SAMPLE_MD, encoding="utf-8")
        (content_dir / "article.zh-cn.md").write_text(SAMPLE_MD, encoding="utf-8")

        cfg = TranslateConfig(languages=["zh-cn"], force=True)
        with patch("stock_ticker.translate.CONTENT_DIR", content_dir), \
             patch("stock_ticker.translate.PROJECT_ROOT", tmp_path):
            jobs = build_job_list(cfg)

        assert sum(1 for j in jobs if j["action"] == "translate") == 1

    def test_ignores_zh_cn_source_files(self, tmp_path):
        """Translation-variant files (foo.zh-cn.md) are never treated as sources."""
        content_dir = tmp_path / "hugo" / "site" / "content"
        content_dir.mkdir(parents=True)
        (content_dir / "article.md").write_text(SAMPLE_MD, encoding="utf-8")
        (content_dir / "article.zh-cn.md").write_text("", encoding="utf-8")

        cfg = TranslateConfig(languages=["zh-cn"])
        with patch("stock_ticker.translate.CONTENT_DIR", content_dir), \
             patch("stock_ticker.translate.PROJECT_ROOT", tmp_path):
            jobs = build_job_list(cfg)

        source_paths = [j["source_path"] for j in jobs]
        assert not any("article.zh-cn.md" in p for p in source_paths)


# ──────────────────────────────────────────────────────────────────────────────
# translate_job — mocked Ollama
# ──────────────────────────────────────────────────────────────────────────────

class TestTranslateJob:
    def test_frontmatter_preserved(self, tmp_path, temp_db):
        src = tmp_path / "article.md"
        src.write_text(SAMPLE_MD, encoding="utf-8")
        target = tmp_path / "article.zh-cn.md"
        job = _make_job(src, target, tmp_path)

        cfg = TranslateConfig(model="qwen2.5:7b", backend="ollama")
        _insert_run("run-01", cfg, workers=1, total_files=1)
        _insert_job_rows("run-01", [job], cfg.model)

        with patch("urllib.request.urlopen", return_value=_mock_ollama_response(TRANSLATED_BODY)):
            translate_job(job, "run-01", cfg)

        output = target.read_text(encoding="utf-8")
        fm, body = split_frontmatter(output)
        assert fm == SAMPLE_FRONTMATTER, "Frontmatter must be preserved byte-for-byte"
        assert len(body.strip()) > 0

    def test_shortcodes_passthrough(self, tmp_path, temp_db):
        """Hugo shortcodes must survive the translation round-trip."""
        src = tmp_path / "article.md"
        src.write_text(SAMPLE_MD, encoding="utf-8")
        target = tmp_path / "article.zh-cn.md"
        job = _make_job(src, target, tmp_path)

        cfg = TranslateConfig(model="qwen2.5:7b", backend="ollama")
        _insert_run("run-02", cfg, workers=1, total_files=1)
        _insert_job_rows("run-02", [job], cfg.model)

        with patch("urllib.request.urlopen", return_value=_mock_ollama_response(TRANSLATED_BODY)):
            translate_job(job, "run-02", cfg)

        output = target.read_text(encoding="utf-8")
        assert '{{< shortcode param="value" >}}' in output

    def test_ticker_symbols_passthrough(self, tmp_path, temp_db):
        """Ticker symbols (AAPL etc.) must appear unchanged in translated output."""
        src = tmp_path / "article.md"
        src.write_text(SAMPLE_MD, encoding="utf-8")
        target = tmp_path / "article.zh-cn.md"
        job = _make_job(src, target, tmp_path)

        cfg = TranslateConfig(model="qwen2.5:7b", backend="ollama")
        _insert_run("run-03", cfg, workers=1, total_files=1)
        _insert_job_rows("run-03", [job], cfg.model)

        with patch("urllib.request.urlopen", return_value=_mock_ollama_response(TRANSLATED_BODY)):
            translate_job(job, "run-03", cfg)

        output = target.read_text(encoding="utf-8")
        assert "AAPL" in output

    def test_result_contains_timing(self, tmp_path, temp_db):
        """Returned dict includes status, duration, and char counts."""
        src = tmp_path / "article.md"
        src.write_text(SAMPLE_MD, encoding="utf-8")
        target = tmp_path / "article.zh-cn.md"
        job = _make_job(src, target, tmp_path)

        cfg = TranslateConfig(model="qwen2.5:7b", backend="ollama")
        _insert_run("run-04", cfg, workers=1, total_files=1)
        _insert_job_rows("run-04", [job], cfg.model)

        with patch("urllib.request.urlopen", return_value=_mock_ollama_response(TRANSLATED_BODY)):
            result = translate_job(job, "run-04", cfg)

        assert result["status"] == "completed"
        assert isinstance(result["duration"], float)
        assert result["input_chars"] > 0
        assert result["output_chars"] > 0

    def test_db_row_created(self, tmp_path, temp_db):
        """A completed translate_file_jobs row with duration_seconds is written to DB."""
        src = tmp_path / "article.md"
        src.write_text(SAMPLE_MD, encoding="utf-8")
        target = tmp_path / "article.zh-cn.md"
        job = _make_job(src, target, tmp_path)

        cfg = TranslateConfig(model="qwen2.5:7b", backend="ollama")
        _insert_run("run-05", cfg, workers=1, total_files=1)
        _insert_job_rows("run-05", [job], cfg.model)

        with patch("urllib.request.urlopen", return_value=_mock_ollama_response(TRANSLATED_BODY)):
            translate_job(job, "run-05", cfg)

        conn = sqlite3.connect(str(temp_db))
        row = conn.execute(
            "SELECT status, duration_seconds FROM translate_file_jobs"
            " WHERE run_id = 'run-05'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "completed"
        assert row[1] is not None and row[1] > 0


# ──────────────────────────────────────────────────────────────────────────────
# fetch_heuristics
# ──────────────────────────────────────────────────────────────────────────────

class TestFetchHeuristics:
    def _seed_jobs(self, db_path: Path, run_id: str, n: int, durations: list) -> None:
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO translate_runs"
            " (run_id, started_at, languages, model, backend, workers, total_files)"
            " VALUES (?, ?, '[]', 'qwen2.5:7b', 'ollama', 1, ?)",
            (run_id, time.time(), n),
        )
        for i, d in enumerate(durations):
            conn.execute(
                "INSERT INTO translate_file_jobs"
                " (run_id, source_path, target_path, language, model,"
                "  queued_at, status, duration_seconds)"
                " VALUES (?, ?, ?, 'zh-cn', 'qwen2.5:7b', ?, 'completed', ?)",
                (run_id, f"src{i}.md", f"src{i}.zh-cn.md", time.time(), d),
            )
        conn.commit()
        conn.close()

    def test_returns_none_when_insufficient_history(self, temp_db):
        self._seed_jobs(temp_db, "run-h1", 3, [100.0, 120.0, 130.0])
        result = fetch_heuristics("zh-cn", "qwen2.5:7b")
        assert result is None  # 3 < MIN_HISTORY_FOR_ETA (5)

    def test_returns_stats_with_sufficient_history(self, temp_db):
        durations = [100.0, 120.0, 150.0, 80.0, 200.0, 130.0]
        self._seed_jobs(temp_db, "run-h2", len(durations), durations)
        result = fetch_heuristics("zh-cn", "qwen2.5:7b")

        assert result is not None
        assert result["sample_size"] == 6
        assert abs(result["avg_seconds"] - sum(durations) / len(durations)) < 0.01
        assert result["min_seconds"] == 80.0
        assert result["max_seconds"] == 200.0

    def test_ignores_different_model(self, temp_db):
        """Jobs recorded under a different model don't pollute ETA for our model."""
        durations = [50.0] * 6
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO translate_runs"
            " (run_id, started_at, languages, model, backend, workers, total_files)"
            " VALUES ('run-h3', ?, '[]', 'other-model', 'ollama', 1, 6)",
            (time.time(),),
        )
        for i, d in enumerate(durations):
            conn.execute(
                "INSERT INTO translate_file_jobs"
                " (run_id, source_path, target_path, language, model,"
                "  queued_at, status, duration_seconds)"
                " VALUES ('run-h3', ?, ?, 'zh-cn', 'other-model', ?, 'completed', ?)",
                (f"src{i}.md", f"src{i}.zh-cn.md", time.time(), d),
            )
        conn.commit()
        conn.close()

        result = fetch_heuristics("zh-cn", "qwen2.5:7b")
        assert result is None


# ──────────────────────────────────────────────────────────────────────────────
# run_translate — dry run
# ──────────────────────────────────────────────────────────────────────────────

class TestRunTranslateDryRun:
    def test_writes_no_files(self, tmp_path, temp_db):
        content_dir = tmp_path / "hugo" / "site" / "content"
        content_dir.mkdir(parents=True)
        (content_dir / "article.md").write_text(SAMPLE_MD, encoding="utf-8")

        cfg = TranslateConfig(languages=["zh-cn"], dry_run=True, no_heuristics=True)
        with patch("stock_ticker.translate.CONTENT_DIR", content_dir), \
             patch("stock_ticker.translate.PROJECT_ROOT", tmp_path):
            run_translate(cfg)

        assert not (content_dir / "article.zh-cn.md").exists()

    def test_inserts_no_db_rows(self, tmp_path, temp_db):
        content_dir = tmp_path / "hugo" / "site" / "content"
        content_dir.mkdir(parents=True)
        (content_dir / "article.md").write_text(SAMPLE_MD, encoding="utf-8")

        cfg = TranslateConfig(languages=["zh-cn"], dry_run=True, no_heuristics=True)
        with patch("stock_ticker.translate.CONTENT_DIR", content_dir), \
             patch("stock_ticker.translate.PROJECT_ROOT", tmp_path):
            run_translate(cfg)

        conn = sqlite3.connect(str(temp_db))
        count = conn.execute("SELECT COUNT(*) FROM translate_runs").fetchone()[0]
        conn.close()
        assert count == 0

    def test_nothing_to_do_when_all_translated(self, tmp_path, temp_db):
        content_dir = tmp_path / "hugo" / "site" / "content"
        content_dir.mkdir(parents=True)
        # Both source and non-empty translation exist
        (content_dir / "article.md").write_text(SAMPLE_MD, encoding="utf-8")
        (content_dir / "article.zh-cn.md").write_text(SAMPLE_MD, encoding="utf-8")

        cfg = TranslateConfig(languages=["zh-cn"], dry_run=True, no_heuristics=True)
        with patch("stock_ticker.translate.CONTENT_DIR", content_dir), \
             patch("stock_ticker.translate.PROJECT_ROOT", tmp_path):
            run_translate(cfg)  # should not raise


# ──────────────────────────────────────────────────────────────────────────────
# run_translate — second run skips
# ──────────────────────────────────────────────────────────────────────────────

class TestRunTranslateSkip:
    def test_second_run_skips_already_translated(self, tmp_path, temp_db):
        """Running translate twice without --force records second file as skipped."""
        content_dir = tmp_path / "hugo" / "site" / "content"
        content_dir.mkdir(parents=True)
        (content_dir / "article.md").write_text(SAMPLE_MD, encoding="utf-8")

        cfg = TranslateConfig(
            languages=["zh-cn"], workers=1, no_heuristics=True,
            model="qwen2.5:7b", backend="ollama"
        )

        with patch("stock_ticker.translate.CONTENT_DIR", content_dir), \
             patch("stock_ticker.translate.PROJECT_ROOT", tmp_path), \
             patch("urllib.request.urlopen", return_value=_mock_ollama_response(TRANSLATED_BODY)):
            run_translate(cfg)  # first run — translates

        assert (content_dir / "article.zh-cn.md").exists()

        # Second run — file already translated, should be skipped
        with patch("stock_ticker.translate.CONTENT_DIR", content_dir), \
             patch("stock_ticker.translate.PROJECT_ROOT", tmp_path):
            run_translate(cfg)  # should print "Nothing to do."

        conn = sqlite3.connect(str(temp_db))
        rows = conn.execute(
            "SELECT status FROM translate_file_jobs ORDER BY id"
        ).fetchall()
        conn.close()
        statuses = [r[0] for r in rows]
        # First run: completed. Second run: skipped.
        assert "completed" in statuses
        assert "skipped" in statuses


# ──────────────────────────────────────────────────────────────────────────────
# _fmt_duration
# ──────────────────────────────────────────────────────────────────────────────

class TestFmtDuration:
    def test_seconds(self):
        assert _fmt_duration(45) == "45s"

    def test_minutes(self):
        assert _fmt_duration(125) == "2m05s"

    def test_hours(self):
        assert _fmt_duration(3665) == "1h01m"


# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM_PROMPT content
# ──────────────────────────────────────────────────────────────────────────────

class TestSystemPrompt:
    def test_contains_key_rules(self):
        assert "ticker symbols" in SYSTEM_PROMPT
        assert "{{<" in SYSTEM_PROMPT  # shortcode preservation
        assert "frontmatter" in SYSTEM_PROMPT
        assert "Simplified Chinese" in SYSTEM_PROMPT

    def test_no_preamble_instruction(self):
        assert "No explanations" in SYSTEM_PROMPT or "no preamble" in SYSTEM_PROMPT.lower()
