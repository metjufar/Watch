"""
Document/PDF publication monitor.

Visits each site in config/sites.json, extracts document links, and
compares them against what's been seen before (state/seen.json).
Anything new gets appended to data/findings.json, which the dashboard reads.

Run manually with:  python scraper.py
Runs automatically via .github/workflows/check-updates.yml
"""

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}
REQUEST_TIMEOUT = 30
DELAY_BETWEEN_SITES = 2  # seconds, be polite
MAX_FINDINGS_LOG = 500


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def make_id(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def extract_pdf_links(soup, base_url):
    """Grab every link that points directly at a .pdf file."""
    items = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().split("?")[0].endswith(".pdf"):
            title = a.get_text(strip=True) or href.rsplit("/", 1)[-1]
            items.append({"title": title, "url": urljoin(base_url, href)})
    return items


def extract_article_links(soup, base_url, selector):
    """Grab links matching a CSS selector (for list-of-articles pages)."""
    items = []
    for a in soup.select(selector):
        href = a.get("href")
        title = a.get_text(strip=True)
        if href and title:
            items.append({"title": title, "url": urljoin(base_url, href)})
    return items


def dedupe(items):
    seen, out = set(), []
    for it in items:
        if it["url"] not in seen:
            seen.add(it["url"])
            out.append(it)
    return out


def scrape_site(site, session):
    url = site["url"]
    parsed = urlparse(url)
    homepage = f"{parsed.scheme}://{parsed.netloc}/"

    # Warm up: visit the homepage first so any cookies/challenge cookies
    # get set, same as a real browser landing on the site before
    # clicking through to an inner page. Ignore failures here — some
    # sites' homepage differs enough that this isn't needed.
    try:
        session.get(homepage, headers=BROWSER_HEADERS, timeout=REQUEST_TIMEOUT)
        time.sleep(1)
    except requests.RequestException:
        pass

    headers = dict(BROWSER_HEADERS)
    headers["Referer"] = homepage

    resp = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    mode = site.get("mode", "pdf_links")
    if mode == "pdf_links":
        items = extract_pdf_links(soup, url)
    elif mode == "article_links":
        items = extract_article_links(soup, url, site["selector"])
    else:
        raise ValueError(f"Unknown mode: {mode}")

    return dedupe(items)


def main():
    sites = load_json("config/sites.json", [])
    if not sites:
        print("No sites configured in config/sites.json", file=sys.stderr)
        sys.exit(1)

    state = load_json("state/seen.json", {})
    new_findings = []
    errors = []
    session = requests.Session()

    for i, site in enumerate(sites):
        name = site["name"]
        print(f"Checking: {name} ...")
        try:
            items = scrape_site(site, session)
        except Exception as e:
            msg = f"ERROR scraping '{name}': {e}"
            print(msg, file=sys.stderr)
            errors.append(msg)
            continue

        seen_ids = set(state.get(name, []))
        site_new = []
        for it in items:
            iid = make_id(it["url"])
            if iid not in seen_ids:
                site_new.append(it)
                seen_ids.add(iid)

        if site_new:
            print(f"  -> {len(site_new)} new item(s)")
        for it in site_new:
            new_findings.append({
                "site": name,
                "title": it["title"],
                "url": it["url"],
                "found_at": datetime.now(timezone.utc).isoformat(),
            })

        state[name] = list(seen_ids)

        if i < len(sites) - 1:
            time.sleep(DELAY_BETWEEN_SITES)

    save_json("state/seen.json", state)

    log = load_json("data/findings.json", [])
    log = new_findings + log
    log = log[:MAX_FINDINGS_LOG]
    save_json("data/findings.json", log)

    save_json("data/last_run.json", {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "sites_checked": len(sites),
        "new_items": len(new_findings),
        "errors": errors,
    })

    print(f"\nDone. {len(new_findings)} new document(s) found across {len(sites)} site(s).")
    if errors:
        print(f"{len(errors)} site(s) failed to load — see errors above.")


if __name__ == "__main__":
    main()
