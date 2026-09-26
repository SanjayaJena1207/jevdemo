"""Loads models.json, API keys from .env, and persisted price overrides."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import truststore
from dotenv import load_dotenv

# Use the OS certificate store so TLS works behind antivirus/corporate HTTPS inspection.
truststore.inject_into_ssl()

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
MODELS_FILE = BACKEND_DIR / "models.json"
PRICES_FILE = DATA_DIR / "prices.json"

load_dotenv(BACKEND_DIR / ".env")
DATA_DIR.mkdir(exist_ok=True)


@dataclass
class ModelConfig:
    id: str
    name: str
    model: str
    base_url: str
    api_key_env: str | None
    color: str
    price_input_per_m: float
    price_output_per_m: float
    kind: str = "chat"  # "chat" (streaming) | "jev" (TypeSafe decision model)

    @property
    def api_key(self) -> str | None:
        if not self.api_key_env:
            return "ollama"  # local servers ignore the key but the SDK requires one
        return os.getenv(self.api_key_env) or None

    def public(self) -> dict:
        """Safe-to-share view (never includes the key itself)."""
        d = asdict(self)
        d["has_key"] = self.api_key is not None
        return d


@dataclass
class RaceSettings:
    timeout_seconds: float = 90
    connect_timeout_seconds: float = 8
    max_tokens: int = 2048


def _load() -> tuple[RaceSettings, list[ModelConfig]]:
    raw = json.loads(MODELS_FILE.read_text(encoding="utf-8"))
    settings = RaceSettings(**raw.get("race", {}))
    models = [ModelConfig(**m) for m in raw["models"]]
    if PRICES_FILE.exists():
        overrides = json.loads(PRICES_FILE.read_text(encoding="utf-8"))
        for m in models:
            if m.id in overrides:
                m.price_input_per_m = float(overrides[m.id]["input"])
                m.price_output_per_m = float(overrides[m.id]["output"])
    return settings, models


SETTINGS, MODELS = _load()
MODELS_BY_ID = {m.id: m for m in MODELS}


def set_price(model_id: str, input_per_m: float, output_per_m: float) -> ModelConfig:
    m = MODELS_BY_ID[model_id]
    m.price_input_per_m = max(0.0, float(input_per_m))
    m.price_output_per_m = max(0.0, float(output_per_m))
    PRICES_FILE.write_text(
        json.dumps(
            {x.id: {"input": x.price_input_per_m, "output": x.price_output_per_m} for x in MODELS},
            indent=2,
        ),
        encoding="utf-8",
    )
    return m
