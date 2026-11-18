"""Audit cached Traffy type labels against the explicit tag map."""

from __future__ import annotations

import csv
import gzip
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "data" / "raw_traffy_cache" / "pages"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MAP_PATH = Path(__file__).with_name("category_map.json")


def split_tags(raw_type: str) -> list[str]:
    return [part.strip() for part in str(raw_type).split(",") if part.strip()]


def bucket_for(tags: list[str], mapping: dict[str, str], default: str) -> str:
    buckets = {mapping.get(tag, default) for tag in tags}
    if "flood" in buckets:
        return "flood"
    if "traffic" in buckets:
        return "traffic"
    return default


def cached_records() -> dict[str, dict]:
    records: dict[str, dict] = {}
    for path in sorted(CACHE_DIR.glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for record in json.load(handle):
                records.setdefault(record["ticket_id"], record)
    return records


def write_csv(path: Path, header: tuple[str, ...], rows: list[tuple]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    config = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    mapping, default = config["tags"], config["default"]
    records = cached_records()

    labels: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    for record in records.values():
        raw = record.get("type_raw", "")
        labels[raw] += 1
        tags.update(split_tags(raw))

    label_rows = [
        (raw, count, bucket_for(split_tags(raw), mapping, default))
        for raw, count in labels.items()
    ]
    label_rows.sort(key=lambda row: (-row[1], row[0]))
    tag_rows = [(tag, count, bucket_for([tag], mapping, default)) for tag, count in tags.items()]
    tag_rows.sort(key=lambda row: (-row[1], row[0]))

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(ARTIFACTS_DIR / "type_raw_counts.csv", ("type_raw", "count", "bucket"), label_rows)
    write_csv(ARTIFACTS_DIR / "type_tag_counts.csv", ("tag", "count", "bucket"), tag_rows)

    print(f"[audit] {len(records):,} unique cached records")
    print(f"[audit] {len(label_rows)} type_raw labels, {len(tag_rows)} comma-split tags")
    for bucket in ("flood", "traffic", "other"):
        total = sum(row[1] for row in label_rows if row[2] == bucket)
        print(f"[audit] {bucket}: {total:,} records")
    print(f"[audit] unmatched tags: {sum(1 for tag in tags if tag not in mapping)}")
    print("[audit] type_raw labels")
    for raw, count, bucket in label_rows:
        print(f"{count:>7}  {bucket:<7}  {raw}")
    print("[audit] comma-split tags")
    for tag, count, bucket in tag_rows:
        print(f"{count:>7}  {bucket:<7}  {tag}")


if __name__ == "__main__":
    main()
