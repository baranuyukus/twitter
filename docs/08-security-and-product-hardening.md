# Security and Product Hardening

## Credential Handling

Twitter/X account records include sensitive values:

- password
- auth token
- ct0 cookie
- email password
- 2FA secret

These are password-equivalent credentials. They should stay local and should not be committed, printed in full or sent to external services.

## UI Masking

The UI masks sensitive token values in account inventory:

```text
1419b1...cf75
```

This lets the user confirm that credentials exist without exposing the full values.

## Runtime Data Separation

Packaged apps should not write into the app bundle. Runtime data is separated into a writable user data directory.

This protects user data across app updates and avoids broken writes in signed or packaged builds.

## Source Visibility in Releases

The release package avoids shipping Python source files directly:

- Electron UI is packed into ASAR.
- Python bridge is packaged as PyInstaller binaries.

This is not a cryptographic guarantee against reverse engineering, but it prevents casual source browsing in the installed app.

## Recommended Next Hardening

Before selling the app, add:

- license activation server
- signed update channel
- macOS notarization
- Windows code signing certificate
- encrypted local config storage
- crash-safe account file writes
- explicit export/import backup flow

## Operational Safety

Risky operations should continue to use:

- confirmation dialogs
- dry-run defaults
- live progress
- clear error output
- post-run summaries

This reduces accidental mass actions and makes failures visible.

