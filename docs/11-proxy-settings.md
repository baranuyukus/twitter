# Proxy Settings

## Purpose

Proxy usage is optional. Users can keep a proxy list saved in `proxy.txt` and decide separately whether Twitter actions should use it.

## Runtime Behavior

Proxy behavior is controlled by `proxyEnabled` in `app_config.json`.

- `proxyEnabled: true`: `tweeter.py` uses the proxy pool and passes `HTTP_PROXY` / `HTTPS_PROXY` to Twitter CLI child processes.
- `proxyEnabled: false`: proxy records may still exist, but no proxy environment variables are passed to Twitter CLI child processes.

This lets users switch proxy use on and off without deleting the proxy list.

## UI Flow

Settings contains:

- `Use proxy for Twitter actions` checkbox.
- Proxy list textarea.
- `Save proxy settings` button.

Saving proxy settings updates both `proxy.txt` and the proxy enabled flag.

## Implementation Notes

- `ui_config.py` persists `proxyEnabled`.
- `ui_config.apply_runtime_env()` exports `TWEETER_PROXY_ENABLED`.
- `tweeter.get_proxy()` returns `None` when proxy is disabled.
- `ui_api._settings()` returns proxy count and enabled state for the UI.

## Safety

Proxy disable does not delete saved proxies. Clearing the textarea and saving removes the saved proxy list.

