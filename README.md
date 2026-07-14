# Document Monitor

Checks a list of websites for newly published PDFs/documents and shows them
on a dashboard page. Runs automatically on a schedule via GitHub Actions —
no server of your own required, works even when your computer is off.

## How it works

1. `config/sites.json` lists the pages to check.
2. Every 6 hours, a GitHub Action runs `scraper.py`, which visits each page,
   collects document links, and compares them against what it saw last time
   (`state/seen.json`).
3. Anything new gets logged to `data/findings.json`.
4. `dashboard.html`, hosted via GitHub Pages, reads that file and shows you
   the list — new items (since your last visit) are highlighted.

## One-time setup (about 10 minutes)

1. **Create a GitHub account** if you don't have one (free): github.com

2. **Create a new repository**
   - Click "+" → "New repository"
   - Name it anything, e.g. `doc-monitor`
   - Make it **Public** (required for free GitHub Pages)
   - Don't initialize with a README (we already have one)

3. **Upload these files**
   - On the repo page, click "Add file" → "Upload files"
   - Drag in everything from this folder, **keeping the folder structure**
     (`config/`, `.github/workflows/`, `state/`, `data/`, plus the loose files)
   - Commit the changes

4. **Enable GitHub Actions** (usually on by default for new repos)
   - Go to the "Actions" tab of your repo — if prompted, click "I understand,
     enable Actions"

5. **Run it once manually** to populate initial data
   - Actions tab → "Check for new documents" (left sidebar) → "Run workflow"
     button → "Run workflow"
   - Wait ~30 seconds, refresh — you should see a green checkmark
   - Note: the *first* run will show every existing document as "new" since
     it has nothing to compare against yet. That's expected — from the second
     run onward, only genuinely new items show up.

6. **Enable GitHub Pages** so you can view the dashboard
   - Repo → Settings → Pages
   - Under "Build and deployment", set Source to "Deploy from a branch"
   - Branch: `main`, folder: `/ (root)` → Save
   - Wait a minute, then visit: `https://<your-username>.github.io/<repo-name>/dashboard.html`

That's it — bookmark that dashboard URL. It updates itself every 6 hours.

## Adding more sites later

Edit `config/sites.json` (directly on GitHub: open the file → pencil icon
to edit → commit). Each entry looks like:

```json
{
  "name": "Display name for the dashboard",
  "url": "https://example.com/publications",
  "mode": "pdf_links"
}
```

Two modes are supported:

- **`pdf_links`** (most common) — grabs every link on the page that points
  directly to a `.pdf` file. Works for most publication/document listing pages.
- **`article_links`** — for pages that link to individual article pages
  rather than PDFs directly (like NSO's news releases). Requires a `selector`
  field (a CSS selector matching the article title links) — you may need to
  inspect the page's HTML (right-click → Inspect) to find the right one.

After committing the change, either wait for the next scheduled run or
trigger it manually (Actions tab → Run workflow) to pick up the new site.

## Changing the check frequency

Edit the `cron` line in `.github/workflows/check-updates.yml`. It's in UTC.
Examples:
- Every hour: `0 * * * *`
- Twice a day: `0 6,18 * * *`
- Once a day at 7am UTC: `0 7 * * *`

## Notes on the sites currently configured

- Most sites (GRDA, Central Bank of Malta, Malta Chamber, Standards
  Commissioner pages) link straight to PDFs, so `pdf_links` mode works well.
- **NSO Malta's news releases** page links to article pages rather than PDFs
  directly, so it uses `article_links` mode. If it stops finding new items,
  the site's HTML structure may have changed — you'll likely need to update
  the `selector`.
- The **Government Gazette Repository** page (gov.mt) wasn't fully verified —
  government ASPX sites sometimes load content via JavaScript, which this
  simple scraper can't execute. If it consistently finds nothing, let me
  know and I can look into whether it needs a different approach.

## Running it locally (optional, for testing)

```bash
pip install -r requirements.txt
python scraper.py
```
