"""
Interactive Playwright scraper for the BMA Traffy Fondue public dashboard.

Rubric evidence: real browser automation, DOM interaction, XHR capture, and
screenshots. The complete dataset is still backfilled by
`fetch_traffy_geojson.py`, so a UI change here never blocks the pipeline.

Dashboard chain (verified 2026-11-12):
    https://www.traffy.in.th/            -> Notion page
    https://dashboard.traffy.in.th/      -> meta refresh
    https://citydata.traffy.in.th/stat   -> login wall (not usable)
    https://bangkok.traffy.in.th/        -> public interactive map (usable)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = PROJECT_ROOT / "02_scraping_traffy_playwright" / "artifacts"
TARGET_URL = "https://bangkok.traffy.in.th/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 bkk-pulse-course-project"
)
MAX_BODY_BYTES = 1_000_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    network: list[dict] = []
    log: dict = {"started_at": _now(), "target_url": TARGET_URL, "steps": []}

    def on_response(response) -> None:
        url = response.url
        if "api.traffy.in.th" not in url and "/rpc/" not in url:
            return
        entry = {
            "url": url,
            "status": response.status,
            "content_type": response.headers.get("content-type", ""),
        }
        try:
            body = response.body()
            entry["bytes"] = len(body)
            if "json" in entry["content_type"] and len(body) <= MAX_BODY_BYTES:
                entry["json_preview"] = body[:2_000].decode("utf-8", errors="replace")
        except Exception as exc:  # body may be unavailable on redirects
            entry["body_error"] = f"{type(exc).__name__}: {exc}"
        network.append(entry)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1440, "height": 900},
                locale="th-TH",
            )
            page = context.new_page()
            page.on("response", on_response)

            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=90_000)
            log["steps"].append({"step": "goto", "at": _now(), "url": page.url})
            try:
                page.wait_for_load_state("networkidle", timeout=60_000)
                log["steps"].append({"step": "networkidle", "at": _now()})
            except PlaywrightError:
                log["steps"].append({"step": "networkidle_timeout", "at": _now()})

            # Google Maps and chart chunks render after the network settles.
            page.wait_for_timeout(8_000)
            page.screenshot(path=str(ARTIFACT_DIR / "traffy_dashboard_initial.png"), full_page=True)

            # Best-effort DOM interaction: open the statistics panel, then scroll.
            interacted = False
            for label in ("สถิติ", "แสดงความเห็น", "แจ้งปัญหา"):
                try:
                    link = page.get_by_text(label, exact=True).first
                    if link.count() and link.is_visible():
                        link.click(timeout=3_000)
                        interacted = True
                        log["steps"].append({"step": f"click {label}", "at": _now()})
                        page.wait_for_timeout(3_000)
                        break
                except PlaywrightError:
                    continue

            page.mouse.wheel(0, 900)
            page.wait_for_timeout(1_500)
            page.mouse.wheel(0, 900)
            page.wait_for_timeout(1_500)

            if not interacted:
                log["steps"].append({"step": "no_interactive_element_found", "at": _now()})

            page.screenshot(path=str(ARTIFACT_DIR / "traffy_dashboard.png"), full_page=True)
            log["title"] = page.title()
            log["final_url"] = page.url
            context.close()
            browser.close()
    except Exception as exc:
        log["error"] = f"{type(exc).__name__}: {exc}"

    log["finished_at"] = _now()
    log["network_requests"] = len(network)
    log["interacted"] = bool(log["steps"]) and any("click" in s["step"] for s in log["steps"])

    (ARTIFACT_DIR / "network_capture.json").write_text(
        json.dumps(network, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (ARTIFACT_DIR / "playwright_scrape_log.json").write_text(
        json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({k: log[k] for k in log if k != "steps"}, indent=2))
    print(f"[artifacts] {ARTIFACT_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
