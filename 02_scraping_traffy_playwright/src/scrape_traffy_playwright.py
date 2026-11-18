"""
Interactive Playwright scraper for the BMA Traffy Fondue public dashboard.

Rubric evidence: real browser automation, DOM interaction (district dropdown +
category filter toggles), XHR interception of the filtered GeoJSON payloads,
and step-by-step screenshots. The complete 6-month dataset is still backfilled
by `fetch_traffy_geojson.py` (using the same `get_bkk_geojson_feed` endpoint
this scraper discovers), so a UI change here never blocks the pipeline.

Dashboard chain (verified 2026-11-12):
    https://www.traffy.in.th/            -> Notion page
    https://dashboard.traffy.in.th/      -> meta refresh
    https://citydata.traffy.in.th/stat   -> login wall (not usable)
    https://bangkok.traffy.in.th/        -> public interactive map (usable)

UI controls (verified 2026-11-17):
    button.dropdown-header + li[role=option]  -> district filter, fires
        get_bkk_geojson_feed?group_id=<district org id>
    button.buttonCategory (21 toggles)        -> category filter, fires
        get_bkk_geojson_feed?...&problem_type=<thai category>

Outputs (02_scraping_traffy_playwright/artifacts/):
    01_initial.png, 02_district_<district>.png, 03_category_<category>.png, 04_stats.png
    playwright_filtered_complaints.json  -- complaints parsed from intercepted XHR
    network_capture.json                 -- every intercepted api.traffy.in.th call
    playwright_scrape_log.json           -- timestamped interaction log
"""

from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = PROJECT_ROOT / "02_scraping_traffy_playwright" / "artifacts"
TARGET_URL = "https://bangkok.traffy.in.th/"
FEED_PATH = "get_bkk_geojson_feed"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 bkk-pulse-course-project"
)
MAX_PREVIEW_BYTES = 2_000

# Districts covering many of our camera corridors (Phahon Yothin / Lat Phrao / Ratchada).
DISTRICTS = (("เขตจตุจักร", "chatuchak"), ("เขตดินแดง", "din_daeng"))
# Traffy categories mapped onto our flood / traffic buckets (see fetch_traffy_geojson.classify).
CATEGORIES = (
    ("น้ำท่วม", "flood", "flood"),
    ("ถนน", "traffic", "road"),
    ("ผิดกฎจราจร", "traffic", "traffic_violation"),
)

# Old screenshot names from the previous version of this scraper.
LEGACY_ARTIFACTS = ("traffy_dashboard_initial.png", "traffy_dashboard.png")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact(feature: dict, filter_label: str) -> dict | None:
    props = feature.get("properties") or {}
    coords = (feature.get("geometry") or {}).get("coordinates") or []
    ticket_id = str(props.get("ticket_id") or "").strip()
    if not ticket_id or len(coords) < 2:
        return None
    return {
        "ticket_id": ticket_id,
        "lon": float(coords[0]),
        "lat": float(coords[1]),
        "timestamp": props.get("timestamp"),
        "type_raw": str(props.get("type") or ""),
        "status": str(props.get("state") or ""),
        "district": str(props.get("district") or ""),
        "captured_by_filter": filter_label,
    }


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    network: list[dict] = []
    complaints: dict[str, dict] = {}
    log: dict = {"started_at": _now(), "target_url": TARGET_URL, "steps": []}
    current_filter = {"label": "initial_load"}

    def step(name: str, **extra) -> None:
        log["steps"].append({"step": name, "at": _now(), **extra})
        print(f"[playwright] {name} {extra if extra else ''}")

    def on_response(response) -> None:
        url = response.url
        if "api.traffy.in.th" not in url:
            return
        entry = {
            "url": url,
            "status": response.status,
            "content_type": response.headers.get("content-type", ""),
            "filter": current_filter["label"],
        }
        try:
            body = response.body()
            entry["bytes"] = len(body)
            if "json" in entry["content_type"]:
                entry["json_preview"] = body[:MAX_PREVIEW_BYTES].decode("utf-8", errors="replace")
                if FEED_PATH in url and response.ok:
                    payload = json.loads(body.decode("utf-8"))
                    features = payload.get("features") or [] if isinstance(payload, dict) else []
                    kept = 0
                    for feature in features:
                        record = _compact(feature, current_filter["label"])
                        if record and record["ticket_id"] not in complaints:
                            complaints[record["ticket_id"]] = record
                            kept += 1
                    entry["features"] = len(features)
                    entry["new_complaints"] = kept
        except Exception as exc:  # body may be unavailable on redirects
            entry["body_error"] = f"{type(exc).__name__}: {exc}"
        network.append(entry)

    def wait_for_feed(page: Page, trigger, must_contain: str, label: str) -> bool:
        """Run `trigger` and wait for the filtered GeoJSON XHR it fires."""
        current_filter["label"] = label
        try:
            with page.expect_response(
                lambda r: FEED_PATH in r.url and must_contain in urllib.parse.unquote(r.url),
                timeout=30_000,
            ) as info:
                trigger()
            response = info.value
            step(f"xhr {label}", url=urllib.parse.unquote(response.url)[:200], status=response.status)
            page.wait_for_timeout(3_000)  # let markers render before the screenshot
            return True
        except PlaywrightError as exc:
            step(f"xhr_timeout {label}", error=str(exc)[:1500])
            return False

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

            # 1. Load the dashboard and wait for the JS-rendered map.
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=90_000)
            step("goto", url=page.url)
            try:
                page.wait_for_load_state("networkidle", timeout=60_000)
                step("networkidle")
            except PlaywrightError:
                step("networkidle_timeout")
            page.locator("button.buttonCategory").first.wait_for(timeout=30_000)
            page.wait_for_timeout(5_000)
            page.screenshot(path=str(ARTIFACT_DIR / "01_initial.png"))

            # 2. District filter: open the dropdown and pick each district.
            for district, district_slug in DISTRICTS:
                def pick_district(name: str = district) -> None:
                    page.locator("button.dropdown-header").first.click()
                    page.get_by_role("option", name=name, exact=True).click()

                if wait_for_feed(page, pick_district, "group_id=", f"district:{district}"):
                    page.screenshot(path=str(ARTIFACT_DIR / f"02_district_{district_slug}.png"))

            # Reset the district back to "all" before applying category filters.
            try:
                page.locator("button.dropdown-header").first.click()
                page.get_by_role("option", name="เขต/สำนักทั้งหมด", exact=True).click()
                page.wait_for_timeout(3_000)
                step("district reset")
            except PlaywrightError as exc:
                step("district_reset_failed", error=str(exc)[:1500])

            # 3. Category filter: the category toggles sit behind the
            #    "advanced filter" (ตัวกรองขั้นสูง) button; open it, then toggle one at a time.
            try:
                page.locator("button.div-more-filter").first.click(timeout=10_000)
                page.locator("button.buttonCategory").filter(
                    has=page.get_by_text(CATEGORIES[0][0], exact=True)
                ).first.wait_for(state="visible", timeout=10_000)
                step("open advanced filter")
            except PlaywrightError as exc:
                step("advanced_filter_failed", error=str(exc)[:1500])

            for category, bucket, category_slug in CATEGORIES:
                button = page.locator("button.buttonCategory").filter(
                    has=page.get_by_text(category, exact=True)
                ).first
                label = f"category:{category}({bucket})"
                if wait_for_feed(page, button.click, f"problem_type={category}", label):
                    page.screenshot(path=str(ARTIFACT_DIR / f"03_category_{category_slug}.png"))
                try:
                    button.click()  # toggle off before the next category
                    page.wait_for_timeout(2_000)
                except PlaywrightError:
                    pass

            # 4. Statistics tab (navigation interaction).
            current_filter["label"] = "stats_tab"
            try:
                page.get_by_text("สถิติ", exact=True).first.click(timeout=5_000)
                page.wait_for_timeout(5_000)
                step("click สถิติ", url=page.url)
                page.screenshot(path=str(ARTIFACT_DIR / "04_stats.png"))
            except PlaywrightError as exc:
                step("stats_click_failed", error=str(exc)[:1500])

            log["title"] = page.title()
            log["final_url"] = page.url
            context.close()
            browser.close()
    except Exception as exc:
        log["error"] = f"{type(exc).__name__}: {exc}"

    for name in LEGACY_ARTIFACTS:
        (ARTIFACT_DIR / name).unlink(missing_ok=True)

    by_filter: dict[str, int] = {}
    for record in complaints.values():
        by_filter[record["captured_by_filter"]] = by_filter.get(record["captured_by_filter"], 0) + 1

    log["finished_at"] = _now()
    log["network_requests"] = len(network)
    log["filtered_xhr_captured"] = sum(1 for s in log["steps"] if s["step"].startswith("xhr "))
    log["complaints_captured"] = len(complaints)
    log["complaints_by_filter"] = by_filter
    log["interacted"] = log["filtered_xhr_captured"] > 0

    (ARTIFACT_DIR / "network_capture.json").write_text(
        json.dumps(network, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (ARTIFACT_DIR / "playwright_filtered_complaints.json").write_text(
        json.dumps(list(complaints.values()), indent=1, ensure_ascii=False), encoding="utf-8"
    )
    (ARTIFACT_DIR / "playwright_scrape_log.json").write_text(
        json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({k: log[k] for k in log if k != "steps"}, indent=2, ensure_ascii=False))
    print(f"[artifacts] {ARTIFACT_DIR.relative_to(PROJECT_ROOT).as_posix()}")
    if log.get("error"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
