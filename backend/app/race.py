"""Runs one race: streams the same prompt to every model concurrently and emits events."""

from __future__ import annotations

import asyncio
import json
import math
import time
import uuid
from typing import Any, AsyncIterator, Callable

import httpx
from openai import AsyncOpenAI

from .config import MODELS, SETTINGS, ModelConfig
from .questions import Question, extract_answer, is_correct, random_question, to_letter
from . import scoreboard

Emit = Callable[[dict], None]

PROGRESS_EMIT_INTERVAL = 0.05  # seconds between progress events per car
EXPECTED_TOKENS = 60  # tokens at which a car is ~63% of the way down the track


def _progress(tokens: int) -> float:
    # Cars move with every token but only reach the line when the stream completes.
    return 0.95 * (1 - math.exp(-tokens / EXPECTED_TOKENS))


def _cost(m: ModelConfig, prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens * m.price_input_per_m + completion_tokens * m.price_output_per_m) / 1_000_000


def _reasoning_text(delta: Any) -> str:
    """Reasoning models expose thinking under various non-standard fields."""
    for attr in ("reasoning_content", "reasoning"):
        val = getattr(delta, attr, None)
        if val is None and delta.model_extra:
            val = delta.model_extra.get(attr)
        if isinstance(val, str) and val:
            return val
    return ""


class ConfigError(Exception):
    pass


def _short_error(e: BaseException) -> str:
    if isinstance(e, ConfigError):
        return str(e)
    if isinstance(e, (asyncio.TimeoutError, TimeoutError, httpx.TimeoutException)):
        return f"Timed out after {SETTINGS.timeout_seconds:.0f}s"
    name = type(e).__name__
    msg = str(e) or name
    if "Connection" in name or "connect" in msg.lower():
        return "Unreachable (connection failed)"
    status = getattr(e, "status_code", None)
    body = getattr(e, "body", None)
    if isinstance(body, dict):
        msg = (body.get("error") or {}).get("message", msg) if isinstance(body.get("error"), dict) else body.get("message", msg)
    return f"{status or name}: {msg}"[:240]


def _grade(q: Question, r: dict, letter: str | None, raw: str) -> None:
    r["answer"] = f"{letter}) {q.options[letter]}" if letter else raw
    r["correct"] = is_correct(q, letter)
    r["status"] = "ok" if r["correct"] else "wrong"


async def _ask_jev(client: AsyncOpenAI, m: ModelConfig, q: Question, r: dict, start: float) -> None:
    """Jev is a decision model: no free text and no streaming. It picks one of the
    options via response_format {"type": "questions"} and returns JSON answers."""
    resp = await client.chat.completions.create(
        model=m.model,
        messages=[{"role": "user", "content": q.text}],
        response_format={  # type: ignore[arg-type]  # KodeKloud/LiteLLM extension
            "type": "questions",
            "questions": {"answer": {"type": "choice", "instructions": q.text, "criteria": q.options}},
        },
    )
    r["ttft"] = time.perf_counter() - start  # whole answer arrives at once
    content = resp.choices[0].message.content or ""
    r["content"] = content
    if resp.usage:
        r["usage_reported"] = True
        r["prompt_tokens"] = resp.usage.prompt_tokens or 0
        r["completion_tokens"] = resp.usage.completion_tokens or 0
    try:
        ans = json.loads(content)["answer"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise RuntimeError(f"Unexpected Jev response: {content[:120]!r}") from None
    r["confidence"] = ans.get("confidence")
    letter = ans.get("choice")
    _grade(q, r, letter if letter in q.options else None, str(letter))


async def run_model(m: ModelConfig, q: Question, emit: Emit) -> dict:
    """Runs one model. Always returns a result dict and never raises."""
    start = time.perf_counter()
    r: dict[str, Any] = {
        "model_id": m.id,
        "status": "error",  # ok | wrong | error
        "ttft": None,
        "total_time": None,
        "tokens_per_sec": None,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "usage_reported": False,
        "cost": 0.0,
        "answer": "",
        "confidence": None,
        "content": "",
        "correct": False,
        "error": None,
    }
    content, reasoning_chars, chunks = [], 0, 0
    first_at: float | None = None
    last_emit = 0.0
    usage = None

    try:
        if m.api_key is None:
            raise ConfigError(f"Missing {m.api_key_env} in backend/.env")
        client = AsyncOpenAI(
            base_url=m.base_url,
            api_key=m.api_key,
            max_retries=0,
            timeout=httpx.Timeout(SETTINGS.timeout_seconds, connect=SETTINGS.connect_timeout_seconds),
        )
        if m.kind == "jev":
            async with asyncio.timeout(SETTINGS.timeout_seconds):
                await _ask_jev(client, m, q, r, start)
            return r
        async with asyncio.timeout(SETTINGS.timeout_seconds):
            stream = await client.chat.completions.create(
                model=m.model,
                messages=[{"role": "user", "content": q.prompt}],
                stream=True,
                stream_options={"include_usage": True},
                max_tokens=SETTINGS.max_tokens,
                temperature=0,
            )
            async for chunk in stream:
                if chunk.usage:
                    usage = chunk.usage
                for choice in chunk.choices:
                    text = choice.delta.content or ""
                    think = _reasoning_text(choice.delta)
                    if not (text or think):
                        continue
                    if first_at is None:
                        first_at = time.perf_counter()
                        r["ttft"] = first_at - start
                    chunks += 1
                    content.append(text)
                    reasoning_chars += len(think)
                now = time.perf_counter()
                if chunks and now - last_emit >= PROGRESS_EMIT_INTERVAL:
                    last_emit = now
                    live = max(chunks, (sum(map(len, content)) + reasoning_chars) // 4)
                    emit({"type": "progress", "model_id": m.id, "tokens": live,
                          "progress": _progress(live), "ttft": r["ttft"],
                          "elapsed": now - start})
            await client.close()

        full = "".join(content)
        r["content"] = full
        if usage:
            r["usage_reported"] = True
            r["prompt_tokens"] = usage.prompt_tokens or 0
            r["completion_tokens"] = usage.completion_tokens or 0
        else:  # estimate (~4 chars/token) when the provider doesn't report usage
            r["prompt_tokens"] = len(q.prompt) // 4
            r["completion_tokens"] = max(chunks, (len(full) + reasoning_chars) // 4)
        _grade(q, r, to_letter(q, extract_answer(full)), extract_answer(full))
        if not full.strip():
            r["status"], r["error"] = "error", "Empty response"
    except asyncio.CancelledError:
        raise
    except BaseException as e:  # noqa: BLE001 - one car failing must never stop the race
        r["error"] = _short_error(e)
        r["content"] = "".join(content)
        r["completion_tokens"] = max(chunks, (len(r["content"]) + reasoning_chars) // 4)
        r["prompt_tokens"] = len(q.prompt) // 4 if chunks else 0
    finally:
        end = time.perf_counter()
        r["total_time"] = end - start
        if r["ttft"] is not None and r["completion_tokens"] and m.kind != "jev":
            gen = max(end - (first_at or end), 1e-3)
            r["tokens_per_sec"] = r["completion_tokens"] / gen
        r["cost"] = _cost(m, r["prompt_tokens"], r["completion_tokens"])
    return r


def _sse(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"


async def race_events(model_ids: list[str] | None = None) -> AsyncIterator[str]:
    """Async generator of SSE frames for one full race."""
    racers = [m for m in MODELS if not model_ids or m.id in model_ids]
    q = random_question()
    race_id = uuid.uuid4().hex[:8]
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def lane(m: ModelConfig) -> None:
        res = await run_model(m, q, queue.put_nowait)
        queue.put_nowait({"type": "finish", **res})

    yield _sse({"type": "race_start", "race_id": race_id, "question": q.public(),
                "lanes": [m.id for m in racers]})
    tasks = [asyncio.create_task(lane(m)) for m in racers]
    results: list[dict] = []
    try:
        while len(results) < len(racers):
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
                continue
            if ev["type"] == "finish":
                ev["finish_order"] = len(results) + 1
                results.append(ev)
            yield _sse(ev)

        winners = sorted((r for r in results if r["correct"]), key=lambda r: r["total_time"])
        winner = winners[0]["model_id"] if winners else None
        board = scoreboard.record(results, winner)
        yield _sse({"type": "race_end", "race_id": race_id, "question": q.public(),
                    "winner": winner, "results": results, "scoreboard": board})
    finally:
        for t in tasks:
            t.cancel()
