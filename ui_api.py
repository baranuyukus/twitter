#!/usr/bin/env python3
"""
Stable JSON bridge for the Tweeter desktop UI.

Electron calls this file with:
  python3 ui_api.py <command> '<json payload>'

The bridge imports tweeter.py, captures terminal-oriented output, and returns
machine-readable JSON so the UI is not coupled to ANSI logs or CLI wording.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import traceback
from pathlib import Path
from typing import Any

import tweeter
import ui_config

GROUPS_FILE = Path(__file__).parent / "account_groups.json"


def _account_to_public(account: tweeter.Account, index: int) -> dict[str, Any]:
    return {
        "index": index,
        "username": account.username,
        "authTokenPreview": _preview_secret(account.auth_token),
        "ct0Preview": _preview_secret(account.ct0),
        "hasCredentials": bool(account.auth_token and account.ct0),
    }


def _preview_secret(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    return value[:6] + "..." + value[-4:] if len(value) > 12 else value[:3] + "..."


def _load_accounts() -> list[tweeter.Account]:
    return tweeter.load_accounts()


def _select_accounts(indices: list[int] | None = None) -> list[tweeter.Account]:
    accounts = _load_accounts()
    if not indices:
        return accounts
    selected = []
    for index in indices:
        if 1 <= int(index) <= len(accounts):
            selected.append(accounts[int(index) - 1])
    return selected


def _capture(fn, *args, **kwargs) -> tuple[Any, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        value = fn(*args, **kwargs)
    return value, buf.getvalue()


def _read_logs(limit: int = 100) -> list[dict[str, Any]]:
    path = tweeter.LOG_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return data[-limit:][::-1]


def _settings() -> dict[str, Any]:
    proxies = tweeter.load_proxies()
    config = ui_config.public_config()
    return {
        "aiBaseUrl": tweeter.DEFAULT_AI_BASE_URL,
        "aiModel": tweeter.DEFAULT_AI_MODEL,
        "aiTimeout": tweeter.DEFAULT_AI_TIMEOUT,
        **config,
        "workers": tweeter.DEFAULT_WORKERS,
        "proxyCount": len(proxies),
        "proxyPreview": [
            tweeter._proxy_display_str(proxy) for proxy in proxies[:3]  # noqa: SLF001
        ],
        "twitterCli": " ".join(tweeter.get_twitter_cli_prefix()),
    }


def _load_groups() -> dict[str, list[str]]:
    if not GROUPS_FILE.exists():
        return {"All": []}
    try:
        data = json.loads(GROUPS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"All": []}
    if not isinstance(data, dict):
        return {"All": []}
    groups: dict[str, list[str]] = {"All": []}
    for name, users in data.items():
        if isinstance(name, str) and isinstance(users, list):
            groups[name] = [str(user) for user in users]
    return groups


def _save_groups(groups: dict[str, list[str]]) -> None:
    GROUPS_FILE.write_text(json.dumps(groups, ensure_ascii=False, indent=2), encoding="utf-8")


def _status(_: dict[str, Any]) -> dict[str, Any]:
    accounts = _load_accounts()
    logs = _read_logs(limit=1)
    return {
        "accounts": [_account_to_public(account, i) for i, account in enumerate(accounts, 1)],
        "accountCount": len(accounts),
        "groups": _load_groups(),
        "settings": _settings(),
        "latestLog": logs[0] if logs else None,
    }


def _logs(payload: dict[str, Any]) -> dict[str, Any]:
    return {"logs": _read_logs(int(payload.get("limit", 100)))}


def _preview_rewrite(payload: dict[str, Any]) -> dict[str, Any]:
    text = (payload.get("text") or "").strip()
    if not text:
        raise ValueError("Tweet metni boş olamaz.")
    accounts = _select_accounts(payload.get("indices"))
    if not accounts:
        raise ValueError("En az bir hesap seçilmeli.")
    ai = ui_config.ai_request_options(payload)
    variants, output = _capture(
        tweeter.build_ai_rewrites,
        accounts,
        text,
        base_url=ai["base_url"],
        model=ai["model"],
        timeout=ai["timeout"],
        workers=int(payload.get("workers") or tweeter.DEFAULT_WORKERS),
    )
    return {
        "variants": _variants_to_list(accounts, variants),
        "output": output,
    }


def _preview_instruction(payload: dict[str, Any]) -> dict[str, Any]:
    instruction = (payload.get("instruction") or "").strip()
    if not instruction:
        raise ValueError("Yönerge boş olamaz.")
    accounts = _select_accounts(payload.get("indices"))
    if not accounts:
        raise ValueError("En az bir hesap seçilmeli.")
    ai = ui_config.ai_request_options(payload)
    variants, output = _capture(
        tweeter.build_ai_composes,
        accounts,
        instruction,
        base_url=ai["base_url"],
        model=ai["model"],
        timeout=ai["timeout"],
        workers=int(payload.get("workers") or tweeter.DEFAULT_WORKERS),
    )
    return {
        "variants": _variants_to_list(accounts, variants),
        "output": output,
    }


def _variants_to_list(
    accounts: list[tweeter.Account],
    variants: dict[str, tuple[bool, str, str | None]],
) -> list[dict[str, Any]]:
    rows = []
    for account in accounts:
        ok, text, error = variants.get(account.username, (False, "", "AI varyantı yok"))
        rows.append(
            {
                "username": account.username,
                "ok": ok,
                "text": text,
                "error": error,
                "length": len(text or ""),
            }
        )
    return rows


def _post_variants(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("variants") or []
    if not rows:
        raise ValueError("Gönderilecek varyant yok.")

    accounts_by_name = {account.username: account for account in _load_accounts()}
    max_retry = int(payload.get("retry") or tweeter.DEFAULT_MAX_RETRY)
    reply_to = (payload.get("replyTo") or "").strip() or None
    images = payload.get("images") or None

    results = []
    output_parts = []
    for row in rows:
        username = row.get("username")
        text = (row.get("text") or "").strip()
        enabled = bool(row.get("enabled", True))
        account = accounts_by_name.get(username)
        if not enabled:
            results.append({"username": username, "success": False, "skipped": True, "error": "Atlandı"})
            continue
        if not account:
            results.append({"username": username, "success": False, "error": "Hesap bulunamadı"})
            continue
        if not text:
            results.append({"username": username, "success": False, "error": "Metin boş"})
            continue

        result, output = _capture(
            tweeter.post_single,
            account,
            text,
            reply_to=reply_to,
            images=images,
            max_retry=max_retry,
        )
        output_parts.append(output)
        results.append(
            {
                "username": username,
                "success": bool(result.get("success")),
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
            }
        )

    return {"results": results, "output": "\n".join(output_parts)}


def _check_accounts(payload: dict[str, Any]) -> dict[str, Any]:
    accounts = _select_accounts(payload.get("indices"))
    if not accounts:
        raise ValueError("En az bir hesap seçilmeli.")
    results, output = _capture(
        tweeter.check_accounts,
        accounts,
        workers=int(payload.get("workers") or tweeter.DEFAULT_WORKERS),
        deep=bool(payload.get("deep", False)),
    )
    rows = []
    for item in results:
        account = item.get("account")
        rows.append(
            {
                "username": account.username if account else "",
                "uid": item.get("uid"),
                "screenName": item.get("screen_name"),
                "label": item.get("label"),
                "ok": item.get("ok"),
                "writeOk": item.get("write_ok"),
                "error": item.get("err"),
            }
        )
    return {"accounts": rows, "output": output}


def _save_proxies(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("proxies") or ""
    lines = [line.strip() for line in raw.replace(",", "\n").splitlines() if line.strip()]
    normalized = [tweeter._normalize_proxy(line) for line in lines]  # noqa: SLF001
    content = "# DataImpulse / rotating proxy listesi\n" + "\n".join(normalized)
    if normalized:
        content += "\n"
    tweeter.PROXY_FILE.write_text(content, encoding="utf-8")
    return {"proxyCount": len(normalized)}


def _save_settings(payload: dict[str, Any]) -> dict[str, Any]:
    updates = {
        "aiProvider": payload.get("aiProvider") or "oauth",
        "aiBaseUrl": payload.get("aiBaseUrl") or tweeter.DEFAULT_AI_BASE_URL,
        "aiModel": payload.get("aiModel") or tweeter.DEFAULT_AI_MODEL,
        "aiTimeout": int(payload.get("aiTimeout") or tweeter.DEFAULT_AI_TIMEOUT),
    }
    api_key = payload.get("aiApiKey")
    if api_key is not None and str(api_key).strip() != "":
        updates["aiApiKey"] = str(api_key).strip()
    if bool(payload.get("clearAiApiKey", False)):
        updates["aiApiKey"] = ""
    config = ui_config.save_config(updates)
    return {"settings": {**_settings(), **ui_config.public_config(config)}}


def _run_action(payload: dict[str, Any]) -> dict[str, Any]:
    action = (payload.get("action") or "").strip()
    accounts = _select_accounts(payload.get("indices"))
    workers = int(payload.get("workers") or tweeter.DEFAULT_WORKERS)
    retry = int(payload.get("retry") or tweeter.DEFAULT_MAX_RETRY)
    delay = (
        float(payload.get("delayMin") or 0),
        float(payload.get("delayMax") or 0),
    )
    if not accounts and action not in {"fix-usernames"}:
        raise ValueError("En az bir hesap seçilmeli.")

    if bool(payload.get("dryRun", False)) and action not in {"fix-usernames", "purge"}:
        return {
            "output": (
                "[DRY-RUN]\n"
                f"Aksiyon       : {action}\n"
                f"Hesap sayısı  : {len(accounts)}\n"
                f"Tweet ID      : {payload.get('tweetId') or '-'}\n"
                f"Kullanıcı     : {payload.get('username') or '-'}\n"
                f"Metin         : {(payload.get('text') or payload.get('instruction') or '-')[:240]}\n"
                "Gerçek işlem yapılmadı. Çalıştırmak için Dry run seçimini kaldır."
            ),
            "logs": _read_logs(int(payload.get("logLimit") or 50)),
        }

    if action == "like":
        value = _required(payload, "tweetId", "Tweet ID gerekli.")
        _, output = _capture(tweeter.like_all, accounts, value, workers=workers)
    elif action == "retweet":
        value = _required(payload, "tweetId", "Tweet ID gerekli.")
        _, output = _capture(tweeter.retweet_all, accounts, value, workers=workers)
    elif action == "follow":
        value = _required(payload, "username", "Kullanıcı adı gerekli.").lstrip("@")
        _, output = _capture(tweeter.follow_all, accounts, value, workers=workers)
    elif action == "bookmark":
        value = _required(payload, "tweetId", "Tweet ID gerekli.")
        _, output = _capture(tweeter.bookmark_all, accounts, value, workers=workers)
    elif action == "reply":
        ai = ui_config.ai_request_options(payload)
        tweet_id = _required(payload, "tweetId", "Tweet ID gerekli.")
        text = _required(payload, "text", "Yanıt metni gerekli.")
        _, output = _capture(
            tweeter.reply_all,
            accounts,
            tweet_id,
            text,
            workers=workers,
            max_retry=retry,
            delay_range=delay,
            ai_rewrite=bool(payload.get("aiRewrite", False)),
            ai_dry_run=bool(payload.get("dryRun", False)),
            ai_base_url=ai["base_url"],
            ai_model=ai["model"],
        )
    elif action == "reply-ai":
        ai = ui_config.ai_request_options(payload)
        tweet_id = _required(payload, "tweetId", "Tweet ID gerekli.")
        instruction = _required(payload, "instruction", "AI yönergesi gerekli.")
        _, output = _capture(
            tweeter.reply_all_from_instruction,
            accounts,
            tweet_id,
            instruction,
            dry_run=bool(payload.get("dryRun", False)),
            delay_range=delay,
            workers=workers,
            max_retry=retry,
            ai_base_url=ai["base_url"],
            ai_model=ai["model"],
        )
    elif action == "view":
        value = _required(payload, "tweetId", "Tweet ID gerekli.")
        _, output = _capture(
            tweeter.view_all,
            accounts,
            value,
            repeat=max(1, int(payload.get("repeat") or 1)),
            workers=workers,
            delay_range=delay if delay[1] > 0 else (0.5, 2.0),
        )
    elif action == "protect":
        _, output = _capture(tweeter.protect_all, accounts, workers=workers)
    elif action == "unprotect":
        _, output = _capture(tweeter.unprotect_all, accounts, workers=workers)
    elif action == "follow-boost":
        _, output = _capture(
            tweeter.follow_boost,
            accounts,
            workers=workers,
            delay=float(payload.get("roundDelay") or 0.5),
        )
    elif action == "boost":
        text = _required(payload, "text", "Tweet metni gerekli.")
        _, output = _capture(
            tweeter.boost_all,
            accounts,
            tweet_text=text,
            reply_text=(payload.get("replyText") or "🔥"),
            workers=workers,
            max_retry=retry,
            skip_follow=bool(payload.get("skipFollow", False)),
        )
    elif action == "fix-usernames":
        _, output = _capture(
            tweeter.fix_usernames,
            accounts or _load_accounts(),
            workers=workers,
            dry_run=bool(payload.get("dryRun", True)),
        )
    elif action == "purge":
        _, output = _capture(
            tweeter.purge_accounts,
            accounts,
            workers=workers,
            dry_run=bool(payload.get("dryRun", True)),
            deep=bool(payload.get("deep", False)),
        )
    else:
        raise ValueError(f"Bilinmeyen aksiyon: {action}")

    return {
        "output": output,
        "logs": _read_logs(int(payload.get("logLimit") or 50)),
    }


def _required(payload: dict[str, Any], key: str, message: str) -> str:
    value = (payload.get(key) or "").strip()
    if not value:
        raise ValueError(message)
    return value


def _add_accounts(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("raw") or ""
    if not raw.strip():
        manual = payload.get("manual") or {}
        raw = ":".join(
            [
                manual.get("username", ""),
                manual.get("password", ""),
                manual.get("telephone", ""),
                manual.get("authToken", ""),
                manual.get("ct0", ""),
            ]
        )

    existing = {account.username.lower() for account in _load_accounts()}
    added: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    new_lines: list[str] = []

    for line_no, raw_line in enumerate(raw.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parsed = _parse_account_line(line)
        if not parsed:
            skipped.append({"line": line_no, "reason": "Format geçersiz"})
            continue
        username = parsed["username"].lstrip("@").strip()
        if not username:
            skipped.append({"line": line_no, "reason": "Kullanıcı adı boş"})
            continue
        if username.lower() in existing:
            skipped.append({"line": line_no, "username": username, "reason": "Duplicate"})
            continue
        existing.add(username.lower())
        account_line = ":".join(
            [
                username,
                parsed["password"],
                parsed["telephone"],
                parsed["authToken"],
                parsed["ct0"],
            ]
        )
        new_lines.append(account_line)
        added.append({"username": username})

    if new_lines:
        _append_lines(tweeter.ACCOUNTS_FILE, new_lines)

    accounts = _load_accounts()
    return {
        "added": added,
        "skipped": skipped,
        "accounts": [_account_to_public(account, i) for i, account in enumerate(accounts, 1)],
        "accountCount": len(accounts),
    }


def _delete_accounts(payload: dict[str, Any]) -> dict[str, Any]:
    usernames = {str(name).lstrip("@").lower() for name in payload.get("usernames", []) if str(name).strip()}
    indices = {int(index) for index in payload.get("indices", []) if str(index).isdigit()}
    accounts = _load_accounts()
    for index in indices:
        if 1 <= index <= len(accounts):
            usernames.add(accounts[index - 1].username.lower())
    if not usernames:
        raise ValueError("Silinecek hesap seçilmedi.")

    kept_lines: list[str] = []
    removed: list[str] = []
    with tweeter.ACCOUNTS_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                kept_lines.append(line)
                continue
            username = stripped.lstrip("@").split(":")[0].strip()
            if username.lower() in usernames:
                removed.append(username)
                continue
            kept_lines.append(line)

    tweeter.ACCOUNTS_FILE.write_text("".join(kept_lines), encoding="utf-8")

    groups = _load_groups()
    removed_lower = {name.lower() for name in removed}
    for group, users in list(groups.items()):
        groups[group] = [user for user in users if user.lower() not in removed_lower]
    _save_groups(groups)

    accounts = _load_accounts()
    return {
        "removed": removed,
        "accounts": [_account_to_public(account, i) for i, account in enumerate(accounts, 1)],
        "groups": groups,
    }


def _groups(payload: dict[str, Any]) -> dict[str, Any]:
    groups = _load_groups()
    op = (payload.get("op") or "list").strip()
    if op == "create":
        name = _required(payload, "name", "Grup adı gerekli.")
        groups.setdefault(name, [])
        _save_groups(groups)
    elif op == "assign":
        name = _required(payload, "name", "Grup adı gerekli.")
        accounts = _select_accounts(payload.get("indices"))
        users = [account.username for account in accounts]
        if not users:
            raise ValueError("Gruba eklenecek hesap seçilmedi.")
        existing = {user.lower(): user for user in groups.get(name, [])}
        for user in users:
            existing[user.lower()] = user
        groups[name] = sorted(existing.values(), key=str.lower)
        _save_groups(groups)
    elif op == "remove":
        name = _required(payload, "name", "Grup adı gerekli.")
        groups.pop(name, None)
        _save_groups(groups)
    elif op == "list":
        pass
    else:
        raise ValueError(f"Bilinmeyen grup işlemi: {op}")
    return {"groups": groups}


def _parse_account_line(line: str) -> dict[str, str] | None:
    parts = [part.strip() for part in line.split(":")]
    if len(parts) == 5:
        username, password, telephone, auth_token, ct0 = parts
        return {
            "username": username,
            "password": password,
            "telephone": telephone,
            "authToken": auth_token,
            "ct0": ct0,
        }
    if len(parts) == 7:
        username, password, email, _email_password, _twofa, ct0, auth_token = parts
        return {
            "username": username,
            "password": password,
            "telephone": email,
            "authToken": auth_token,
            "ct0": ct0,
        }
    return None


def _append_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_newline = False
    if path.exists() and path.stat().st_size > 0:
        with path.open("rb") as file:
            file.seek(-1, 2)
            needs_newline = file.read(1) != b"\n"
    with path.open("a", encoding="utf-8") as file:
        if needs_newline:
            file.write("\n")
        for line in lines:
            file.write(line + "\n")


COMMANDS = {
    "status": _status,
    "logs": _logs,
    "previewRewrite": _preview_rewrite,
    "previewInstruction": _preview_instruction,
    "postVariants": _post_variants,
    "checkAccounts": _check_accounts,
    "saveProxies": _save_proxies,
    "saveSettings": _save_settings,
    "runAction": _run_action,
    "addAccounts": _add_accounts,
    "deleteAccounts": _delete_accounts,
    "groups": _groups,
}


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Komut eksik"}))
        return 2

    command = sys.argv[1]
    try:
        payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    except json.JSONDecodeError as exc:
        print(json.dumps({"ok": False, "error": f"JSON okunamadı: {exc}"}))
        return 2

    fn = COMMANDS.get(command)
    if not fn:
        print(json.dumps({"ok": False, "error": f"Bilinmeyen komut: {command}"}))
        return 2

    try:
        ui_config.apply_ai_env()
        data = fn(payload)
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "trace": traceback.format_exc(limit=5),
                },
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
