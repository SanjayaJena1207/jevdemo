"""Records N races in the running app as a video, plus screenshots and raw results.

Prereqs: backend on :8010 and frontend on :5173 already running.
    pip install playwright imageio-ffmpeg
    python tools/record_demo.py --races 3

Outputs (docs/demo/): race-demo.mp4, race-N.png, races.json
Uses the locally installed Chrome (or Edge), so no Playwright browser download is needed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "demo"
SIZE = {"width": 1280, "height": 900}

# Forward every race_end SSE payload to Python so we keep the exact results.
CAPTURE_JS = """
(() => {
  const Orig = window.EventSource;
  window.EventSource = class extends Orig {
    constructor(...args) {
      super(...args);
      this.addEventListener("race_end", (e) => window.__raceEnd(e.data));
    }
  };
})();
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--races", type=int, default=3)
    ap.add_argument("--url", default="http://localhost:5173")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    races: list[dict] = []

    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:  # noqa: BLE001
            browser = p.chromium.launch(channel="msedge")
        ctx = browser.new_context(viewport=SIZE, record_video_dir=tmp, record_video_size=SIZE)
        ctx.expose_function("__raceEnd", lambda data: races.append(json.loads(data)))
        ctx.add_init_script(CAPTURE_JS)
        page = ctx.new_page()
        page.goto(args.url)
        page.get_by_text("Prices").wait_for()
        page.wait_for_timeout(1500)

        button = page.locator("header button")
        for i in range(1, args.races + 1):
            page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            page.wait_for_timeout(800)
            button.click()
            page.get_by_text("Racing…").wait_for()
            page.get_by_text("Race results").wait_for(timeout=180_000)
            page.wait_for_timeout(2500)  # let the finish animations land
            page.get_by_text("Race results").scroll_into_view_if_needed()
            page.evaluate("window.scrollBy({top: 250, behavior: 'smooth'})")
            page.wait_for_timeout(3500)
            page.screenshot(path=OUT / f"race-{i}.png", full_page=True)
            print(f"race {i}: winner={races[-1]['winner'] if races else '?'}")

        page.get_by_text("Championship").scroll_into_view_if_needed()
        page.wait_for_timeout(3000)
        video_path = page.video.path()
        ctx.close()
        browser.close()
        webm = OUT / "race-demo.webm"
        shutil.copy(video_path, webm)

    (OUT / "races.json").write_text(json.dumps(races, indent=2), encoding="utf-8")
    mp4 = OUT / "race-demo.mp4"
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(webm),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "28", "-movflags", "+faststart", str(mp4)],
        check=True,
    )
    webm.unlink()
    print(f"saved {mp4} ({mp4.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
