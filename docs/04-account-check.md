# Account Check

## Purpose

Account Check verifies whether selected accounts can be used. It helps separate active accounts from failed, unauthorized or timed-out accounts.

## Flow

The current live check flow uses `ui_live.py`:

1. Renderer sends selected account indices.
2. `desktop/main.js` starts `ui_live.py check`.
3. `ui_live.py` calls `tweeter.check_accounts()`.
4. Python output is streamed back line by line.
5. Renderer parses lines and updates each account row.
6. Final structured results replace the temporary row state.

## Check Modes

The UI supports:

- Surface check: token/account status-oriented check.
- Deep write test: optional deeper verification when enabled.

## Result Fields

Structured check results include:

- `username`
- `uid`
- `screenName`
- `label`
- `ok`
- `writeOk`
- `error`

The UI maps these into status pills and detail text.

## Follow-up Actions

After check, the user can:

- Select failed accounts.
- Delete failed accounts.
- Review live output.
- Use the account inventory for further grouping or deletion.

## Logging Boundary

The check result is safe to log when limited to metadata such as username, status label, UID, screen name and error text.

Do not log raw `auth_token`, `ct0`, passwords, email passwords or 2FA secrets to remote services.

