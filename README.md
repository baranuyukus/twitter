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

GitHub Actions builds macOS and Windows packages automatically when you push a tag like:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The release packages ship the Python bridge as PyInstaller binaries and package the Electron UI with ASAR.
