#!/usr/bin/env python3

import json
import re
from pathlib import Path
from typing import List, Dict

RAW_FILE = Path("jobs_raw.json")
FILTERED_FILE = Path("jobs_filtered.json")

JOB_URL_RE = re.compile(
    r"https://www\.google\.com/about/careers/applications/jobs/results/(\d+)-([a-z0-9\-]+)",
    re.IGNORECASE
)


def load_raw_items() -> List[Dict]:
    if not RAW_FILE.exists():
        print("jobs_raw.json not found.")
        return []

    with RAW_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def slug_to_title(slug: str) -> str:
    words = slug.split("-")
    return " ".join(word.capitalize() for word in words if word)


def filter_jobs(items: List[Dict]) -> List[Dict]:
    results: List[Dict] = []
    seen_job_ids = set()

    for item in items:
        if item.get("type") != "anchor":
            continue

        href = (item.get("href") or "").strip()
        if not href:
            continue

        match = JOB_URL_RE.match(href)
        if not match:
            continue

        job_id = match.group(1)
        title_slug = match.group(2)

        if job_id in seen_job_ids:
            continue

        seen_job_ids.add(job_id)

        clean_url = href.split("?")[0]
        title = slug_to_title(title_slug)

        results.append({
            "job_id": job_id,
            "title": title,
            "url": clean_url
        })

    return results


def main() -> None:
    items = load_raw_items()
    filtered = filter_jobs(items)

    with FILTERED_FILE.open("w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)

    print(f"Saved filtered jobs to {FILTERED_FILE.resolve()}")
    print(f"Filtered jobs count: {len(filtered)}")

    for i, job in enumerate(filtered[:10], start=1):
        print(f"{i}. [{job['job_id']}] {job['title']} -> {job['url']}")


if __name__ == "__main__":
    main()