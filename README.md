# twitter

Tweeter Studio is a desktop control panel for the existing `tweeter.py` workflows.

## AI Provider

The app supports two OpenAI-compatible AI modes from Settings:

- ChatGPT OAuth proxy: run `npx openai-oauth` from the app or terminal, then use `http://127.0.0.1:10531/v1`.
- OpenAI API key: select API key mode and paste your key in Settings.

Both modes use the same preview, rewrite, reply and publish flows.

## Development

```bash
npm install
python3 -m pip install -r requirements.txt
npm start
```

## Checks

```bash
npm run check
```

## Release Builds

GitHub Actions builds macOS and Windows packages when you push a **version tag** (pushing `main` alone is not enough):

```bash
git tag v0.1.1
git push origin v0.1.1
```

Or run the **Release** workflow manually from GitHub Actions and enter the tag name.

The release packages ship the Python bridge as PyInstaller binaries and package the Electron UI with ASAR.

## Project Documentation

The implementation work is split into focused notes under `docs/`:

- `docs/00-overview.md`: project purpose, layers and current product shape.
- `docs/01-architecture.md`: Electron, JSON bridge and Python runtime flow.
- `docs/02-ui-ux.md`: page-by-page UI and UX decisions.
- `docs/03-account-import.md`: manual and bulk account import behavior.
- `docs/04-account-check.md`: live account check process.
- `docs/05-ai-provider.md`: OAuth proxy and API key AI modes.
- `docs/06-actions-and-logs.md`: bulk actions, dry-run and logging.
- `docs/07-release-and-github.md`: GitHub, Actions and release packaging.
- `docs/08-security-and-product-hardening.md`: credential boundaries and next hardening steps.
- `docs/09-change-log.md`: summary of implemented changes.
- `docs/11-proxy-settings.md`: optional proxy enable/disable behavior.
- `docs/10-runtime-account-mirror.md`: **critical** runtime account mirror — do not remove or break.
- `docs/12-smm-dashboard-ux.md`: Dashboard-centered SMM panel UX changes.
