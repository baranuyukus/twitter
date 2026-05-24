# AI Provider

## Purpose

The AI layer generates account-specific text variants for compose and reply workflows.

## Supported Providers

Tweeter Studio supports two OpenAI-compatible modes:

- OAuth proxy mode.
- OpenAI API key mode.

## OAuth Proxy Mode

OAuth proxy mode is intended for local use with:

```bash
npx openai-oauth
```

Default base URL:

```text
http://127.0.0.1:10531/v1
```

The app can start and stop the OAuth proxy from Settings.

## API Key Mode

API key mode uses a user-provided OpenAI API key. The key is stored in `app_config.json` in the runtime data directory and shown masked in the UI.

The Python layer reads it through:

```text
TWEETER_AI_API_KEY
```

## Shared Request Shape

The AI functions call an OpenAI-compatible:

```text
/v1/chat/completions
```

endpoint with:

- model
- messages
- max completion token limit
- timeout

## AI Workflows

AI is used for:

- Rewriting one base tweet into unique account-specific variants.
- Writing account-specific tweets from an instruction.
- Writing account-specific replies from an instruction.
- Optional AI rewrite for reply text.

## Configuration Source

`ui_config.py` is the central source for:

- provider
- base URL
- model
- timeout
- API key

`ui_api.py` and `ui_live.py` both apply this configuration before running AI-dependent work.

