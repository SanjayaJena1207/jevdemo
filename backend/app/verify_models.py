"""Checks configured model IDs against each provider's GET /models.

Run:  python -m app.verify_models
"""

from __future__ import annotations

import asyncio
import difflib

import httpx

from .config import MODELS


async def verify() -> list[dict]:
    by_endpoint: dict[tuple[str, str | None], list] = {}
    for m in MODELS:
        by_endpoint.setdefault((m.base_url.rstrip("/"), m.api_key), []).append(m)

    report = []
    async with httpx.AsyncClient(timeout=10) as http:
        for (base, key), models in by_endpoint.items():
            available: list[str] | None = None
            error = None
            if key is None:
                error = f"missing {models[0].api_key_env}"
            else:
                try:
                    resp = await http.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"})
                    resp.raise_for_status()
                    available = [d["id"] for d in resp.json().get("data", [])]
                except Exception as e:  # noqa: BLE001
                    error = f"{type(e).__name__}: {e}"[:200]
            for m in models:
                entry = {"model_id": m.id, "model": m.model, "base_url": m.base_url,
                         "found": None, "suggestions": [], "error": error}
                if available is not None:
                    # Gemini lists IDs as "models/gemini-..."
                    ids = {a.removeprefix("models/") for a in available}
                    entry["found"] = m.model in ids
                    if not entry["found"]:
                        entry["suggestions"] = difflib.get_close_matches(m.model, list(ids), n=5, cutoff=0.3)
                report.append(entry)
    return report


def main() -> None:
    for e in asyncio.run(verify()):
        if e["error"]:
            status = f"?  could not check ({e['error']})"
        elif e["found"]:
            status = "OK"
        else:
            status = f"NOT FOUND - did you mean: {', '.join(e['suggestions']) or '(no close match)'}"
        print(f"{e['model_id']:<14} {e['model']:<28} {status}")


if __name__ == "__main__":
    main()
