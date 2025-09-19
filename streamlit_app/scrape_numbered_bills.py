#!/usr/bin/env python3
"""
Robust scraper for https://le.utah.gov/billlist.jsp?session=2025GS
Saves utah_bills_2025.csv and utah_bills_2025.json in the current folder.
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timezone
from dateutil import parser as dateparser
from urllib.parse import urljoin
import time
import re
import sys
from tqdm import tqdm  # progress bar


# This is where all the bills that were introduced in the Utah state 2025 Legislative Session
# The csv I downloaded from the website only had the bills that had passed.
# This data set will give all the bills introduced so they can be compared and added to the dashboard data

BASE_URL = "https://le.utah.gov/billlist.jsp?session=2025GS"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}

def normalize_sponsor(s):
    if not s:
        return None
    s = s.strip()
    s = re.sub(r'^\(|\)$', '', s).strip()
    s = re.sub(r'^(Rep\.?|Sen\.?|Representative|Senator)\s*', '', s, flags=re.I).strip()
    return s

def parse_date(dt_text):
    if not dt_text:
        return None
    try:
        dt = dateparser.parse(dt_text, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return dt_text.strip()

def scrape_billlist(url=BASE_URL, pause=0.5, verbose=True):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    bill_anchors = soup.find_all("a", class_="billlink")
    if verbose:
        print(f"Found {len(bill_anchors)} anchors with class 'billlink'")

    rows = []
    if bill_anchors:
        for a in tqdm(bill_anchors, desc="Scraping bills", unit="bill"):
            try:
                bill_number = a.get_text(strip=True)
                href = a.get("href", "")
                bill_url = urljoin(BASE_URL, href) if href else None

                li = a.find_parent("li") or a.parent

                title_tag = li.find("b") if li else None
                bill_title = title_tag.get_text(strip=True) if title_tag else None

                sponsor_tag = li.find("i") if li else None
                sponsor_raw = sponsor_tag.get_text(strip=True) if sponsor_tag else None
                sponsor = normalize_sponsor(sponsor_raw)

                em_tags = li.find_all("em") if li else []
                date_raw = em_tags[-1].get_text(strip=True) if em_tags else None
                bill_date = parse_date(date_raw)

                category_tag = li.find_previous(
                    lambda tag: tag.name == "div" and "grouptitle" in (tag.get("class") or [])
                )
                category = category_tag.get_text(strip=True) if category_tag else None

                rows.append({
                    "Category": category,
                    "Bill Number": bill_number,
                    "Bill Title": bill_title,
                    "Bill Sponsor Raw": sponsor_raw,
                    "Bill Sponsor": sponsor,
                    "Bill Date Raw": date_raw,
                    "Bill Date (utc_iso)": bill_date,
                    "Bill URL": bill_url
                })
            except Exception as e:
                if verbose:
                    print("Error parsing anchor:", e)
            time.sleep(pause)
    else:
        print("No anchors with class 'billlink' found.")

    df = pd.DataFrame(rows)
    df["Scrape Timestamp"] = datetime.now(timezone.utc).isoformat()

    if df.empty and verbose:
        with open("debug_billlist_snapshot.html", "w", encoding="utf-8") as fh:
            fh.write(html)
        print("Warning: no bill rows found. Saved page snapshot to debug_billlist_snapshot.html")

    return df

if __name__ == "__main__":
    try:
        df = scrape_billlist()
        print(f"\nScraped {len(df)} rows.")
        if not df.empty:
            df = df.drop_duplicates(subset=["Bill Number", "Bill Title", "Bill URL"]).reset_index(drop=True)

            # --- Normalize formats ---
            # Bill Number: "H.B. 1" -> "HB 1"
            df["Bill Number"] = df["Bill Number"].str.replace(r"\.(?=[A-Z])", "", regex=True)

            # Sponsor: "Peterson, K." -> "Peterson, K"
            df["Bill Sponsor"] = df["Bill Sponsor"].str.replace(r"\.\b", "", regex=True)

            # --- Save ---
            df.to_csv("utah_bills_2025.csv", index=False)
            df.to_json("utah_bills_2025.json", orient="records", indent=2, force_ascii=False)

            print("Saved utah_bills_2025.csv and utah_bills_2025.json")
        else:
            print("No rows scraped — please inspect debug_billlist_snapshot.html")
    except Exception as e:
        print("Failed:", e)
        sys.exit(1)
