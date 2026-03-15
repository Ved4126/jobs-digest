#!/usr/bin/env python3

import json
import os
import time

from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
from selenium import webdriver

from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

load_dotenv()

JOB_KEYWORDS = os.getenv("JOB_KEYWORDS", "software engineer,intern").split(",")
JOB_LOCATION = os.getenv("JOB_LOCATION", "United States")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "50"))
BASE_SEARCH_URL = "https://careers.google.com/jobs/results/?"
OUTPUT_FILE = Path("jobs_raw.json")

def build_search_url(keywords: List[str], location: str):
    q = "+".join("+".join(k.strip().split()) for k in keywords if k.strip())
    parts = []
    if q:
        parts.append(f"q={q}")
    if location:
        parts.append(f"location={'+'.join(location.split())}")
    return BASE_SEARCH_URL + "&".join(parts)

def make_headless_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1400,900")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    return driver

def collect_raw_data(driver: webdriver.chrome, max_results: int) -> List[Dict]:
    
    data: List[Dict] = []
    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
    print("TOTAL_ANCHORS_FOUND =", len(anchors))

    for i, a in enumerate(anchors[:max_results], start=1):
        href = (a.get_attribute("href") or "").strip()
        text = (a.text or "").strip()
        item = {
            "type": "anchor",
            "index": i,
            "text": text,
            "href": href,
        }

        data.append(item)
    
    blocks = driver.find_elements(By.XPATH, "//*[self::div or self::span or self::p or self::li]")
    visible_text_blocks = []
    for b in blocks[:300]:
        text = (b.text or "").strip()
        if text:
            visible_text_blocks.append(text)

    
    data.append({
        "type": "page_summary",
        "current_url": driver.current_url,
        "title": driver.title,
        "visible_text_blocks": visible_text_blocks[:100],
    })

    return data

def main() -> None:
    all_raw_data = []
    for keyword in JOB_KEYWORDS:
        keyword = keyword.strip()
        if not keyword:
            continue

        search_url = build_search_url([keyword], JOB_LOCATION)
        print("Search URL:", search_url)
        driver = make_headless_driver()
        try:
            driver.get(search_url)
            time.sleep(5)

            for _ in range(3):
                try:
                    button = driver.find_element(
                        By.XPATH,
                        "//button[contains(., 'Load more') or contains(., 'Show more')]"
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(0.5)
                    button.click()
                    time.sleep(2)
                except Exception:
                    break

            raw_data = collect_raw_data(driver, MAX_RESULTS)
            all_raw_data.extend(raw_data)

        finally:
            driver.quit()
    

    driver = make_headless_driver()

    try:
        driver.get(search_url)
        time.sleep(5)

        for _ in range(3):
            try:
                button = driver.find_element(
                    By.XPATH,
                    "//button[contains(., 'Load more') or contains(., 'Show more')]"
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(0.5)
                button.click()
                time.sleep(2)
            except Exception:
                break
        
        raw_data = collect_raw_data(driver, MAX_RESULTS)

    finally:
        driver.quit()

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(all_raw_data, f, indent=2, ensure_ascii=False)

    print(f"Saved raw data to {OUTPUT_FILE.resolve()}")
    print(f"Collected {len(all_raw_data)} raw items.")

if __name__ == "__main__":
    main()
