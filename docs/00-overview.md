# Tweeter Studio Overview

## Purpose

Tweeter Studio turns the original command-line Twitter/X account automation tool into a desktop control panel. The goal is to keep the proven Python workflow in `tweeter.py`, while moving day-to-day usage into a safer and more visible UI.

The system is built around three layers:

- Python core: account loading, Twitter CLI execution, retries, AI rewrite/compose, checks, logs and bulk actions.
- JSON bridge: stable commands for Electron to call without coupling the UI to CLI output.
- Electron UI: pages for composing tweets, running actions, checking accounts, managing accounts, settings and logs.

## Main Files

- `tweeter.py`: core business logic and original CLI feature set.
- `ui_api.py`: request/response JSON bridge for short operations.
- `ui_live.py`: NDJSON streaming bridge for long-running operations.
- `ui_config.py`: persistent AI provider and runtime configuration.
- `desktop/main.js`: Electron main process, Python process runner and OAuth proxy launcher.
- `desktop/preload.js`: safe renderer API exposed through context bridge.
- `desktop/renderer/index.html`: desktop UI structure.
- `desktop/renderer/app.js`: UI state, rendering and event orchestration.
- `desktop/renderer/styles.css`: visual system and responsive layout.

## Data Files

Runtime data is intentionally kept outside the packaged app:

- `accounts.txt`: account records.
- `proxy.txt`: proxy list.
- `tweet_log.json`: operation logs.
- `account_groups.json`: UI account groups.
- `app_config.json`: AI provider and model settings.

In development these live in the project folder. In packaged builds they live under the user data directory so the app can update safely without overwriting user data.

## Current Product Shape

The desktop app now covers:

- AI preview and account-specific tweet variants.
- Live tweet publishing status.
- Bulk like, retweet, follow, reply, bookmark, view, protect, unprotect, boost and purge actions.
- Account check with live output.
- Manual and bulk account import.
- Account grouping and selected account deletion.
- OAuth proxy mode and OpenAI API key mode.
- Packaged release builds for macOS and Windows.

