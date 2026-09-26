"""FastAPI app: config, prices, scoreboard, and the SSE race stream."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import scoreboard
from .config import MODELS, MODELS_BY_ID, SETTINGS, set_price
from .race import race_events
from .verify_models import verify

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await _check_models()
    yield


app = FastAPI(title="LLM Grand Prix", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _check_models() -> None:
    try:
        for e in await verify():
            if e["error"]:
                log.warning("model %s: could not verify ID (%s)", e["model_id"], e["error"])
            elif not e["found"]:
                log.warning("model %s: ID %r not listed by provider. Close matches: %s",
                            e["model_id"], e["model"], e["suggestions"])
    except Exception as ex:  # noqa: BLE001
        log.warning("model verification skipped: %s", ex)


@app.get("/api/config")
def get_config() -> dict:
    return {"models": [m.public() for m in MODELS], "race": vars(SETTINGS)}


class PriceUpdate(BaseModel):
    input: float = Field(ge=0)
    output: float = Field(ge=0)


@app.put("/api/prices/{model_id}")
def update_price(model_id: str, body: PriceUpdate) -> dict:
    if model_id not in MODELS_BY_ID:
        raise HTTPException(404, "unknown model")
    return set_price(model_id, body.input, body.output).public()


@app.get("/api/verify-models")
async def verify_models() -> list[dict]:
    return await verify()


@app.get("/api/scoreboard")
def get_scoreboard() -> dict:
    return scoreboard.view()


@app.post("/api/scoreboard/reset")
def reset_scoreboard() -> dict:
    return scoreboard.reset()


@app.get("/api/race/stream")
async def race_stream(models: str | None = Query(None, description="comma-separated model ids")):
    ids = [s for s in (models or "").split(",") if s] or None
    return StreamingResponse(
        race_events(ids),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
