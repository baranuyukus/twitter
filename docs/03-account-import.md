# Account Import

## Purpose

Account import turns raw account lines into the `accounts.txt` format used by the Python core. It supports manual entry and bulk paste.

## Supported Formats

Five-field format:

```text
username:password:phone:auth_token:ct0
```

Seven-field batch format:

```text
username:password:email:email_password:2fa:ct0:auth_token
```

The seven-field format is normalized into the internal five-field account format.

## Import Rules

The import flow:

1. Reads manual or bulk text.
2. Skips blank lines and comments.
3. Parses each line by field count.
4. Skips invalid rows.
5. Skips duplicate usernames.
6. Appends new rows to `accounts.txt`.
7. Returns added and skipped summaries to the UI.

## UI Feedback

After import, the UI shows:

- Number of accounts added.
- Number of rows skipped.
- Added usernames.
- Skipped row reasons.

The bulk text area is cleared only when at least one row was added.

## Sensitive Data

The UI masks `auth_token` and `ct0` in account inventory. These values are treated as password-equivalent credentials.

They are stored locally in `accounts.txt` because the Twitter CLI workflow needs them, but they should not be sent to external logging endpoints or committed to Git.

