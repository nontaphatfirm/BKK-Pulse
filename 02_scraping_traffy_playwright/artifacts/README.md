# Playwright run artifacts

Evidence that the interactive scraper drives the dashboard — not data for the pipeline.

    python 02_scraping_traffy_playwright/src/scrape_traffy_playwright.py

- `0*.png` — one screenshot per interaction step
- `network_capture.json` — every intercepted `api.traffy.in.th` call, tagged with the filter that fired it
- `playwright_scrape_log.json` — timestamped interaction log and capture counts
- `playwright_filtered_complaints.json` — reports parsed from the intercepted feeds.
  Covers only the days the dashboard was serving at run time; **do not use as dataset
  input**. Table 4 comes from `data/traffy_complaints_near_cctv.parquet`.
- `type_raw_counts.csv` & `type_tag_counts.csv` — category and tag frequency audits
  generated from the page cache by `02_scraping_traffy_playwright/src/audit_categories.py`.

Regenerating `scrape_traffy_playwright.py` overwrites the Playwright captures above and deletes the legacy `traffy_dashboard*.png`.
