# Project Change Log

## Desktop UI

- Added Electron desktop application.
- Added sidebar navigation.
- Added Compose, Actions, Check, Accounts, Settings and Logs pages.
- Improved account table layout and responsive behavior.
- Added live consoles for checks, actions and publishing.

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

## Actions

- Surfaced CLI actions in the desktop UI.
- Added dry-run mode.
- Added live action console.

## Packaging

- Added PyInstaller binary build for Python bridge.
- Added Electron Builder config.
- Added ASAR packaging.
- Added GitHub Actions release workflow for macOS and Windows.
- Initialized Git repository.
- Pushed `main` and `v0.1.0` tag to GitHub.

