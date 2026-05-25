#!/usr/bin/env python3
"""NDJSON streaming runner for long Tweeter UI actions."""

from __future__ import annotations

import contextlib
import json
import re
import sys
import traceback
from datetime import datetime
from typing import Any

import tweeter
import ui_config
from ui_api import _read_logs, _required, _select_accounts


class JsonLineEmitter:
    def __init__(self, stream_name: str):
        self.stream_name = stream_name
        self.buffer = ""
        self.lines: list[str] = []

    def write(self, data: str) -> int:
        self.buffer += data
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip():
                self.lines.append(line)
                emit({"type": "line", "stream": self.stream_name, "line": line})
        return len(data)

    def flush(self) -> None:
        if self.buffer.strip():
            self.lines.append(self.buffer)
            emit({"type": "line", "stream": self.stream_name, "line": self.buffer})
        self.buffer = ""


def emit(event: dict[str, Any]) -> None:
    sys.__stdout__.write(json.dumps(event, ensure_ascii=False) + "\n")
    sys.__stdout__.flush()


def run_with_live_output(fn, *args, return_output: bool = False, **kwargs):
    out = JsonLineEmitter("stdout")
    err = JsonLineEmitter("stderr")
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        result = fn(*args, **kwargs)
    out.flush()
    err.flush()
    if return_output:
        return result, "\n".join([*out.lines, *err.lines])
    return result


def parse_action_counts(output: str, account_count: int) -> tuple[int, int, str]:
    text = strip_ansi(output)
    summary = re.search(
        r"Başarılı:\s*(\d+).*?Başarısız:\s*(\d+).*?Toplam:\s*(\d+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if summary:
        fail_count = int(summary.group(2))
        return int(summary.group(1)), fail_count, _first_error_line(text) if fail_count else ""

    success = len(re.findall(r"→\s*✓", text))
    failed = len(re.findall(r"→\s*✗", text))
    if success or failed:
        return success, failed, _first_error_line(text)

    if account_count and re.search(r"\b(ok|success|başarılı|tamamlandı)\b", text, flags=re.IGNORECASE):
        return account_count, 0, ""
    return 0, account_count if account_count else 0, _first_error_line(text)


def _first_error_line(text: str) -> str:
    for line in text.splitlines():
        if "→ ✗" in line or re.search(r"\b(error|hata|başarısız|failed)\b", line, flags=re.IGNORECASE):
            return line.strip()[:240]
    return ""


def strip_ansi(value: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", str(value or ""))


def selected(payload: dict[str, Any]) -> list[tweeter.Account]:
    accounts = _select_accounts(payload.get("indices"))
    if not accounts:
        raise ValueError("En az bir hesap seçilmeli.")
    return accounts


def run_action(payload: dict[str, Any]) -> dict[str, Any]:
    action = (payload.get("action") or "").strip()
    accounts = _select_accounts(payload.get("indices"))
    started_at = datetime.now().isoformat(timespec="seconds")
    workers = int(payload.get("workers") or tweeter.DEFAULT_WORKERS)
    retry = int(payload.get("retry") or tweeter.DEFAULT_MAX_RETRY)
    delay = (
        float(payload.get("delayMin") or 0),
        float(payload.get("delayMax") or 0),
    )
    ai = ui_config.ai_request_options(payload)
    use_proxy = bool(payload.get("useProxy", ui_config.public_config().get("proxyEnabled", False)))
    ui_config.apply_runtime_env({**ui_config.load_config(), "proxyEnabled": use_proxy})
    emit({"type": "line", "line": f"Proxy: {'aktif' if use_proxy else 'kapalı'}"})

    if action != "fix-usernames" and not accounts:
        raise ValueError("En az bir hesap seçilmeli.")

    if action == "like":
        result, output = run_with_live_output(tweeter.like_all, accounts, _required(payload, "tweetId", "Tweet ID gerekli."), workers=workers, return_output=True)
    elif action == "retweet":
        result, output = run_with_live_output(tweeter.retweet_all, accounts, _required(payload, "tweetId", "Tweet ID gerekli."), workers=workers, return_output=True)
    elif action == "follow":
        result, output = run_with_live_output(tweeter.follow_all, accounts, _required(payload, "username", "Kullanıcı adı gerekli.").lstrip("@"), workers=workers, return_output=True)
    elif action == "bookmark":
        result, output = run_with_live_output(tweeter.bookmark_all, accounts, _required(payload, "tweetId", "Tweet ID gerekli."), workers=workers, return_output=True)
    elif action == "reply":
        result, output = run_with_live_output(
            tweeter.reply_all,
            accounts,
            _required(payload, "tweetId", "Tweet ID gerekli."),
            _required(payload, "text", "Yanıt metni gerekli."),
            workers=workers,
            max_retry=retry,
            delay_range=delay,
            ai_rewrite=bool(payload.get("aiRewrite", False)),
            ai_dry_run=False,
            ai_base_url=ai["base_url"],
            ai_model=ai["model"],
            return_output=True,
        )
    elif action == "reply-ai":
        result, output = run_with_live_output(
            tweeter.reply_all_from_instruction,
            accounts,
            _required(payload, "tweetId", "Tweet ID gerekli."),
            _required(payload, "instruction", "AI yönergesi gerekli."),
            dry_run=False,
            delay_range=delay,
            workers=workers,
            max_retry=retry,
            ai_base_url=ai["base_url"],
            ai_model=ai["model"],
            return_output=True,
        )
    elif action == "view":
        result, output = run_with_live_output(
            tweeter.view_all,
            accounts,
            _required(payload, "tweetId", "Tweet ID gerekli."),
            repeat=max(1, int(payload.get("repeat") or 1)),
            workers=workers,
            delay_range=delay if delay[1] > 0 else (0.5, 2.0),
            return_output=True,
        )
    elif action == "protect":
        result, output = run_with_live_output(tweeter.protect_all, accounts, workers=workers, return_output=True)
    elif action == "unprotect":
        result, output = run_with_live_output(tweeter.unprotect_all, accounts, workers=workers, return_output=True)
    elif action == "follow-boost":
        result, output = run_with_live_output(tweeter.follow_boost, accounts, workers=workers, delay=float(payload.get("roundDelay") or 0.5), return_output=True)
    elif action == "boost":
        result, output = run_with_live_output(
            tweeter.boost_all,
            accounts,
            tweet_text=_required(payload, "text", "Tweet metni gerekli."),
            reply_text=(payload.get("replyText") or "🔥"),
            workers=workers,
            max_retry=retry,
            skip_follow=bool(payload.get("skipFollow", False)),
            return_output=True,
        )
    elif action == "fix-usernames":
        result, output = run_with_live_output(
            tweeter.fix_usernames,
            accounts or tweeter.load_accounts(),
            workers=workers,
            dry_run=False,
            return_output=True,
        )
    elif action == "purge":
        result, output = run_with_live_output(
            tweeter.purge_accounts,
            accounts,
            workers=workers,
            dry_run=False,
            deep=bool(payload.get("deep", False)),
            return_output=True,
        )
    else:
        raise ValueError(f"Bilinmeyen aksiyon: {action}")

    success_count, fail_count, last_error = parse_action_counts(output, len(accounts))
    ui_config.record_campaign(
        {
            "type": action or "action",
            "title": f"Operation: {action}",
            "target": payload.get("tweetId") or payload.get("username") or "",
            "accountCount": len(accounts),
            "successCount": success_count,
            "failCount": fail_count,
            "status": "completed",
            "startedAt": started_at,
            "lastError": last_error,
        }
    )
    return {"result": result, "logs": _read_logs(50), "campaigns": ui_config.read_campaign_history(20)}


def run_check(payload: dict[str, Any]) -> dict[str, Any]:
    accounts = selected(payload)
    started_at = datetime.now().isoformat(timespec="seconds")
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
    ui_config._side_effect_check(accounts, results)
    ok_count = sum(1 for row in rows if row.get("ok"))
    ui_config.record_campaign(
        {
            "type": "check",
            "title": "Account health check",
            "target": "deep" if bool(payload.get("deep", False)) else "surface",
            "accountCount": len(accounts),
            "successCount": ok_count,
            "failCount": len(rows) - ok_count,
            "status": "completed",
            "startedAt": started_at,
            "lastError": next((row.get("error") or "" for row in rows if not row.get("ok")), ""),
        }
    )
    return {"accounts": rows, "campaigns": ui_config.read_campaign_history(20)}


def run_post_variants(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("variants") or []
    started_at = datetime.now().isoformat(timespec="seconds")
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
    ui_config.record_campaign(
        {
            "type": "post",
            "title": "Tweet publish",
            "target": reply_to or "timeline",
            "accountCount": len(rows),
            "successCount": ok_count,
            "failCount": fail_count,
            "status": "completed",
            "startedAt": started_at,
            "lastError": next((row.get("error") or row.get("stderr") or "" for row in results if not row.get("success")), ""),
        }
    )
    return {"results": results, "logs": _read_logs(50), "campaigns": ui_config.read_campaign_history(20)}


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
