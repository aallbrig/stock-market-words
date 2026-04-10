"""
Translation module for ticker-cli translate.

Translates English markdown content files to Simplified Chinese (zh-CN)
using Ollama (default) or HuggingFace. SQLite-backed job tracking provides
ETA estimates from historical timing data.

Parallelism: concurrent.futures.ThreadPoolExecutor — threads are correct here
because the bottleneck is Ollama I/O (HTTP + inference), not Python CPU.
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request
import logging

from .config import DB_PATH, PROJECT_ROOT
from .database import get_connection

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a professional financial translator. Translate the following English\n"
    "markdown text into Simplified Chinese (zh-CN) suitable for a Singaporean\n"
    "audience reading a stock-market educational website. Rules:\n\n"
    "1. Preserve ALL markdown formatting exactly: headings, bullets, code blocks,\n"
    "   links, tables, Hugo shortcodes ({{< ... >}} and {{% ... %}}).\n"
    "2. Do NOT translate ticker symbols (AAPL, CRM, NVDA), company names, code\n"
    "   snippets, URLs, or anything inside backticks.\n"
    "3. Use established Chinese financial terminology:\n"
    "   - RSI -> \u76f8\u5bf9\u5f3a\u5f31\u6307\u6807 (RSI)\n"
    "   - P/E ratio -> \u5e02\u76c8\u7387\n"
    "   - market cap -> \u5e02\u5024\n"
    "   - dividend yield -> \u80a1\u606f\u6536\u76ca\u7387\n"
    "   - moving average -> \u79fb\u52a8\u5e73\u5747\u7ebf\n"
    "4. Keep frontmatter (the --- block at the top) entirely unchanged. Translate\n"
    "   only the body.\n"
    "5. Output ONLY the translated markdown. No explanations, no preamble."
)

CONTENT_DIR = PROJECT_ROOT / "hugo" / "site" / "content"
TEMP_DIR = PROJECT_ROOT / "temp"
OLLAMA_BASE_URL = "http://localhost:11434"

DEFAULT_MODEL = "qwen2.5:7b"
DEFAULT_BACKEND = "ollama"
DEFAULT_TIMEOUT = 300
DEFAULT_RETRY = 1
MIN_HISTORY_FOR_ETA = 5

# Language codes that appear in translated-file stems (e.g. foo.zh-cn.md)
_LANG_SUFFIXES = {"zh-cn", "ko", "ja", "fr", "de", "es"}

# Size-based ETA speed brackets for qwen2.5:7b (Chinese chars output / second / worker).
# Chinese output chars ≈ English input chars × _ZH_RATIO (Chinese is more compact).
# CPU:  ~1 tok/s × 3 chars/tok = 3 chars/s  (single-threaded Ollama without GPU)
# GPU:  ~20 tok/s × 3 chars/tok = 60 chars/s (mid-range GPU, e.g. RTX 3080)
_ZH_RATIO = 0.35        # empirical: Chinese body is ~35% of English char count
_CPU_CHARS_PER_SEC = 3  # conservative low end for CPU-only inference
_GPU_CHARS_PER_SEC = 60 # optimistic for GPU-accelerated inference


# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class TranslateConfig:
    path: Optional[Path] = None
    languages: List[str] = field(default_factory=lambda: ["zh-cn"])
    workers: Optional[int] = None
    utilization: Optional[float] = None
    timeout_per_file: int = DEFAULT_TIMEOUT
    retry: int = DEFAULT_RETRY
    model: str = DEFAULT_MODEL
    backend: str = DEFAULT_BACKEND
    force: bool = False
    dry_run: bool = False
    no_heuristics: bool = False

    def effective_workers(self) -> int:
        """Compute worker count from --workers or --utilization, defaulting to 75% of CPUs."""
        if self.workers is not None:
            return self.workers
        cpu = os.cpu_count() or 1
        if self.utilization is not None:
            return max(1, math.floor(cpu * self.utilization))
        return max(1, math.floor(cpu * 0.75))


# ──────────────────────────────────────────────────────────────────────────────
# Frontmatter parsing
# ──────────────────────────────────────────────────────────────────────────────

def split_frontmatter(text: str) -> Tuple[str, str]:
    """
    Split markdown text into (frontmatter_block, body).

    frontmatter_block includes both surrounding --- delimiters (no trailing
    newline). Returns ('', text) if the file has no frontmatter.
    """
    if not text.startswith("---"):
        return "", text
    close = text.find("\n---", 3)
    if close == -1:
        return "", text
    # close points to the \n before closing ---; +4 skips \n---
    frontmatter = text[: close + 4]
    body = text[close + 4 :].lstrip("\n")
    return frontmatter, body


def _has_non_empty_body(path: Path) -> bool:
    """Return True if the file exists and has content beyond its frontmatter."""
    if not path.exists():
        return False
    _, body = split_frontmatter(path.read_text(encoding="utf-8"))
    return bool(body.strip())


def _is_translation_file(path: Path) -> bool:
    """Return True if the file is already a language-variant (e.g. foo.zh-cn.md)."""
    stem = path.stem  # "foo.zh-cn" for foo.zh-cn.md
    for lang in _LANG_SUFFIXES:
        if stem.endswith(f".{lang}"):
            return True
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Job list
# ──────────────────────────────────────────────────────────────────────────────

def build_job_list(config: TranslateConfig) -> List[Dict]:
    """
    Walk hugo/site/content/ and return all (source, target, language) pairs.

    Each dict has keys:
      source_path  – relative to PROJECT_ROOT (for DB storage)
      target_path  – relative to PROJECT_ROOT
      language
      action       – 'translate' | 'skip'
      source_abs   – present only when action == 'translate'
      target_abs   – present only when action == 'translate'
      queued_at    – Unix timestamp
    """
    queued_at = time.time()
    jobs: List[Dict] = []

    if config.path:
        sources = [Path(config.path).resolve()]
    else:
        sources = sorted(CONTENT_DIR.rglob("*.md"))

    for src in sources:
        if _is_translation_file(src):
            continue

        for lang in config.languages:
            target = src.with_name(src.stem + f".{lang}.md")

            base: Dict = {
                "source_path": str(src.relative_to(PROJECT_ROOT)),
                "target_path": str(target.relative_to(PROJECT_ROOT)),
                "language": lang,
                "queued_at": queued_at,
            }

            if not config.force and _has_non_empty_body(target):
                base["action"] = "skip"
            else:
                base["action"] = "translate"
                base["source_abs"] = str(src)
                base["target_abs"] = str(target)

            jobs.append(base)

    return jobs


# ──────────────────────────────────────────────────────────────────────────────
# Heuristics / ETA
# ──────────────────────────────────────────────────────────────────────────────

def fetch_heuristics(language: str, model: str) -> Optional[Dict]:
    """
    Query translate_file_jobs for historical timing.
    Returns None if fewer than MIN_HISTORY_FOR_ETA completed jobs exist.
    """
    if not DB_PATH.exists():
        return None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                AVG(duration_seconds),
                MIN(duration_seconds),
                MAX(duration_seconds),
                COUNT(*)
            FROM translate_file_jobs
            WHERE status = 'completed'
              AND language = ?
              AND model = ?
            """,
            (language, model),
        )
        row = cursor.fetchone()
        conn.close()
        if row and row[3] and row[3] >= MIN_HISTORY_FOR_ETA:
            return {
                "avg_seconds": row[0],
                "min_seconds": row[1],
                "max_seconds": row[2],
                "sample_size": row[3],
            }
    except Exception as exc:
        logger.debug("Heuristics query failed: %s", exc)
    return None


def _fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m{int(seconds % 60):02d}s"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h{m:02d}m"


def _size_based_eta(pending: List[Dict], workers: int) -> str:
    """
    Derive a wall-time range from source file sizes when no historical data exists.

    Reads each pending source file, measures body character count, and applies
    two inference speed brackets for qwen2.5:7b:
      CPU (no GPU): ~3 Chinese chars/second  (1 tok/s × 3 chars/tok)
      GPU:          ~60 Chinese chars/second (20 tok/s × 3 chars/tok)

    Chinese output length ≈ English input length × _ZH_RATIO (≈ 0.35): Chinese
    is more compact than English, so output char count is shorter even though
    the same information is conveyed.

    Returns a human-readable range string, e.g.:
      "~3h20m (CPU) – ~10m (GPU), based on 22 files / 45 KB source text"
    """
    total_input_chars = 0
    for job in pending:
        try:
            src_text = Path(job["source_abs"]).read_text(encoding="utf-8")
            _, body = split_frontmatter(src_text)
            total_input_chars += len(body)
        except Exception:
            # Fallback: assume 2000 chars per file if unreadable
            total_input_chars += 2000

    total_output_chars = total_input_chars * _ZH_RATIO

    # Wall time = total output chars / (chars_per_sec_per_worker * workers)
    # (workers translating in parallel, each at the given rate)
    cpu_wall = total_output_chars / (_CPU_CHARS_PER_SEC * 1)   # CPU: effective 1 worker
    gpu_wall = total_output_chars / (_GPU_CHARS_PER_SEC * workers)

    size_kb = total_input_chars / 1024
    return (
        f"~{_fmt_duration(cpu_wall)} (CPU, 1 worker) "
        f"– ~{_fmt_duration(gpu_wall)} (GPU, {workers} workers)\n"
        f"  Based on {len(pending)} files / {size_kb:.0f} KB source text. "
        f"First run will record actual timings for future ETA accuracy."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Ollama backend
# ──────────────────────────────────────────────────────────────────────────────

def _ollama_translate(body: str, model: str, timeout: int) -> str:
    """POST body to Ollama /api/generate; return translated text."""
    payload = json.dumps({
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": body,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data.get("response", "").strip()


# ──────────────────────────────────────────────────────────────────────────────
# HuggingFace backend
# ──────────────────────────────────────────────────────────────────────────────

def _hf_translate(body: str, model: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Translate using HuggingFace transformers (optional extra dependency)."""
    try:
        from transformers import pipeline as hf_pipeline  # type: ignore
    except ImportError:
        raise ImportError(
            "HuggingFace backend requires: pip install 'stock-ticker-cli[hf]'"
        )
    pipe = hf_pipeline("translation", model=model)
    result = pipe(body, max_length=4096)
    return result[0]["translation_text"]


# ──────────────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────────────

def _insert_run(run_id: str, config: TranslateConfig, workers: int, total_files: int) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO translate_runs
            (run_id, started_at, status, languages, model, backend, workers, total_files)
        VALUES (?, ?, 'running', ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            time.time(),
            json.dumps(config.languages),
            config.model,
            config.backend,
            workers,
            total_files,
        ),
    )
    conn.commit()
    conn.close()


def _insert_job_rows(run_id: str, jobs: List[Dict], model: str) -> None:
    conn = get_connection()
    for job in jobs:
        db_status = "skipped" if job["action"] == "skip" else "queued"
        conn.execute(
            """
            INSERT INTO translate_file_jobs
                (run_id, source_path, target_path, language, model, queued_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                job["source_path"],
                job["target_path"],
                job["language"],
                model,
                job["queued_at"],
                db_status,
            ),
        )
    conn.commit()
    conn.close()


def _update_job(run_id: str, source_path: str, language: str, updates: Dict) -> None:
    if not updates:
        return
    conn = get_connection()
    set_clauses = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [run_id, source_path, language]
    conn.execute(
        f"UPDATE translate_file_jobs SET {set_clauses}"
        f" WHERE run_id = ? AND source_path = ? AND language = ?",
        values,
    )
    conn.commit()
    conn.close()


def _update_run(run_id: str, updates: Dict) -> None:
    if not updates:
        return
    conn = get_connection()
    set_clauses = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [run_id]
    conn.execute(
        f"UPDATE translate_runs SET {set_clauses} WHERE run_id = ?",
        values,
    )
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Single-file translation job
# ──────────────────────────────────────────────────────────────────────────────

def translate_job(job: Dict, run_id: str, config: TranslateConfig) -> Dict:
    """
    Translate one (source_file, language) pair.

    Updates translate_file_jobs row in SQLite throughout execution.
    Raises on failure so the caller can handle retries.
    """
    started_at = time.time()
    thread_id = threading.get_ident()

    _update_job(run_id, job["source_path"], job["language"], {
        "status": "running",
        "started_at": started_at,
        "worker_id": thread_id,
    })

    src_text = Path(job["source_abs"]).read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(src_text)
    input_chars = len(body)

    if config.backend == "ollama":
        translated_body = _ollama_translate(body, config.model, config.timeout_per_file)
    elif config.backend == "huggingface":
        translated_body = _hf_translate(body, config.model, config.timeout_per_file)
    else:
        raise ValueError(f"Unknown backend: {config.backend!r}")

    output_chars = len(translated_body)

    if frontmatter:
        output_text = frontmatter + "\n\n" + translated_body
    else:
        output_text = translated_body

    target = Path(job["target_abs"])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(output_text, encoding="utf-8")

    duration = time.time() - started_at
    _update_job(run_id, job["source_path"], job["language"], {
        "status": "completed",
        "completed_at": time.time(),
        "duration_seconds": duration,
        "input_chars": input_chars,
        "output_chars": output_chars,
    })

    return {
        "status": "completed",
        "source_path": job["source_path"],
        "target_path": job["target_path"],
        "duration": duration,
        "input_chars": input_chars,
        "output_chars": output_chars,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ──────────────────────────────────────────────────────────────────────────────

def run_translate(config: TranslateConfig) -> None:
    """
    Build the job list, print ETA, run translations in parallel, write summary.
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    workers = config.effective_workers()
    all_jobs = build_job_list(config)
    pending = [j for j in all_jobs if j["action"] == "translate"]
    skipped = [j for j in all_jobs if j["action"] == "skip"]

    languages_str = ", ".join(config.languages)
    print(f"Found {len(pending)} file(s) to translate into {languages_str}.")
    if skipped:
        print(f"Skipping {len(skipped)} already-translated file(s). (use --force to re-translate)")

    # ── ETA (shown for both dry-run and real runs) ────────────────────────────
    if pending and not config.no_heuristics:
        h = fetch_heuristics(config.languages[0], config.model)
        if h:
            avg = h["avg_seconds"]
            wall = math.ceil(len(pending) / workers) * avg
            print(
                f"Historical avg: {_fmt_duration(avg)}/file"
                f" (based on {h['sample_size']} past jobs, model {config.model})."
            )
            print(f"Estimated wall time with {workers} workers: ~{_fmt_duration(wall)}.")
        else:
            print(f"Estimated wall time: {_size_based_eta(pending, workers)}")

    # ── Dry run ──────────────────────────────────────────────────────────────
    if config.dry_run:
        if pending:
            print("\nFiles that would be translated:")
            for job in pending:
                print(f"  {job['source_path']} -> {job['target_path']}")
        print("\nDry run complete — no files written, no DB rows inserted.")
        return

    if not pending:
        # Record skipped files so heuristics and audit logs stay accurate
        if skipped:
            run_id = str(uuid.uuid4())
            _insert_run(run_id, config, workers, 0)
            _insert_job_rows(run_id, all_jobs, config.model)
            _update_run(run_id, {
                "completed_at": time.time(),
                "status": "completed",
                "skipped_files": len(skipped),
            })
        print("Nothing to do.")
        return

    # ── CPU-only Ollama warning ───────────────────────────────────────────────
    if config.backend == "ollama" and workers > 2:
        print(
            f"Note: For CPU-only Ollama, --workers 2 is the practical optimum.\n"
            f"      GPU-accelerated or API backends scale better with {workers} workers."
        )

    print(f"Starting...\n")

    # ── DB setup ─────────────────────────────────────────────────────────────
    run_id = str(uuid.uuid4())
    _insert_run(run_id, config, workers, len(pending))
    _insert_job_rows(run_id, all_jobs, config.model)

    # ── Log file ─────────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = TEMP_DIR / f"translate-{ts}.log"

    results: List[Dict] = []
    run_start = time.time()

    try:
        from tqdm import tqdm  # type: ignore
        progress = tqdm(total=len(pending), unit="file", desc="Translating")
        use_tqdm = True
    except ImportError:
        progress = None
        use_tqdm = False

    def _emit(msg: str) -> None:
        if use_tqdm and progress:
            progress.write(msg)
        else:
            print(msg)

    def _run_with_retry(job: Dict) -> Dict:
        last_exc: Optional[Exception] = None
        for attempt in range(1, config.retry + 2):
            if attempt > 1:
                _emit(f"  ↺ Retrying {Path(job['source_path']).name} (attempt {attempt})")
                # Update attempt count in DB
                _update_job(run_id, job["source_path"], job["language"], {
                    "attempt": attempt,
                    "status": "queued",
                })
            try:
                return translate_job(job, run_id, config)
            except Exception as exc:
                last_exc = exc
        raise last_exc  # type: ignore[misc]

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_with_retry, job): job for job in pending}
        for future in as_completed(futures):
            job = futures[future]
            try:
                result = future.result()
                results.append(result)
                name = Path(result["target_path"]).name
                _emit(f"  \u2713 {name}  ({_fmt_duration(result['duration'])})")
            except Exception as exc:
                results.append({
                    "status": "failed",
                    "source_path": job["source_path"],
                    "target_path": job["target_path"],
                    "error": str(exc),
                })
                name = Path(job["target_path"]).name
                _emit(f"  \u2717 {name}  ({exc})")
            finally:
                if use_tqdm and progress:
                    progress.update(1)

    if use_tqdm and progress:
        progress.close()

    wall_time = time.time() - run_start
    completed = [r for r in results if r.get("status") == "completed"]
    failed = [r for r in results if r.get("status") == "failed"]

    final_status = "completed" if not failed else ("partial" if completed else "failed")
    _update_run(run_id, {
        "completed_at": time.time(),
        "status": final_status,
        "completed_files": len(completed),
        "failed_files": len(failed),
        "skipped_files": len(skipped),
    })

    # ── Write log ─────────────────────────────────────────────────────────────
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Translation run {run_id}\n")
        f.write(f"Model: {config.model}  Backend: {config.backend}  Workers: {workers}\n")
        f.write(f"Wall time: {_fmt_duration(wall_time)}\n\n")
        for r in results:
            if r.get("status") == "completed":
                f.write(f"OK   {r['source_path']}  ({_fmt_duration(r['duration'])})\n")
            else:
                f.write(f"ERR  {r['source_path']}  {r.get('error', '?')}\n")
        if skipped:
            f.write("\nSkipped (already translated):\n")
            for j in skipped:
                f.write(f"SKIP {j['source_path']}\n")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\nTranslation run complete.")
    print(f"  Completed: {len(completed)}/{len(pending)}")
    failed_line = f"  Failed:    {len(failed)}/{len(pending)}"
    if failed:
        print(f"{failed_line}  (see {log_path})")
    else:
        print(failed_line)
    print(f"  Wall time: {_fmt_duration(wall_time)}")
    print(f"  Workers:   {workers}")
    print(f"  Model:     {config.model}")
