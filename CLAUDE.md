# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Korean KOSDAQ active ETF daily composition tracker. Downloads Excel files from ETF providers, compares holdings day-over-day, and sends change summaries via Telegram.

**Supported ETFs:**
- **KoAct** (2ETFU6) — `koact` — Samsung, `.xls` format
- **TIME** (0162Y0) — `time` — TIME ETF, `.xlsx` format
- **PLUS150** (006399) — `plus150` — PLUS ETF, `.xlsx` format
- **TIME 코스피액티브** (385720) — `timek` — TIME ETF, `.xlsx` format

## Commands

```bash
# Setup
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements.txt

# Run all ETFs for today
python main.py --all

# Run specific ETF(s) for a specific date
python main.py --date 2026-03-20 --etf koact
python main.py --date 2026-03-20 --etf koact --etf time

# Windows batch shortcuts
run_etf_tracker.bat              # today, all ETFs
run_etf_tracker_with_date.bat    # prompts for date
```

No test suite exists.

## Architecture

```
main.py                         # CLI entry point & orchestration
etf_tracker/
  config.py                     # ETF definitions (EtfConfig frozen dataclass)
  etl/
    common.py                   # Shared: Holding dataclass, Excel parsing, column detection, normalization
    koact.py / time_etf.py / plus150.py / time_kospi.py  # ETF-specific parsers (weight scaling differs)
    koact_download.py / time_download.py / plus150_download.py / time_kospi_download.py  # HTTP downloaders
  core/
    diff.py                     # DiffResult (full/new/removed/increased/decreased DataFrames)
  alerts/
    telegram.py                 # Message formatting & Telegram Bot API calls
```

### Data Flow

1. **Download** — Each ETF downloader fetches an Excel file from its provider URL, saves to `data/<etf>/YYYY-MM-DD_<etf>.<ext>`. Skips if file already cached. Validates response > 1024 bytes.
2. **Parse** — ETF-specific parser calls `common.normalize_holdings_df()` to produce a standardized DataFrame (ticker, name, shares, weight, etc.). KoAct multiplies weight by 100 (provider returns decimal form).
3. **Find Previous** — `_find_previous_file()` in main.py searches up to 14 weekdays back, auto-downloading and validating each (minimum 10 holdings = valid trading day).
4. **Diff** — `compute_diff()` outer-merges on ticker, calculates share/weight changes, weight change in basis points, categorizes into new/removed/increased/decreased.
5. **Report** — Saves full diff CSV to `reports/`, sends summary message + CSV via Telegram.

### Key Constants

- `MIN_HOLDINGS_PREV_DAY = 10` — minimum holdings to consider a file as valid trading day data
- `MAX_DAYS = 14` — look-back limit for previous trading day search
- Telegram message chunk limit: 3500 chars

### Column Detection

`common.py` uses `COLUMN_CANDIDATES` dict mapping logical names to multiple possible Excel header strings, with case-insensitive partial matching via `_choose_column()`. This handles variation across ETF provider Excel formats.

### Environment

Requires `.env` file with `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

## Language

All user-facing messages, log output, commit messages, and code comments are in Korean. Follow this convention.
