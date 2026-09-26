"""Running scoreboard across races, persisted to data/scoreboard.json."""

from __future__ import annotations

import json
import threading

from .config import DATA_DIR, MODELS

FILE = DATA_DIR / "scoreboard.json"
_lock = threading.Lock()


def _empty() -> dict:
    return {"races": 0, "models": {}}


def _load() -> dict:
    if FILE.exists():
        try:
            return json.loads(FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return _empty()


_state = _load()


def _entry(model_id: str) -> dict:
    return _state["models"].setdefault(model_id, {
        "races": 0, "wins": 0, "correct": 0, "wrong": 0, "errors": 0,
        "tps_sum": 0.0, "tps_count": 0, "time_sum": 0.0, "time_count": 0,
        "total_cost": 0.0, "total_tokens": 0,
    })


def view() -> dict:
    rows = []
    for m in MODELS:
        e = _entry(m.id)
        rows.append({
            "model_id": m.id,
            "races": e["races"],
            "wins": e["wins"],
            "correct": e["correct"],
            "wrong": e["wrong"],
            "errors": e["errors"],
            "avg_tokens_per_sec": e["tps_sum"] / e["tps_count"] if e["tps_count"] else None,
            "avg_total_time": e["time_sum"] / e["time_count"] if e["time_count"] else None,
            "total_cost": e["total_cost"],
            "total_tokens": e["total_tokens"],
        })
    return {"races": _state["races"], "rows": rows}


def record(results: list[dict], winner: str | None) -> dict:
    with _lock:
        _state["races"] += 1
        for r in results:
            e = _entry(r["model_id"])
            e["races"] += 1
            e["wins"] += int(r["model_id"] == winner)
            e[{"ok": "correct", "wrong": "wrong"}.get(r["status"], "errors")] += 1
            if r["tokens_per_sec"]:
                e["tps_sum"] += r["tokens_per_sec"]
                e["tps_count"] += 1
            if r["status"] != "error":
                e["time_sum"] += r["total_time"]
                e["time_count"] += 1
            e["total_cost"] += r["cost"]
            e["total_tokens"] += r["prompt_tokens"] + r["completion_tokens"]
        FILE.write_text(json.dumps(_state, indent=2), encoding="utf-8")
        return view()


def reset() -> dict:
    global _state
    with _lock:
        _state = _empty()
        FILE.unlink(missing_ok=True)
        return view()
