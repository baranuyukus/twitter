# Architecture

## Runtime Flow

Electron never imports Python directly. It spawns Python commands and receives JSON:

1. Renderer calls `window.tweeterAPI.call()` or `window.tweeterAPI.stream()`.
2. `desktop/preload.js` forwards the request through IPC.
3. `desktop/main.js` starts either `ui_api.py` or `ui_live.py`.
4. Python imports `tweeter.py`, executes the requested workflow and returns structured JSON.
5. Renderer updates tables, status pills, consoles and logs.

This keeps the UI stable even if the CLI wording changes.

## Short Operations

`ui_api.py` is used for operations that can return a single response:

- `status`
- `logs`
- `previewRewrite`
- `previewInstruction`
- `postVariants` legacy non-stream path
- `checkAccounts` legacy non-stream path
- `saveProxies`
- `saveSettings`
- `addAccounts`
- `deleteAccounts`
- `groups`

## Long Operations

`ui_live.py` is used where the user must see progress immediately:

- `action`
- `check`
- `postVariants`

It writes newline-delimited JSON events:

- `line`: terminal-style output.
- `progress`: structured per-account progress.
- `done`: final result.
- `error`: exception or validation failure.
- `closed`: child process termination from Electron.

## Packaged App Behavior

During development, Electron runs:

```text
python3 ui_api.py ...
python3 ui_live.py ...
```

In packaged builds, Electron runs PyInstaller binaries:

```text
resources/bin/ui_api
resources/bin/ui_live
```

The Electron app is packed with ASAR. Python bridge binaries are copied as extra resources.

## Why This Design

The Python core remains the source of truth. The UI is a product layer over it, not a rewrite. This reduces breakage risk because the same functions power both the CLI heritage and the desktop experience.

