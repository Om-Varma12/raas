"""
Fetch SEC 10-K filings for a company via the EDGAR submissions API.

Usage:
    python fetch_sec.py [CIK] [--count N]

Example:
    python fetch_sec.py 0000320193 --count 4   # Apple, last 4 10-Ks

To find another company's CIK:
    https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany
    (search the company name, CIK is in the URL / results table)

IMPORTANT: edit YOUR_USER_AGENT below before running — SEC blocks
requests without a real identifying User-Agent header.
"""
import argparse
import os
import time
import requests

YOUR_USER_AGENT = "Sahil your_email@example.com"  # <-- EDIT THIS
HEADERS = {"User-Agent": YOUR_USER_AGENT}

OUT_DIR = "data/finance"


def get_submissions(cik: str) -> dict:
    cik = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def fetch_10ks(cik: str, count: int = 4):
    os.makedirs(OUT_DIR, exist_ok=True)
    data = get_submissions(cik)
    recent = data["filings"]["recent"]

    found = 0
    for form, accn, doc, date in zip(
        recent["form"], recent["accessionNumber"],
        recent["primaryDocument"], recent["filingDate"],
    ):
        if form != "10-K":
            continue
        accn_nodash = accn.replace("-", "")
        cik_int = str(int(cik))
        doc_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_int}/{accn_nodash}/{doc}"
        )
        print(f"Fetching {form} filed {date}: {doc_url}")
        r = requests.get(doc_url, headers=HEADERS)
        r.raise_for_status()
        company_dir = os.path.join(OUT_DIR, cik)
        os.makedirs(company_dir, exist_ok=True)

        out_path = os.path.join(company_dir, f"{cik_int}_{date}_10K.htm")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(r.text)
        found += 1
        time.sleep(0.3)  # stay under SEC's rate limit
        if found >= count:
            break

    print(f"Saved {found} filings to {OUT_DIR}/")
    if found == 0:
        print("No 10-Ks found — double check the CIK.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "cik", nargs="?", default="0000320193",
        help="Company CIK, e.g. 0000320193 (default: Apple)",
    )
    parser.add_argument("--count", type=int, default=4)
    args = parser.parse_args()
    fetch_10ks(args.cik, args.count)
