# scirate-notifier

Daily digest of top [SciRate](https://scirate.com) papers for arXiv categories (default: **quant-ph**), delivered as a push notification to your phone via [ntfy.sh](https://ntfy.sh).

Runs locally or on a scheduled [GitHub Actions](https://github.com/features/actions) workflow.

## What it does

1. Scrapes SciRate for the highest-scited papers in the configured category/categories over the last day.
2. Filters by minimum scite count and keeps the top N papers.
3. Sends a concise notification with titles, scite counts, and arXiv links.

## How notifications work

1. Install the **ntfy** app on [iOS](https://apps.apple.com/app/ntfy/id1625396347) or [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy).
2. Choose a **topic name** — this acts like a password. Use something long and unguessable (e.g. `my-quant-ph-digest-x7k2m9`).
3. Subscribe to that topic in the app (Add subscription → enter topic name).
4. Set `NTFY_TOPIC` to the same name when running this tool.

Notifications are sent to `https://ntfy.sh/<your-topic>`. Anyone who knows your topic can read messages, so keep it secret.

## Local usage

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export NTFY_TOPIC=your-secret-topic

# Preview without sending
python -m scirate_notifier --dry-run

# Send notification
python -m scirate_notifier
```

Optional CLI overrides:

```bash
python -m scirate_notifier --dry-run --top-n 10 --category quant-ph --category gr-qc
```

Copy `.env.example` to `.env` for reference; export variables manually or use a tool like `direnv`.

## GitHub Actions setup

1. Push this repository to GitHub.
2. Add a repository **secret**: `NTFY_TOPIC` (Settings → Secrets and variables → Actions → Secrets).
3. Optionally add repository **variables**: `SCIRATE_CATEGORIES`, `TOP_N`, `MIN_SCITES`.
4. The workflow in `.github/workflows/daily.yml` runs daily at **23:00 UTC** (~08:00 JST the next morning) and can be triggered manually from the Actions tab.

## SciRate HTML changes

SciRate markup can change without notice. If scraping returns no papers or wrong data, update selectors in `scirate_notifier/scraper.py`:

| Purpose | Selectors tried (in order) |
|---------|---------------------------|
| Paper container | `div.paper`, `li.paper` |
| Title link | `.title a` |
| Scite count | `.scites_count`, `.num-scites`, `a.scite-button`, `[class*='scite']` |
| Authors | `.authors` |

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NTFY_TOPIC` | Yes | — | Private ntfy topic name |
| `NTFY_SERVER` | No | `https://ntfy.sh` | ntfy server base URL |
| `SCIRATE_CATEGORIES` | No | `quant-ph` | Comma-separated SciRate categories |
| `SCIRATE_RANGE_DAYS` | No | `1` | Days to look back on SciRate |
| `TOP_N` | No | `5` | Max papers in notification |
| `MIN_SCITES` | No | `1` | Minimum scites to include |
| `NTFY_PRIORITY` | No | `default` | ntfy priority (`min`, `low`, `default`, `high`, `max`) |

## License

MIT (or your choice — add a LICENSE file if needed).
