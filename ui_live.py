#!/usr/bin/env python3
"""NDJSON streaming runner for long Tweeter UI actions."""

from __future__ import annotations

import contextlib
import json
import sys
import traceback
from typing import Any

import tweeter
import ui_config
from ui_api import _read_logs, _required, _select_accounts


class JsonLineEmitter:
    def __init__(self, stream_name: str):
        self.stream_name = stream_name
        self.buffer = ""

    def write(self, data: str) -> int:
        self.buffer += data
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip():
                emit({"type": "line", "stream": self.stream_name, "line": line})
        return len(data)

    def flush(self) -> None:
        if self.buffer.strip():
            emit({"type": "line", "stream": self.stream_name, "line": self.buffer})
        self.buffer = ""


def emit(event: dict[str, Any]) -> None:
    sys.__stdout__.write(json.dumps(event, ensure_ascii=False) + "\n")
    sys.__stdout__.flush()


def run_with_live_output(fn, *args, **kwargs):
    out = JsonLineEmitter("stdout")
    err = JsonLineEmitter("stderr")
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        result = fn(*args, **kwargs)
    out.flush()
    err.flush()
    return result


def selected(payload: dict[str, Any]) -> list[tweeter.Account]:
    accounts = _select_accounts(payload.get("indices"))
    if not accounts:
        raise ValueError("En az bir hesap seçilmeli.")
    return accounts


def run_action(payload: dict[str, Any]) -> dict[str, Any]:
    action = (payload.get("action") or "").strip()
    accounts = _select_accounts(payload.get("indices"))
    workers = int(payload.get("workers") or tweeter.DEFAULT_WORKERS)
    retry = int(payload.get("retry") or tweeter.DEFAULT_MAX_RETRY)
    delay = (
        float(payload.get("delayMin") or 0),
        float(payload.get("delayMax") or 0),
    )
    ai = ui_config.ai_request_options(payload)

    if bool(payload.get("dryRun", False)) and action not in {"fix-usernames", "purge"}:
        emit({"type": "line", "line": "[DRY-RUN] Gerçek işlem yapılmadı."})
        emit({"type": "line", "line": f"Aksiyon: {action}"})
        emit({"type": "line", "line": f"Hesap sayısı: {len(accounts)}"})
        emit({"type": "line", "line": f"Tweet ID: {payload.get('tweetId') or '-'}"})
        emit({"type": "line", "line": f"Kullanıcı: {payload.get('username') or '-'}"})
        emit({"type": "line", "line": f"Metin: {(payload.get('text') or payload.get('instruction') or '-')[:240]}"})
        return {"logs": _read_logs(50)}

    if action != "fix-usernames" and not accounts:
        raise ValueError("En az bir hesap seçilmeli.")

    if action == "like":
        result = run_with_live_output(tweeter.like_all, accounts, _required(payload, "tweetId", "Tweet ID gerekli."), workers=workers)
    elif action == "retweet":
        result = run_with_live_output(tweeter.retweet_all, accounts, _required(payload, "tweetId", "Tweet ID gerekli."), workers=workers)
    elif action == "follow":
        result = run_with_live_output(tweeter.follow_all, accounts, _required(payload, "username", "Kullanıcı adı gerekli.").lstrip("@"), workers=workers)
    elif action == "bookmark":
        result = run_with_live_output(tweeter.bookmark_all, accounts, _required(payload, "tweetId", "Tweet ID gerekli."), workers=workers)
    elif action == "reply":
        result = run_with_live_output(
            tweeter.reply_all,
            accounts,
            _required(payload, "tweetId", "Tweet ID gerekli."),
            _required(payload, "text", "Yanıt metni gerekli."),
            workers=workers,
            max_retry=retry,
            delay_range=delay,
            ai_rewrite=bool(payload.get("aiRewrite", False)),
            ai_dry_run=bool(payload.get("dryRun", False)),
            ai_base_url=ai["base_url"],
            ai_model=ai["model"],
        )
    elif action == "reply-ai":
        result = run_with_live_output(
            tweeter.reply_all_from_instruction,
            accounts,
            _required(payload, "tweetId", "Tweet ID gerekli."),
            _required(payload, "instruction", "AI yönergesi gerekli."),
            dry_run=bool(payload.get("dryRun", False)),
            delay_range=delay,
            workers=workers,
            max_retry=retry,
            ai_base_url=ai["base_url"],
            ai_model=ai["model"],
        )
    elif action == "view":
        result = run_with_live_output(
            tweeter.view_all,
            accounts,
            _required(payload, "tweetId", "Tweet ID gerekli."),
            repeat=max(1, int(payload.get("repeat") or 1)),
            workers=workers,
            delay_range=delay if delay[1] > 0 else (0.5, 2.0),
        )
    elif action == "protect":
        result = run_with_live_output(tweeter.protect_all, accounts, workers=workers)
    elif action == "unprotect":
        result = run_with_live_output(tweeter.unprotect_all, accounts, workers=workers)
    elif action == "follow-boost":
        result = run_with_live_output(tweeter.follow_boost, accounts, workers=workers, delay=float(payload.get("roundDelay") or 0.5))
    elif action == "boost":
        result = run_with_live_output(
            tweeter.boost_all,
            accounts,
            tweet_text=_required(payload, "text", "Tweet metni gerekli."),
            reply_text=(payload.get("replyText") or "🔥"),
            workers=workers,
            max_retry=retry,
            skip_follow=bool(payload.get("skipFollow", False)),
        )
    elif action == "fix-usernames":
        result = run_with_live_output(
            tweeter.fix_usernames,
            accounts or tweeter.load_accounts(),
            workers=workers,
            dry_run=bool(payload.get("dryRun", True)),
        )
    elif action == "purge":
        result = run_with_live_output(
            tweeter.purge_accounts,
            accounts,
            workers=workers,
            dry_run=bool(payload.get("dryRun", True)),
            deep=bool(payload.get("deep", False)),
        )
    else:
        raise ValueError(f"Bilinmeyen aksiyon: {action}")

    return {"result": result, "logs": _read_logs(50)}


def run_check(payload: dict[str, Any]) -> dict[str, Any]:
    accounts = selected(payload)
    results = run_with_live_output(
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
    return {"accounts": rows}


def run_post_variants(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("variants") or []
    if not rows:
        raise ValueError("Gönderilecek varyant yok.")

    accounts_by_name = {account.username.lower(): account for account in tweeter.load_accounts()}
    max_retry = int(payload.get("retry") or tweeter.DEFAULT_MAX_RETRY)
    reply_to = (payload.get("replyTo") or "").strip() or None
    images = payload.get("images") or None
    results = []

    emit({"type": "line", "line": f"Tweet gönderimi başladı. Kuyruk: {len(rows)} hesap"})
    if reply_to:
        emit({"type": "line", "line": f"Yanıt hedefi: {reply_to}"})
    if images:
        emit({"type": "line", "line": f"Görsel: {min(len(images), 4)} dosya"})

    for index, row in enumerate(rows, 1):
        username = str(row.get("username") or "").lstrip("@").strip()
        text = (row.get("text") or "").strip()
        enabled = bool(row.get("enabled", True))
        account = accounts_by_name.get(username.lower())

        def progress(status: str, detail: str = "") -> None:
            emit(
                {
                    "type": "progress",
                    "username": username,
                    "status": status,
                    "detail": detail,
                    "index": index,
                    "total": len(rows),
                }
            )

        if not enabled:
            progress("skipped", "Satır kapalı")
            emit({"type": "line", "line": f"@{username} → atlandı"})
            results.append({"username": username, "success": False, "skipped": True, "error": "Atlandı"})
            continue
        if not account:
            progress("error", "Hesap bulunamadı")
            emit({"type": "line", "line": f"@{username} → ✗ Hesap bulunamadı"})
            results.append({"username": username, "success": False, "error": "Hesap bulunamadı"})
            continue
        if not text:
            progress("error", "Metin boş")
            emit({"type": "line", "line": f"@{username} → ✗ Metin boş"})
            results.append({"username": username, "success": False, "error": "Metin boş"})
            continue

        progress("posting", "Twitter API çağrısı yapılıyor")
        emit({"type": "line", "line": f"@{username} → gönderiliyor ({index}/{len(rows)})"})
        result = run_with_live_output(
            tweeter.post_single,
            account,
            text,
            reply_to=reply_to,
            images=images,
            max_retry=max_retry,
        )
        success = bool(result.get("success"))
        detail = ""
        if success:
            detail = "Başarılı"
        else:
            detail = (result.get("stderr") or result.get("stdout") or "Gönderim başarısız")[:240]
        progress("success" if success else "error", detail)
        results.append(
            {
                "username": username,
                "success": success,
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "error": None if success else detail,
            }
        )

    ok_count = sum(1 for row in results if row.get("success"))
    fail_count = len(results) - ok_count
    emit({"type": "line", "line": f"Tamamlandı: ✓ {ok_count} başarılı, ✗ {fail_count} başarısız"})
    return {"results": results, "logs": _read_logs(50)}


COMMANDS = {
    "action": run_action,
    "check": run_check,
    "postVariants": run_post_variants,
}


def main() -> int:
    if len(sys.argv) < 2:
        emit({"type": "error", "error": "Komut eksik"})
        return 2
    command = sys.argv[1]
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    fn = COMMANDS.get(command)
    if not fn:
        emit({"type": "error", "error": f"Bilinmeyen komut: {command}"})
        return 2
    try:
        ui_config.apply_ai_env()
        data = fn(payload)
        emit({"type": "done", "data": data})
        return 0
    except Exception as exc:
        emit({"type": "error", "error": str(exc), "trace": traceback.format_exc(limit=5)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
