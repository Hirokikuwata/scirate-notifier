# scirate-notifier

Daily digest of top [SciRate](https://scirate.com) papers for arXiv categories (default: **quant-ph**), delivered as a push notification to your phone via [ntfy.sh](https://ntfy.sh).

Runs locally (cron/launchd) or on a scheduled [GitHub Actions](https://github.com/features/actions) workflow.

## What it does

The tool has two complementary modes, both sending push notifications:

| Mode | Source | Sorted by |
|------|--------|-----------|
| `--source scirate` | SciRate top papers | Scite count (community upvotes) |
| `--source arxiv` | arXiv latest submissions | Submission date (newest first) |

Running both every morning gives you **what's popular** + **what's brand new**. If SciRate is unavailable (e.g. IP-blocked on cloud runners), the `auto` mode falls back to arXiv automatically.

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
# SciRate top papers only
python -m scirate_notifier --source scirate --dry-run

# arXiv recent papers only
python -m scirate_notifier --source arxiv --dry-run

# Multiple categories
python -m scirate_notifier --dry-run --top-n 10 --category quant-ph --category gr-qc
```

Copy `.env.example` to `.env` for reference; export variables manually or use a tool like `direnv`.

## Local cron setup (macOS)

Running locally avoids cloud IP restrictions — SciRate works fine from a home/office IP.

**Step 1 — create `.env`**

```bash
cp .env.example .env
# Edit .env and set NTFY_TOPIC=your-secret-topic
```

**Step 2 — test the script**

```bash
./run_local.sh --source scirate --dry-run
./run_local.sh --source arxiv   --dry-run
```

`run_local.sh` automatically creates `.venv` and installs dependencies on first run.

**Step 3 — add crontab entries**

```bash
crontab -e
```

Paste (adjust the path if your repo is elsewhere):

```cron
# scirate-notifier — runs at 08:00 local time
# Assumes macOS system timezone is set to JST.
# SciRate top papers (scite-sorted)
0 8 * * * /Users/kuwatahiroki/Projects/scirate-notifier/run_local.sh --source scirate >> /tmp/scirate-notifier.log 2>&1
# arXiv latest submissions
0 8 * * * /Users/kuwatahiroki/Projects/scirate-notifier/run_local.sh --source arxiv   >> /tmp/scirate-notifier.log 2>&1
```

> **Tip:** To verify your Mac's timezone: `sudo systemsetup -gettimezone`  
> To check the log after 8:00: `cat /tmp/scirate-notifier.log`

**macOS sleep caveat:** If your Mac is asleep at 08:00, macOS skips that cron run. Use *System Settings → Battery → Wake for network access* or schedule slightly later when the machine is reliably awake. Alternatively, use `launchd` with `StartCalendarInterval` (more reliable than cron on macOS).

## GitHub Actions setup

1. Push this repository to GitHub.
2. Add a repository **secret**: `NTFY_TOPIC` (Settings → Secrets and variables → Actions → Secrets).
3. Optionally add repository **variables**: `SCIRATE_CATEGORIES`, `TOP_N`, `MIN_SCITES`.
4. The workflow in `.github/workflows/daily.yml` runs daily at **23:00 UTC** (~08:00 JST the next morning) and can be triggered manually from the Actions tab.

## SciRate HTML changes

SciRate markup can change without notice. If scraping returns no papers or wrong data, update selectors in `scirate_notifier/scraper.py`:

| Purpose | Selectors tried (in order) |
|---------|---------------------------|
| Paper container | `ul.papers .row`, `li.paper`, `div.paper` |
| Title link | `.title a` |
| Scite count | `.scites-count button.count`, `button.btn-default.count` |
| Authors | `.authors a` |

GitHub Actions runners may be blocked by SciRate (HTTP 403). When that happens the notifier automatically falls back to arXiv recent papers and the notification title will read "arXiv … recent papers (SciRate unavailable)". For reliable SciRate access, use the local cron setup above.

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
