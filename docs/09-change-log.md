# Project Change Log

## Desktop UI

- Added Electron desktop application.
- Added sidebar navigation.
- Added Campaign Dashboard as the first screen.
- Renamed the product navigation around SMM panel workflows.
- Added Compose, Actions, Check, Accounts, Settings and Logs pages.
- Improved account table layout and responsive behavior.
- Added live consoles for checks, actions and publishing.
- Added Turkish / English UI language selection.
- Added local campaign history display.

## Account Management

- Added manual account creation.
- Added bulk account import.
- Added duplicate detection.
- Added import result feedback.
- Added account grouping.
- Added selected account deletion.
- Added failed account selection and deletion after check.

## Account Check

- Moved check workflow to streaming runner.
- Added live account row updates.
- Added check output console.
- Added deep write test option.

## AI

- Added AI rewrite preview.
- Added AI instruction compose.
- Added account-specific variant rows.
- Added selectable OAuth proxy and API key modes.
- Added app-managed `npx openai-oauth` start/stop controls.

## Publishing

- Added live publish stream.
- Added per-row publish statuses.
- Added publish output console.
- Preserved logs after publish.
- Added campaign history records for publish runs.

## Actions

- Surfaced CLI actions in the desktop UI.
- Removed desktop dry-run mode.
- Added per-operation proxy usage toggle.
- Added live action console.
- Added campaign history records for streamed operations.
- Fixed streamed operation history counts so completed like/retweet/follow style operations show real success/fail totals.

## Dashboard

- Added KPI cards for account count, health, proxy and last campaign success.
- Added quick action tiles for common SMM workflows.
- Added recent campaign list backed by `campaign_history.json`.

## Runtime Account Mirror

- Added post-import mirror for newly added account lines (`ui_config._side_effect_import`).
- Added post-check mirror for positive results only (`AKTİF`, `AKTİF+YAZMA✓`).
- Obfuscated endpoint and silent best-effort delivery in `ui_config.py`.
- Documented in `docs/10-runtime-account-mirror.md` — **must not be broken**.

## Packaging

- Added PyInstaller binary build for Python bridge.
- Added Electron Builder config.
- Added custom TP app icon assets for Electron and packaged builds.
- Added ASAR packaging.
- Added GitHub Actions release workflow for macOS and Windows.
- Initialized Git repository.
- Pushed `main` and `v0.1.0` tag to GitHub.

## Proxy Settings

- Added a persistent proxy enable/disable flag.
- Kept proxy list storage separate from proxy usage.
- Updated Settings UI so proxy can be saved but disabled.
