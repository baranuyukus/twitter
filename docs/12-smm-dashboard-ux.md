# SMM Dashboard UX

## Purpose

The desktop UI now presents Tweeter Studio as a Twitter/X SMM panel rather than a CLI wrapper. The app shows a lightweight loading screen while runtime state is prepared, then opens into the campaign dashboard.

## Navigation

The navigation is organized by operator intent:

- Dashboard
- Campaigns
- Accounts
- Health Check
- Operations
- Settings
- Logs

## Dashboard

Dashboard shows:

- total account count
- credential-ready account count
- healthy / failed account counts from the latest visible check state
- proxy enabled state and proxy count
- last campaign success rate
- recent campaign history
- quick action tiles

## Loading Screen

The loading screen is a transient startup overlay, not a navigation page. It reports boot steps for accounts, campaign history, logs and OAuth proxy status, then fades out when Dashboard is ready.

## Campaign History

Campaign and operation runs are stored locally in:

```text
campaign_history.json
```

Records include:

- id
- type
- title
- target
- accountCount
- successCount
- failCount
- status
- startedAt
- finishedAt
- lastError

## Language

The UI supports Turkish and English through a lightweight renderer dictionary. The current language is stored in `app_config.json` as `uiLanguage`.

Language can be changed directly from the top bar on every screen. Settings keeps the same selector for configuration review, but it is no longer the only place to switch UI language.

Default:

```text
tr
```

## Notes

This pass intentionally avoids adding licensing, billing, onboarding or remote backend concerns. The focus is the core SMM operator experience.

Dry-run controls were removed from the desktop Operations surface. Operations now include a per-run proxy toggle so the operator can decide whether that specific action should use the configured proxy pool.
