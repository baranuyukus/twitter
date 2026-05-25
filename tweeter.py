#!/usr/bin/env python3
"""
Tweeter - Çoklu Twitter Hesap Yönetim Sistemi
twitter-cli kullanarak birden fazla hesaptan tweet atma aracı.
"""

from __future__ import annotations

import subprocess
import sys
import os
import time
import random
import json
import argparse
import threading
import difflib
import unicodedata
import shutil
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests as _requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    from twitter_cli.client import TwitterClient as _TwitterClient
    _TWCLIENT_OK = True
except ImportError:
    _TWCLIENT_OK = False

# ─── Renk Kodları ───
class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    GRAY    = "\033[90m"
    BG_GREEN  = "\033[42m"
    BG_RED    = "\033[41m"
    BG_BLUE   = "\033[44m"

# ─── Sabitler ───
APP_DIR = Path(os.environ.get("TWEETER_DATA_DIR", Path(__file__).parent)).expanduser()
APP_DIR.mkdir(parents=True, exist_ok=True)
ACCOUNTS_FILE = APP_DIR / "accounts.txt"
LOG_FILE      = APP_DIR / "tweet_log.json"
PROXY_FILE    = APP_DIR / "proxy.txt"

_twitter_cli_prefix_cache: list[str] | None = None


def get_twitter_cli_prefix() -> list[str]:
    """
    twitter-cli çalıştırma komutunun öneki: ['/path/to/twitter'] veya
    [sys.executable, '-m', 'twitter_cli.cli'].

    Öncelik: TWEETER_TWITTER_BIN → projedeki venv|env|.venv/bin/twitter → PATH → python -m
    """
    global _twitter_cli_prefix_cache
    if _twitter_cli_prefix_cache is not None:
        return _twitter_cli_prefix_cache

    env_bin = os.environ.get("TWEETER_TWITTER_BIN", "").strip()
    if env_bin:
        _twitter_cli_prefix_cache = [env_bin]
        return _twitter_cli_prefix_cache

    base = Path(__file__).resolve().parent
    for sub in ("venv", "env", ".venv"):
        candidate = base / sub / "bin" / "twitter"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            _twitter_cli_prefix_cache = [str(candidate)]
            return _twitter_cli_prefix_cache

    wh = shutil.which("twitter")
    if wh:
        _twitter_cli_prefix_cache = [wh]
        return _twitter_cli_prefix_cache

    _twitter_cli_prefix_cache = [sys.executable, "-m", "twitter_cli.cli"]
    return _twitter_cli_prefix_cache

DEFAULT_WORKERS   = 10   # Aynı anda çalışan maksimum thread sayısı
DEFAULT_MAX_RETRY = 2    # Başarısız işlemde kaç kez yeniden dene
RETRY_BASE_DELAY  = 2.0  # İlk retry bekleme süresi (saniye)
DEFAULT_TIMEOUT   = 60   # Varsayılan komut timeout (saniye)

DEFAULT_AI_BASE_URL = os.environ.get("TWEETER_AI_BASE_URL", "http://127.0.0.1:10531/v1")
DEFAULT_AI_MODEL    = os.environ.get("TWEETER_AI_MODEL", "gpt-5.4-mini")
DEFAULT_AI_TIMEOUT  = int(os.environ.get("TWEETER_AI_TIMEOUT", "60"))
AI_STYLE_HINTS = [
    "net ve kısa bir cümle",
    "daha doğal, günlük konuşma dili",
    "daha profesyonel ve sakin ton",
    "daha enerjik ama abartısız ton",
    "farklı söz dizimi ve daha akıcı ifade",
    "daha minimal ve direkt anlatım",
]

# ─── Proxy Havuzu (DataImpulse Rotating) ───
#
# proxy.txt formatları:
#   Tek satır  → http://user:pass@gw.dataimpulse.com:823
#   Çok satır  → Her satır ayrı proxy; round-robin rotasyon yapılır
#
# DataImpulse'un rotating gateway'i (gw.dataimpulse.com:823) her yeni
# bağlantıda otomatik farklı IP verir — tek satır yeterlidir.
# Birden fazla satır varsa her istek farklı satırı sırayla kullanır.
#
# Ortam değişkeni: TWEETER_PROXY=proxy1,proxy2,...  (virgülle ayrılmış)

_PROXY_POOL:    list[str] = []
_proxy_counter: int       = 0
_proxy_lock     = threading.Lock()


def load_proxies() -> list[str]:
    """proxy.txt'deki tüm proxy satırlarını yükler, liste döndürür."""
    proxies: list[str] = []
    if "TWEETER_PROXY" in os.environ:
        for part in os.environ["TWEETER_PROXY"].split(","):
            part = part.strip()
            if part:
                proxies.append(part)
        return proxies
    if PROXY_FILE.exists():
        for line in PROXY_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                proxies.append(line)
    return proxies


def proxy_enabled() -> bool:
    """Proxy kullanımı runtime ayarı ile açılıp kapatılır."""
    raw = os.environ.get("TWEETER_PROXY_ENABLED", "1").strip().lower()
    return raw in {"1", "true", "yes", "on", "enabled", "aktif"}


def get_proxy() -> str | None:
    """
    Thread-safe round-robin proxy seçici.
    Her çağrıda havuzdaki sıradaki proxy'yi döndürür.
    DataImpulse tek-satır kullanımında gateway zaten otomatik rotate eder.
    """
    global _proxy_counter
    if not proxy_enabled():
        return None
    if not _PROXY_POOL:
        return None
    with _proxy_lock:
        proxy = _PROXY_POOL[_proxy_counter % len(_PROXY_POOL)]
        _proxy_counter += 1
    return proxy


def _normalize_proxy(raw: str) -> str:
    """Proxy URL'e gerekirse http:// öneki ekler."""
    if raw and not raw.startswith(("http://", "https://", "socks5://")):
        return "http://" + raw
    return raw


_PROXY_POOL = load_proxies()

# ─── Thread-safe Kilit ───
_print_lock = threading.Lock()
_log_lock   = threading.Lock()

def tprint(*args, **kwargs):
    """Thread-safe print."""
    with _print_lock:
        print(*args, **kwargs)

def twrite(text: str):
    """Thread-safe sys.stdout.write."""
    with _print_lock:
        sys.stdout.write(text)
        sys.stdout.flush()

# ─── Hesap Sınıfı ───
class Account:
    def __init__(self, username: str, password: str, telephone: str, auth_token: str, ct0: str):
        self.username   = username
        self.password   = password
        self.telephone  = telephone
        self.auth_token = auth_token
        self.ct0        = ct0

    def __repr__(self):
        return f"@{self.username}"

# ─── Hesap Yükleme ───
def load_accounts(filepath: Path = ACCOUNTS_FILE) -> list[Account]:
    """accounts.txt dosyasından hesapları yükler."""
    accounts = []
    if not filepath.exists():
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.touch()
        return accounts

    with open(filepath, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("@"):
                line = line[1:]
            parts = line.split(":")
            if len(parts) != 5:
                print(f"{Colors.YELLOW}⚠ Satır {line_num}: Geçersiz format, atlanıyor{Colors.RESET}")
                continue
            username, password, telephone, auth_token, ct0 = parts
            accounts.append(
                Account(
                    username.strip(),
                    password.strip(),
                    telephone.strip(),
                    auth_token.strip(),
                    ct0.strip(),
                )
            )

    return accounts


def _cli_credentials_ok(account: Account) -> tuple[bool, str | None]:
    """twitter-cli eksik env ile tarayıcı oturumuna düşmesin diye ön kontrol."""
    if not (account.auth_token or "").strip() or not (account.ct0 or "").strip():
        return (
            False,
            "auth_token veya ct0 boş — daha önce twitter-cli tarayıcıdaki hesaba (ör. ana hesap) düşebilirdi",
        )
    return True, None


# ─── Twitter CLI Çalıştırma ───
def run_twitter_command(account: Account, args: list[str], timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    Belirtilen hesap ile twitter-cli komutunu çalıştırır. Proxy varsa rotating olarak geçer.

    TWITTER_CLI_ENV_ONLY=1 ile twitter-cli tarayıcı çerezine hiç dönmez; sadece bu hesabın
    token'ları kullanılır (yanlış hesaba tweet atılmasını önler).
    """
    ok, cred_err = _cli_credentials_ok(account)
    if not ok:
        return {"success": False, "stdout": "", "stderr": cred_err or "Eksik credential", "returncode": -1}

    env = os.environ.copy()
    env["TWITTER_CLI_ENV_ONLY"] = "1"
    env["TWITTER_AUTH_TOKEN"] = account.auth_token.strip()
    env["TWITTER_CT0"]        = account.ct0.strip()

    proxy = get_proxy()
    if proxy:
        env["HTTP_PROXY"]  = proxy
        env["HTTPS_PROXY"] = proxy
        env["http_proxy"]  = proxy
        env["https_proxy"] = proxy

    cmd = get_twitter_cli_prefix() + args

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success":    result.returncode == 0,
            "stdout":     result.stdout.strip(),
            "stderr":     result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": f"Zaman aşımı ({timeout}s)", "returncode": -1}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}

# ─── Ortak JSON Parse ───
def parse_twitter_response(result: dict) -> tuple[bool, str | None]:
    """twitter-cli JSON çıktısını parse eder. (success, error_msg) döndürür."""
    if result["stdout"]:
        try:
            json_data = json.loads(result["stdout"])
            if json_data.get("ok"):
                return True, None
            err_info = json_data.get("error", {})
            return False, err_info.get("message", "Bilinmeyen API hatası")
        except json.JSONDecodeError:
            pass
    return False, result["stderr"][:100] if result["stderr"] else "Bilinmeyen hata"


def _transient_twitter_error(result: dict) -> bool:
    """
    Twitter bazen geçerli token ile 401/429 döner (proxy IP değişimi, kısa anti-bot,
    ağ dalgalanması). Bu durumda birkaç kez daha bekleyip denemek işe yarar.
    """
    blob = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"
    low = blob.lower()
    if "could not authenticate" in low:
        return True
    if '"code":32' in blob.replace(" ", "") or '"code": 32' in blob or "code\":32" in blob:
        return True
    if "401" in blob and ("twitter api" in low or "http 401" in low):
        return True
    if "429" in blob and ("rate" in low or "too many" in low or "limit" in low):
        return True
    return False


# ─── Retry ile Komut Çalıştırma ───
def run_with_retry(
    account: Account,
    args: list[str],
    timeout: int = 30,
    max_retry: int = DEFAULT_MAX_RETRY,
) -> tuple[dict, int]:
    """
    Komutu çalıştırır; başarısız olursa exponential backoff ile yeniden dener.

    401 / authenticate / 429 gibi geçici yanıtlarda TWEETER_EXTRA_401_RETRIES kadar
    (varsayılan 6) ek tur dener; aralar 7–20+ sn rasgele bekler. Aynı satırdaki token
    bazen ilk istekte düşüp ikincide geçebilir — özellikle dönen proxy ile.
    """
    normal_tries = max_retry + 1
    extra_cap = int(os.environ.get("TWEETER_EXTRA_401_RETRIES", "6"))
    max_passes = normal_tries + max(0, extra_cap)

    attempt = 0
    result: dict = {}

    while attempt < max_passes:
        result = run_twitter_command(account, args, timeout=timeout)
        ok, _ = parse_twitter_response(result)
        if ok:
            return result, min(attempt, max_retry)

        transient = _transient_twitter_error(result)
        at_last_normal_slot = attempt == normal_tries - 1

        if at_last_normal_slot:
            if not transient:
                break
            time.sleep(6.0 + random.uniform(0, 6) + random.uniform(0, 4))
        elif attempt > normal_tries - 1:
            if not transient:
                break
            time.sleep(7.0 + random.uniform(0, 8) + (attempt - normal_tries) * 2.0)
        else:
            wait = RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
            if transient:
                wait = max(wait, 5.0 + random.uniform(0, 4))
            time.sleep(wait)

        attempt += 1

    return result, min(attempt, max_retry)

# ─── Thread-safe Log ───
def log_result(account: Account, action: str, target: str, result: dict):
    """Sonucu JSON log dosyasına thread-safe şekilde kaydeder."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "username":  account.username,
        "action":    action,
        "target":    target[:200],
        "success":   result["success"],
        "stdout":    result["stdout"][:500],
        "stderr":    result["stderr"][:500],
    }
    with _log_lock:
        logs = []
        if LOG_FILE.exists():
            try:
                with open(LOG_FILE, "r") as f:
                    logs = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logs = []
        logs.append(entry)
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)


# ─── AI Tweet Yeniden Yazma ───
def _clean_ai_tweet(text: str) -> str:
    """Model cevabından tek tweet metnini çıkarır."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        cleaned = cleaned[1:-1].strip()
    return " ".join(cleaned.split())


def _similarity_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return "".join(ch for ch in normalized if ch.isalnum() or ch.isspace()).strip()


def _too_similar_to_seen(text: str, seen: list[str], threshold: float = 0.86) -> bool:
    key = _similarity_key(text)
    return any(difflib.SequenceMatcher(None, key, old).ratio() >= threshold for old in seen)


def rewrite_tweet_with_ai(
    original_text: str,
    account: Account,
    variant_no: int,
    total_variants: int,
    *,
    base_url: str = DEFAULT_AI_BASE_URL,
    model: str = DEFAULT_AI_MODEL,
    timeout: int = DEFAULT_AI_TIMEOUT,
) -> tuple[bool, str, str | None]:
    """
    OpenAI-compatible /v1/chat/completions endpoint'i ile tweet metnini
    hesap başına farklı bir varyanta çevirir.
    """
    if not _REQUESTS_OK:
        return False, original_text, "requests kütüphanesi bulunamadı"

    endpoint = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("TWEETER_AI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sen sosyal medya metin editörüsün. Kullanıcının verdiği tweeti "
                    "aynı anlamı koruyarak doğal, kısa ve yayınlanabilir Türkçe ile yeniden yaz. "
                    "Yeni bilgi uydurma. Linkleri, @kullanıcı adlarını ve hashtagleri aynen koru. "
                    "Orijinal metinde olmayan @mention, hashtag veya link ekleme. "
                    "Yanıt olarak sadece tweet metnini ver; açıklama, seçenek listesi veya tırnak ekleme. "
                    "280 karakter sınırını aşma."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Orijinal tweet:\n{original_text}\n\n"
                    f"Bu {total_variants} varyanttan {variant_no}. varyant olacak. "
                    f"Hesap adı sadece varyant üretimi için bağlamdır, tweet'e ekleme: @{account.username}. "
                    f"Stil ipucu: {AI_STYLE_HINTS[(variant_no - 1) % len(AI_STYLE_HINTS)]}. "
                    "Sadece noktalama, aksan veya tek kelime değişikliği yapma; cümle yapısını belirgin değiştir. "
                    "Diğer varyantlardan farklı kelime seçimi ve cümle ritmi kullan; anlam aynı kalsın."
                ),
            },
        ],
        "max_completion_tokens": 120,
    }

    try:
        resp = _requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
        if resp.status_code >= 400:
            return False, original_text, f"AI HTTP {resp.status_code}: {resp.text[:160]}"
        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        rewritten = _clean_ai_tweet(content)
        if not rewritten:
            return False, original_text, "AI boş metin döndürdü"
        if len(rewritten) > 280:
            return False, original_text, f"AI metni 280 karakteri aştı ({len(rewritten)})"
        return True, rewritten, None
    except Exception as exc:
        return False, original_text, str(exc)[:180]


def build_ai_rewrites(
    accounts: list[Account],
    text: str,
    *,
    base_url: str = DEFAULT_AI_BASE_URL,
    model: str = DEFAULT_AI_MODEL,
    timeout: int = DEFAULT_AI_TIMEOUT,
    workers: int = DEFAULT_WORKERS,
) -> dict[str, tuple[bool, str, str | None]]:
    """Seçili hesaplar için AI varyantlarını paralel üretir."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}AI tweet varyantları hazırlanıyor{Colors.RESET}")
    print(f"  {Colors.GRAY}Model   : {model}{Colors.RESET}")
    print(f"  {Colors.GRAY}Endpoint: {base_url.rstrip('/')}/chat/completions{Colors.RESET}")
    print(f"  {Colors.GRAY}Hesap   : {len(accounts)}{Colors.RESET}\n")

    results: dict[str, tuple[bool, str, str | None]] = {}
    seen: list[str] = []
    lock = threading.Lock()

    def task(item: tuple[int, Account]):
        idx, acc = item
        ok = False
        rewritten = text
        err = None

        for attempt in range(3):
            ok, rewritten, err = rewrite_tweet_with_ai(
                text,
                acc,
                idx + 1 + (attempt * len(accounts)),
                len(accounts),
                base_url=base_url,
                model=model,
                timeout=timeout,
            )
            with lock:
                duplicate = ok and _too_similar_to_seen(rewritten, seen)
                if ok and not duplicate:
                    seen.append(_similarity_key(rewritten))
                    results[acc.username] = (ok, rewritten, err)
                    break
                if not ok:
                    results[acc.username] = (ok, rewritten, err)
                    break
                if attempt == 2:
                    ok = False
                    err = "AI yeterince farklı varyant üretemedi"
                    results[acc.username] = (ok, rewritten, err)
                    break

        if ok:
            preview = rewritten[:90] + ("..." if len(rewritten) > 90 else "")
            tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → {Colors.GREEN}✓{Colors.RESET} {preview}")
        else:
            tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → {Colors.RED}✗ {err}{Colors.RESET}")

    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        list(pool.map(task, enumerate(accounts)))

    return results


def compose_tweet_with_ai(
    instruction: str,
    account: Account,
    variant_no: int,
    total_variants: int,
    *,
    base_url: str = DEFAULT_AI_BASE_URL,
    model: str = DEFAULT_AI_MODEL,
    timeout: int = DEFAULT_AI_TIMEOUT,
) -> tuple[bool, str, str | None]:
    """
    OpenAI-compatible /v1/chat/completions ile kullanıcı yönergesinden
    hesap başına özgün tek bir tweet üretir (openai-oauth proxy ile uyumlu).
    """
    if not _REQUESTS_OK:
        return False, "", "requests kütüphanesi bulunamadı"

    endpoint = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("TWEETER_AI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sen Twitter/X için kısa metin yazıyorsun. Kullanıcının YÖNERGESİNE göre "
                    "tek bir yayınlanabilir tweet yaz. Yönergede olmayan gerçek iddiası veya olay uydurma. "
                    "Yanıtta sadece tweet metni olsun; açıklama, başlık, numara veya tırnak işareti kullanma. "
                    "280 karakteri geçme. Yönergedeki dilde ve üslupta yaz."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Yönerge:\n{instruction.strip()}\n\n"
                    f"Toplam {total_variants} farklı hesap için benzersiz içerik üretilecek; "
                    f"bu {variant_no}. varyant. Hesap adı sadece üslup çeşitliliği için bağlamdır, "
                    f"tweet metnine '@{account.username}' yazma (yönergede istenmedikçe). "
                    f"Stil ipucu: {AI_STYLE_HINTS[(variant_no - 1) % len(AI_STYLE_HINTS)]}. "
                    "Diğer varyantlardan kelime ve cümle yapısı olarak belirgin şekilde farklı ol."
                ),
            },
        ],
        "max_completion_tokens": 180,
    }

    try:
        resp = _requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
        if resp.status_code >= 400:
            return False, "", f"AI HTTP {resp.status_code}: {resp.text[:160]}"
        data = resp.json()
        content = (
            data.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        composed = _clean_ai_tweet(content)
        if not composed:
            return False, "", "AI boş metin döndürdü"
        if len(composed) > 280:
            return False, "", f"AI metni 280 karakteri aştı ({len(composed)})"
        return True, composed, None
    except Exception as exc:
        return False, "", str(exc)[:180]


def build_ai_composes(
    accounts: list[Account],
    instruction: str,
    *,
    base_url: str = DEFAULT_AI_BASE_URL,
    model: str = DEFAULT_AI_MODEL,
    timeout: int = DEFAULT_AI_TIMEOUT,
    workers: int = DEFAULT_WORKERS,
) -> dict[str, tuple[bool, str, str | None]]:
    """Yönergeye göre her hesap için AI ile özgün tweet metni üretir."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}AI — yönergeden tweet üretiliyor{Colors.RESET}")
    print(f"  {Colors.GRAY}Model   : {model}{Colors.RESET}")
    print(f"  {Colors.GRAY}Endpoint: {base_url.rstrip('/')}/chat/completions{Colors.RESET}")
    print(f"  {Colors.GRAY}Hesap   : {len(accounts)}{Colors.RESET}")
    print(f"  {Colors.GRAY}Yönerge : \"{instruction[:100]}{'...' if len(instruction) > 100 else ''}\"{Colors.RESET}\n")

    results: dict[str, tuple[bool, str, str | None]] = {}
    seen: list[str] = []
    lock = threading.Lock()

    def task(item: tuple[int, Account]):
        idx, acc = item
        ok = False
        text = ""
        err = None

        for attempt in range(3):
            ok, text, err = compose_tweet_with_ai(
                instruction,
                acc,
                idx + 1 + (attempt * len(accounts)),
                len(accounts),
                base_url=base_url,
                model=model,
                timeout=timeout,
            )
            with lock:
                duplicate = ok and _too_similar_to_seen(text, seen)
                if ok and not duplicate:
                    seen.append(_similarity_key(text))
                    results[acc.username] = (ok, text, err)
                    break
                if not ok:
                    results[acc.username] = (ok, text, err)
                    break
                if attempt == 2:
                    ok = False
                    err = "AI yeterince farklı metin üretemedi"
                    results[acc.username] = (ok, text, err)
                    break

        if ok:
            preview = text[:90] + ("..." if len(text) > 90 else "")
            tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → {Colors.GREEN}✓{Colors.RESET} {preview}")
        else:
            tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → {Colors.RED}✗ {err}{Colors.RESET}")

    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        list(pool.map(task, enumerate(accounts)))

    return results


def compose_reply_with_ai(
    instruction: str,
    reply_to_tweet_id: str,
    account: Account,
    variant_no: int,
    total_variants: int,
    *,
    base_url: str = DEFAULT_AI_BASE_URL,
    model: str = DEFAULT_AI_MODEL,
    timeout: int = DEFAULT_AI_TIMEOUT,
) -> tuple[bool, str, str | None]:
    """
    Yönergeye göre belirli bir tweet'e yanıt olacak kısa metin üretir (hesap başına farklı).
    Orijinal gönderi metni bilinmiyor olabilir; yanıt sadece yönerge + tweet ID bağlamına uyar.
    """
    if not _REQUESTS_OK:
        return False, "", "requests kütüphanesi bulunamadı"

    endpoint = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("TWEETER_AI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sen Twitter/X için kısa YANIT metinleri yazıyorsun. Kullanıcının YÖNERGESİNE göre "
                    "tek bir yayınlanabilir yanıt yaz. Orijinal gönderinin tam metnini bilmiyorsun; "
                    "yönergeye ve 'yanıt verilecek tweet ID' bağlamına uy. "
                    "Yönergede olmayan gerçek veya olay uydurma. "
                    "Yanıtta sadece yanıt metni olsun; açıklama, başlık veya tırnak kullanma. "
                    "280 karakteri geçme. Yönergedeki dilde yaz."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Yanıt verilecek tweet ID: {reply_to_tweet_id}\n\n"
                    f"Yönerge:\n{instruction.strip()}\n\n"
                    f"Toplam {total_variants} hesap için benzersiz yanıt üretilecek; "
                    f"bu {variant_no}. varyant. '@{account.username}' metne ekleme (yönergede yoksa). "
                    f"Stil ipucu: {AI_STYLE_HINTS[(variant_no - 1) % len(AI_STYLE_HINTS)]}. "
                    "Diğer varyantlardan belirgin şekilde farklı ol."
                ),
            },
        ],
        "max_completion_tokens": 180,
    }

    try:
        resp = _requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
        if resp.status_code >= 400:
            return False, "", f"AI HTTP {resp.status_code}: {resp.text[:160]}"
        data = resp.json()
        content = (
            data.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        composed = _clean_ai_tweet(content)
        if not composed:
            return False, "", "AI boş metin döndürdü"
        if len(composed) > 280:
            return False, "", f"AI metni 280 karakteri aştı ({len(composed)})"
        return True, composed, None
    except Exception as exc:
        return False, "", str(exc)[:180]


def build_ai_reply_composes(
    accounts: list[Account],
    tweet_id: str,
    instruction: str,
    *,
    base_url: str = DEFAULT_AI_BASE_URL,
    model: str = DEFAULT_AI_MODEL,
    timeout: int = DEFAULT_AI_TIMEOUT,
    workers: int = DEFAULT_WORKERS,
) -> dict[str, tuple[bool, str, str | None]]:
    """Yönergeye göre her hesap için hedef tweet'e özgün yanıt metni üretir."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}AI — yönergeden yanıt metni üretiliyor{Colors.RESET}")
    print(f"  {Colors.GRAY}Model   : {model}{Colors.RESET}")
    print(f"  {Colors.GRAY}Endpoint: {base_url.rstrip('/')}/chat/completions{Colors.RESET}")
    print(f"  {Colors.GRAY}Tweet ID: {tweet_id}{Colors.RESET}")
    print(f"  {Colors.GRAY}Hesap   : {len(accounts)}{Colors.RESET}")
    print(f"  {Colors.GRAY}Yönerge : \"{instruction[:100]}{'...' if len(instruction) > 100 else ''}\"{Colors.RESET}\n")

    results: dict[str, tuple[bool, str, str | None]] = {}
    seen: list[str] = []
    lock = threading.Lock()

    def task(item: tuple[int, Account]):
        idx, acc = item
        ok = False
        text = ""
        err = None

        for attempt in range(3):
            ok, text, err = compose_reply_with_ai(
                instruction,
                tweet_id,
                acc,
                idx + 1 + (attempt * len(accounts)),
                len(accounts),
                base_url=base_url,
                model=model,
                timeout=timeout,
            )
            with lock:
                duplicate = ok and _too_similar_to_seen(text, seen)
                if ok and not duplicate:
                    seen.append(_similarity_key(text))
                    results[acc.username] = (ok, text, err)
                    break
                if not ok:
                    results[acc.username] = (ok, text, err)
                    break
                if attempt == 2:
                    ok = False
                    err = "AI yeterince farklı yanıt üretemedi"
                    results[acc.username] = (ok, text, err)
                    break

        if ok:
            preview = text[:90] + ("..." if len(text) > 90 else "")
            tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → {Colors.GREEN}✓{Colors.RESET} {preview}")
        else:
            tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → {Colors.RED}✗ {err}{Colors.RESET}")

    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        list(pool.map(task, enumerate(accounts)))

    return results


def post_all_from_instruction(
    accounts: list[Account],
    instruction: str,
    *,
    dry_run: bool = False,
    delay_range: tuple = (0, 0),
    reply_to: str | None = None,
    images: list[str] | None = None,
    workers: int = DEFAULT_WORKERS,
    max_retry: int = DEFAULT_MAX_RETRY,
    ai_base_url: str = DEFAULT_AI_BASE_URL,
    ai_model: str = DEFAULT_AI_MODEL,
    ai_timeout: int = DEFAULT_AI_TIMEOUT,
):
    """
    Yönergeye göre her hesap için AI ile metin üretir, ardından (dry_run değilse) gönderir.
    """
    variants = build_ai_composes(
        accounts,
        instruction,
        base_url=ai_base_url,
        model=ai_model,
        timeout=ai_timeout,
        workers=workers,
    )
    ok_n = sum(1 for v in variants.values() if v[0])
    print(f"\n{Colors.BOLD}{'─' * 50}{Colors.RESET}")
    print(f"  {Colors.GREEN}AI hazır: {ok_n}{Colors.RESET}  "
          f"{Colors.RED}AI hata: {len(accounts) - ok_n}{Colors.RESET}")

    if dry_run:
        print(f"\n{Colors.YELLOW}[DRY-RUN] Tweet gönderilmedi.{Colors.RESET}")
        return

    success_count = 0
    fail_count    = 0
    lock          = threading.Lock()

    def task(acc: Account):
        ok, text, err = variants.get(acc.username, (False, "", "varyant yok"))
        if not ok:
            result = {"success": False, "stdout": "", "stderr": err or "AI üretimi yok"}
            tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → "
                   f"{Colors.RED}✗ Gönderim atlandı{Colors.RESET}")
            log_result(acc, "post_ai_instruction", instruction, result)
            return False

        if delay_range[1] > 0:
            time.sleep(random.uniform(*delay_range))
        result = post_single(acc, text, reply_to=reply_to, images=images, max_retry=max_retry)
        return result["success"]

    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        futures = {pool.submit(task, acc): acc for acc in accounts}
        for future in as_completed(futures):
            try:
                ok = future.result()
            except Exception as exc:
                ok = False
                tprint(f"  {Colors.RED}✗ Thread hatası: {exc}{Colors.RESET}")
            with lock:
                if ok:
                    success_count += 1
                else:
                    fail_count += 1

    print_action_summary(success_count, fail_count, len(accounts))


def reply_all_from_instruction(
    accounts: list[Account],
    tweet_id: str,
    instruction: str,
    *,
    dry_run: bool = False,
    delay_range: tuple = (0, 0),
    workers: int = DEFAULT_WORKERS,
    max_retry: int = DEFAULT_MAX_RETRY,
    ai_base_url: str = DEFAULT_AI_BASE_URL,
    ai_model: str = DEFAULT_AI_MODEL,
    ai_timeout: int = DEFAULT_AI_TIMEOUT,
):
    """Tweet ID'sine, yönergeye göre AI ile üretilmiş özgün yanıtlar gönderir."""
    variants = build_ai_reply_composes(
        accounts,
        tweet_id,
        instruction,
        base_url=ai_base_url,
        model=ai_model,
        timeout=ai_timeout,
        workers=workers,
    )
    ok_n = sum(1 for v in variants.values() if v[0])
    print(f"\n{Colors.BOLD}{'─' * 50}{Colors.RESET}")
    print(f"  {Colors.GREEN}AI hazır: {ok_n}{Colors.RESET}  "
          f"{Colors.RED}AI hata: {len(accounts) - ok_n}{Colors.RESET}")

    if dry_run:
        print(f"\n{Colors.YELLOW}[DRY-RUN] Yanıt gönderilmedi.{Colors.RESET}")
        return

    success_count = 0
    fail_count    = 0
    lock          = threading.Lock()

    def task(acc: Account):
        ok_ai, reply_text, err = variants.get(acc.username, (False, "", "varyant yok"))
        if not ok_ai:
            result = {"success": False, "stdout": "", "stderr": err or "AI üretimi yok"}
            tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → "
                   f"{Colors.RED}✗ Gönderim atlandı{Colors.RESET}")
            log_result(acc, "reply_ai_instruction", tweet_id, result)
            return False
        if delay_range[1] > 0:
            time.sleep(random.uniform(*delay_range))
        result, _ = run_with_retry(
            acc, ["reply", tweet_id, reply_text, "--json"], timeout=30, max_retry=max_retry
        )
        ok, msg = parse_twitter_response(result)
        result["success"] = ok
        line_ok   = f"{Colors.GREEN}✓ Başarılı{Colors.RESET}"
        line_fail = f"{Colors.RED}✗ {msg or 'Hata'}{Colors.RESET}"
        tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → {line_ok if ok else line_fail}")
        log_result(acc, "reply_ai_instruction", f"{tweet_id} → {reply_text[:120]}", result)
        return ok

    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        futures = {pool.submit(task, acc): acc for acc in accounts}
        for future in as_completed(futures):
            try:
                ok = future.result()
            except Exception as exc:
                ok = False
                tprint(f"  {Colors.RED}✗ Thread hatası: {exc}{Colors.RESET}")
            with lock:
                if ok:
                    success_count += 1
                else:
                    fail_count += 1

    print_action_summary(success_count, fail_count, len(accounts))

# ─── Banner ───
def _proxy_display_str(proxy: str) -> str:
    """Proxy URL'inden parola gizleyerek gösterilecek kısa metni döndürür."""
    if "@" in proxy:
        return proxy.split("@")[-1]
    return proxy.replace("http://", "").replace("https://", "").replace("socks5://", "")


def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ████████╗██╗    ██╗███████╗███████╗████████╗███████╗    ║
║     ╚══██╔══╝██║    ██║██╔════╝██╔════╝╚══██╔══╝██╔════╝    ║
║        ██║   ██║ █╗ ██║█████╗  █████╗     ██║   █████╗      ║
║        ██║   ██║███╗██║██╔══╝  ██╔══╝     ██║   ██╔══╝      ║
║        ██║   ╚███╔███╔╝███████╗███████╗   ██║   ███████╗    ║
║        ╚═╝    ╚══╝╚══╝ ╚══════╝╚══════╝   ╚═╝   ╚══════╝    ║
║                                                              ║
║          Çoklu Twitter Hesap Yönetim Sistemi                ║
║          twitter-cli tabanlı  |  Multi-threaded             ║
╚══════════════════════════════════════════════════════════════╝
{Colors.RESET}"""
    print(banner)
    if _PROXY_POOL and proxy_enabled():
        if len(_PROXY_POOL) == 1:
            host = _proxy_display_str(_PROXY_POOL[0])
            print(f"  {Colors.GREEN}🔒 Rotating Proxy aktif:{Colors.RESET} {Colors.GRAY}{host}{Colors.RESET} "
                  f"{Colors.CYAN}(her istek yeni IP){Colors.RESET}\n")
        else:
            print(f"  {Colors.GREEN}🔒 Proxy Havuzu aktif:{Colors.RESET} "
                  f"{Colors.CYAN}{len(_PROXY_POOL)} proxy{Colors.RESET} "
                  f"{Colors.GRAY}(round-robin rotasyon){Colors.RESET}")
            for i, p in enumerate(_PROXY_POOL[:3], 1):
                print(f"  {Colors.GRAY}  {i}. {_proxy_display_str(p)}{Colors.RESET}")
            if len(_PROXY_POOL) > 3:
                print(f"  {Colors.GRAY}  ... +{len(_PROXY_POOL) - 3} daha{Colors.RESET}")
            print()
    elif _PROXY_POOL:
        print(f"  {Colors.GRAY}Proxy havuzu kayıtlı ama kapalı ({len(_PROXY_POOL)} proxy){Colors.RESET}\n")
    else:
        print(f"  {Colors.YELLOW}⚠  Proxy yok — proxy.txt'e DataImpulse veya başka proxy ekle{Colors.RESET}\n")

# ─── Hesap Listesini Göster ───
def show_accounts(accounts: list[Account]):
    print(f"\n{Colors.BOLD}{Colors.BLUE}📋 Yüklü Hesaplar ({len(accounts)} adet):{Colors.RESET}")
    print(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")
    for i, acc in enumerate(accounts, 1):
        token_preview = acc.auth_token[:8] + "..."
        ct0_preview   = acc.ct0[:8] + "..."
        print(f"  {Colors.CYAN}{i:2d}.{Colors.RESET} {Colors.BOLD}@{acc.username:<20}{Colors.RESET} "
              f"{Colors.GRAY}token:{token_preview}  ct0:{ct0_preview}{Colors.RESET}")
    print(f"{Colors.GRAY}{'─' * 60}{Colors.RESET}")


def fix_usernames(accounts: list[Account], workers: int = DEFAULT_WORKERS, dry_run: bool = False):
    """
    Her hesabın credentials'ını Twitter API üzerinden doğrular ve
    accounts.txt'deki kullanıcı adını gerçek hesap adıyla günceller.
    """
    if not _TWCLIENT_OK:
        print(f"{Colors.RED}✗ twitter_cli bulunamadı{Colors.RESET}")
        return

    print(f"\n{Colors.BOLD}{Colors.CYAN}{'━'*54}{Colors.RESET}")
    print(f"{Colors.BOLD}🔍 Kullanıcı Adı Doğrulama & Düzeltme{Colors.RESET}")
    print(f"  Hesaplar : {Colors.CYAN}{len(accounts)}{Colors.RESET}")
    print(f"  Mod      : {Colors.YELLOW}{'DRY-RUN (yazma yok)' if dry_run else 'Gerçek (accounts.txt güncellenir)'}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'━'*54}{Colors.RESET}\n")

    results: list[tuple[Account, str | None, str | None]] = []  # (acc, real_username, error)
    lock = threading.Lock()

    def verify_one(acc: Account):
        try:
            client = _TwitterClient(acc.auth_token, acc.ct0)
            profile = client.fetch_me()
            real = profile.screen_name.lstrip("@")
            with lock:
                results.append((acc, real, None))
            match = real.lower() == acc.username.lower()
            flag = f"{Colors.GREEN}✓ eşleşiyor{Colors.RESET}" if match else \
                   f"{Colors.RED}✗ FARKLI → gerçek: @{real}{Colors.RESET}"
            tprint(f"  {Colors.CYAN}@{acc.username:<22}{Colors.RESET} {flag}")
        except Exception as exc:
            err = str(exc)[:60]
            with lock:
                results.append((acc, None, err))
            tprint(f"  {Colors.CYAN}@{acc.username:<22}{Colors.RESET} {Colors.YELLOW}⚠ {err}{Colors.RESET}")

    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        list(pool.map(verify_one, accounts))

    # Değişiklik gerektiren hesapları filtrele
    updates = [(acc, real) for acc, real, err in results
               if real and real.lower() != acc.username.lower()]
    no_change = sum(1 for _, real, err in results if real and real.lower() == _.username.lower() if False or True)
    errors = sum(1 for _, real, err in results if err)

    correct = len(accounts) - len(updates) - errors

    print(f"\n{Colors.BOLD}{'─'*54}{Colors.RESET}")
    print(f"  {Colors.GREEN}✓ Doğru    : {correct}{Colors.RESET}")
    print(f"  {Colors.RED}✗ Yanlış   : {len(updates)}{Colors.RESET}")
    print(f"  {Colors.YELLOW}⚠ Hata     : {errors}{Colors.RESET}")

    if not updates:
        print(f"\n{Colors.GREEN}✓ Tüm kullanıcı adları doğru, güncelleme gerekmez.{Colors.RESET}")
        return

    if dry_run:
        print(f"\n{Colors.YELLOW}[DRY-RUN] Aşağıdaki değişiklikler yapılacaktı:{Colors.RESET}")
        for acc, real in updates:
            print(f"  @{acc.username:<22} → @{real}")
        return

    # accounts.txt'yi güncelle
    filepath = ACCOUNTS_FILE
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    update_map = {acc.username.lower(): real for acc, real in updates}
    new_lines = []
    changed = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        clean = stripped.lstrip("@")
        parts = clean.split(":")
        if len(parts) == 5:
            old_name = parts[0].lower()
            if old_name in update_map:
                parts[0] = update_map[old_name]
                new_lines.append(":".join(parts) + "\n")
                changed += 1
                continue
        new_lines.append(line)

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"\n{Colors.GREEN}✓ {changed} hesabın kullanıcı adı accounts.txt'de güncellendi.{Colors.RESET}")
    for acc, real in updates:
        print(f"  {Colors.GRAY}@{acc.username}{Colors.RESET} → {Colors.GREEN}@{real}{Colors.RESET}")

# ─── Özet Yazdır ───
def print_action_summary(success_count: int, fail_count: int, total: int):
    print(f"\n{Colors.BOLD}{'─' * 50}{Colors.RESET}")
    print(f"  {Colors.GREEN}✓ Başarılı: {success_count}{Colors.RESET}  "
          f"{Colors.RED}✗ Başarısız: {fail_count}{Colors.RESET}  "
          f"{Colors.GRAY}Toplam: {total}{Colors.RESET}")

# ─── Generic Paralel İşlem Motoru ───
def run_bulk_action(
    accounts: list[Account],
    action_fn,           # callable(account) -> (ok: bool, msg: str, result: dict)
    label: str,
    action_name: str,
    target: str,
    workers: int = DEFAULT_WORKERS,
):
    """
    Verilen hesaplar üzerinde action_fn'i paralel olarak çalıştırır.
    action_fn: account alır, (ok, msg, raw_result) tuple döner.
    """
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{label}{Colors.RESET}")
    print(f"  {Colors.GRAY}Hedef    : {target}{Colors.RESET}")
    print(f"  {Colors.GRAY}Hesaplar : {len(accounts)}{Colors.RESET}")
    print(f"  {Colors.GRAY}Threads  : {min(workers, len(accounts))}{Colors.RESET}\n")

    success_count = 0
    fail_count    = 0
    lock          = threading.Lock()

    def task(acc: Account):
        ok, msg, raw = action_fn(acc)
        line_ok   = f"{Colors.GREEN}✓ Başarılı{Colors.RESET}"
        line_fail = f"{Colors.RED}✗ {msg}{Colors.RESET}"
        tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → {line_ok if ok else line_fail}")
        log_result(acc, action_name, target, raw)
        return ok

    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        futures = {pool.submit(task, acc): acc for acc in accounts}
        for future in as_completed(futures):
            try:
                ok = future.result()
            except Exception as exc:
                ok = False
                tprint(f"  {Colors.RED}✗ Thread hatası: {exc}{Colors.RESET}")
            with lock:
                if ok:
                    success_count += 1
                else:
                    fail_count += 1

    print_action_summary(success_count, fail_count, len(accounts))

# ─── Hesap Durumu Kategorisi ───
def _classify_error(err: str | None) -> tuple[str, str]:
    """
    Hata mesajını analiz eder, (etiket, renk) döndürür.
    """
    if not err:
        return "AKTİF", Colors.GREEN
    e = err.lower()
    if "suspended" in e or "deactivated" in e or "offboarded" in e:
        return "ASKIDA/KİLİTLİ", Colors.RED
    if "already favorited" in e or "already retweeted" in e:
        return "DUPLICATE_UID", Colors.YELLOW
    if "timeout" in e or "zaman" in e:
        return "TIMEOUT", Colors.YELLOW
    if "unauthorized" in e or "authorization" in e or "forbidden" in e or "invalid" in e:
        return "TOKEN_HATALI", Colors.RED
    if "read-only" in e or "read only" in e or "write" in e:
        return "SALT_OKUMA", Colors.YELLOW
    return "BILINMEYEN", Colors.GRAY


# ─── Hesap Durumlarını Kontrol Et ───
def check_accounts(
    accounts: list[Account],
    workers: int = DEFAULT_WORKERS,
    deep: bool = False,
    deep_tweet_id: str = "20",   # Jack'in ilk tweeti — herkese açık, like testi için güvenli
) -> list[dict]:
    """
    Hesap durumlarını kontrol eder.

    Yüzeysel mod (varsayılan): `whoami` ile token geçerliliğini kontrol eder.
      → Okuma işlemleri çalışır ama YAZMA kısıtlamasını yakalamaz.

    Derin mod (--deep): `whoami` + gerçek like testi yapar.
      → "Aktif görünüp beğeni/RT atamayan" hesapları tespit eder.
      → Test tweet'ini like edip hemen unlike yapar (iz bırakmaz).
    """
    mode_str = "DERİN (yazma testi dahil)" if deep else "YÜZEYSEL (sadece token)"
    print(f"\n{Colors.BOLD}{Colors.BLUE}🔍 Hesap Durumları Kontrol Ediliyor{Colors.RESET}")
    print(f"  {Colors.GRAY}Mod     : {mode_str}{Colors.RESET}")
    print(f"  {Colors.GRAY}Threads : {min(workers, len(accounts))}{Colors.RESET}\n")

    results: list[dict] = []
    res_lock = threading.Lock()

    def check_one(acc: Account):
        # ── Adım 1: whoami (token geçerliliği) ──
        result = run_twitter_command(acc, ["whoami", "--json"], timeout=DEFAULT_TIMEOUT)
        ok, err = parse_twitter_response(result)

        uid = None
        screen_name = None
        if result["stdout"]:
            try:
                data = json.loads(result["stdout"])
                inner = data.get("data", data)
                uid = str(inner.get("id") or inner.get("user_id") or "")
                screen_name = inner.get("screen_name") or inner.get("username") or ""
                # whoami yanıtında doğrudan suspended bayrağı var mı?
                if inner.get("suspended") or inner.get("withheld"):
                    ok  = False
                    err = "suspended (whoami flag)"
            except (json.JSONDecodeError, AttributeError):
                pass

        write_ok = None   # None = test yapılmadı

        # ── Adım 2: Derin mod — like testi ──
        if ok and deep:
            like_r, _ = run_with_retry(acc, ["like", deep_tweet_id, "--json"],
                                        timeout=DEFAULT_TIMEOUT, max_retry=0)
            like_ok, like_err = parse_twitter_response(like_r)

            # "already favorited" → like çalışıyor demektir (daha önce beğenmiş)
            if like_ok or (like_err and "already favorited" in (like_err or "").lower()):
                write_ok = True
                # Unlike — iz bırakmamak için geri al (hata olursa önemli değil)
                run_twitter_command(acc, ["unlike", deep_tweet_id, "--json"],
                                    timeout=DEFAULT_TIMEOUT)
            else:
                write_ok = False
                if not err:
                    err = like_err  # yazma hatasını ana hata yap

        # ── Etiket belirle ──
        if not ok:
            label, color = _classify_error(err)
        elif write_ok is False:
            label, color = _classify_error(err)
            if label == "AKTİF":
                label, color = "YAZMA_KISITLI", Colors.RED
        else:
            label, color = "AKTİF", Colors.GREEN
            if write_ok is True:
                label = "AKTİF+YAZMA✓"

        with res_lock:
            results.append({"account": acc, "uid": uid, "screen_name": screen_name,
                             "label": label, "err": err, "ok": ok, "write_ok": write_ok})

        uid_str  = f" {Colors.GRAY}uid:{uid}{Colors.RESET}" if uid else ""
        sn_str   = (f" {Colors.GRAY}→ @{screen_name}{Colors.RESET}"
                    if screen_name and screen_name.lower() != acc.username.lower() else "")
        err_str  = f" {Colors.GRAY}{(err or '')[:90]}{Colors.RESET}" if not ok or write_ok is False else ""
        tprint(f"  {Colors.CYAN}@{acc.username:<22}{Colors.RESET} "
               f"{color}[{label}]{Colors.RESET}{uid_str}{sn_str}{err_str}")

    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        list(pool.map(check_one, accounts))

    # ── Duplicate uid uyarısı ──
    uid_map: dict[str, list[str]] = {}
    for r in results:
        if r["uid"]:
            uid_map.setdefault(r["uid"], []).append(r["account"].username)
    dups = {uid: names for uid, names in uid_map.items() if len(names) > 1}
    if dups:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}⚠  Aynı Twitter UID'ini paylaşan hesaplar (token karışıklığı):{Colors.RESET}")
        for uid, names in dups.items():
            print(f"  uid:{uid} → {', '.join('@'+n for n in names)}")
        print(f"  {Colors.GRAY}accounts.txt'de bu kullanıcılar için auth_token/ct0 değerlerini kontrol et.{Colors.RESET}")

    # Özet
    counts: dict[str, int] = {}
    for r in results:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    print(f"\n{Colors.BOLD}{'─' * 55}{Colors.RESET}")
    order = ["AKTİF", "AKTİF+YAZMA✓", "YAZMA_KISITLI", "ASKIDA/KİLİTLİ",
             "TOKEN_HATALI", "SALT_OKUMA", "DUPLICATE_UID", "TIMEOUT", "BILINMEYEN"]
    color_map = {
        "AKTİF":          Colors.GREEN,
        "AKTİF+YAZMA✓":   Colors.GREEN,
        "YAZMA_KISITLI":  Colors.RED,
        "ASKIDA/KİLİTLİ": Colors.RED,
        "TOKEN_HATALI":   Colors.RED,
        "SALT_OKUMA":     Colors.YELLOW,
        "DUPLICATE_UID":  Colors.YELLOW,
        "TIMEOUT":        Colors.YELLOW,
        "BILINMEYEN":     Colors.GRAY,
    }
    if deep:
        print(f"  {Colors.GRAY}⚡ Derin mod: YAZMA_KISITLI = token OK ama like/RT atamıyor{Colors.RESET}")
    for lbl in order:
        if lbl in counts:
            print(f"  {color_map[lbl]}{lbl:<14}{Colors.RESET}: {counts[lbl]}")

    return results


# ─── Askıya Alınmış Hesapları Temizle ───
def purge_accounts(
    accounts: list[Account],
    filepath: Path = ACCOUNTS_FILE,
    workers: int = DEFAULT_WORKERS,
    dry_run: bool = False,
    deep: bool = False,
    deep_tweet_id: str = "20",
):
    """
    check ile tüm hesapları tarar; suspended/token_hatalı/yazma_kısıtlı olanları
    accounts.txt'den kaldırır. dry_run=True ile sadece listeler.
    """
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}🧹 Ölü Hesap Temizleyici{Colors.RESET}")
    if dry_run:
        print(f"  {Colors.YELLOW}[DRY-RUN] Gerçek silme yapılmayacak{Colors.RESET}")

    results = check_accounts(accounts, workers=workers, deep=deep, deep_tweet_id=deep_tweet_id)

    dead_labels = {"ASKIDA/KİLİTLİ", "TOKEN_HATALI", "YAZMA_KISITLI"}
    dead = [r for r in results if r["label"] in dead_labels]
    alive = [r for r in results if r["label"] not in dead_labels]

    if not dead:
        print(f"\n{Colors.GREEN}✓ Temizlenecek hesap yok, tüm hesaplar kullanılabilir.{Colors.RESET}")
        return

    print(f"\n{Colors.BOLD}{Colors.RED}Silinecek hesaplar ({len(dead)} adet):{Colors.RESET}")
    for r in dead:
        print(f"  {Colors.RED}✗ @{r['account'].username:<22}{Colors.RESET} [{r['label']}]")

    if dry_run:
        print(f"\n{Colors.YELLOW}[DRY-RUN] Yukarıdaki {len(dead)} hesap silinecekti.{Colors.RESET}")
        return

    try:
        confirm = input(f"\n{Colors.CYAN}{len(dead)} hesap accounts.txt'den silinsin mi? (e/h) ▸ {Colors.RESET}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{Colors.YELLOW}İptal.{Colors.RESET}")
        return

    if confirm not in ("e", "evet", "y", "yes"):
        print(f"{Colors.YELLOW}İptal edildi.{Colors.RESET}")
        return

    # Canlı hesapları geri yaz
    alive_usernames = {r["account"].username.lower() for r in alive}
    kept_lines = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                kept_lines.append(line)
                continue
            uname = stripped.lstrip("@").split(":")[0].lower()
            if uname in alive_usernames:
                kept_lines.append(line)

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(kept_lines)

    print(f"\n{Colors.GREEN}✓ {len(dead)} hesap silindi. {len(alive)} hesap kaldı.{Colors.RESET}")

# ─── Tek Hesaptan Tweet At ───
def post_single(
    account: Account,
    text: str,
    reply_to: str | None = None,
    images: list[str] | None = None,
    max_retry: int = DEFAULT_MAX_RETRY,
) -> dict:
    """Tek bir hesaptan tweet atar (retry destekli)."""
    args = ["post", text]
    if reply_to:
        args.extend(["--reply-to", reply_to])
    if images:
        for img in images[:4]:
            args.extend(["--image", img])
    args.append("--json")

    result, attempts = run_with_retry(account, args, timeout=30, max_retry=max_retry)

    actual_success = False
    tweet_id  = None
    tweet_url = None
    error_msg = None

    if result["stdout"]:
        try:
            json_data = json.loads(result["stdout"])
            if json_data.get("ok"):
                actual_success = True
                inner     = json_data.get("data", {})
                tweet_id  = inner.get("id")
                tweet_url = inner.get("url")
            else:
                err_info  = json_data.get("error", {})
                error_msg = err_info.get("message", "Bilinmeyen API hatası")
        except json.JSONDecodeError:
            pass

    retry_info = f" (deneme: {attempts + 1})" if attempts > 0 else ""

    if actual_success:
        msg = f"{Colors.GREEN}✓ Tweet gönderildi{retry_info}{Colors.RESET}"
        if tweet_id:
            msg += f"\n    {Colors.GRAY}ID : {tweet_id}{Colors.RESET}"
        if tweet_url:
            msg += f"\n    {Colors.GRAY}URL: {tweet_url}{Colors.RESET}"
    else:
        if not error_msg:
            error_msg = result["stderr"][:100] if result["stderr"] else result["stdout"][:100]
        msg = f"{Colors.RED}✗ {error_msg}{retry_info}{Colors.RESET}"

    tprint(f"  {Colors.CYAN}@{account.username:<20}{Colors.RESET} → {msg}")
    result["success"] = actual_success
    log_result(account, "post", text, result)
    return result

# ─── Tüm / Seçili Hesaplardan Tweet At ───
def post_all(
    accounts: list[Account],
    text: str,
    delay_range: tuple = (0, 0),
    reply_to: str | None = None,
    images: list[str] | None = None,
    workers: int = DEFAULT_WORKERS,
    max_retry: int = DEFAULT_MAX_RETRY,
    ai_rewrite: bool = False,
    ai_dry_run: bool = False,
    ai_base_url: str = DEFAULT_AI_BASE_URL,
    ai_model: str = DEFAULT_AI_MODEL,
    ai_timeout: int = DEFAULT_AI_TIMEOUT,
):
    """Hesaplardan paralel olarak tweet atar."""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}🚀 Toplu Tweet Gönderimi Başlıyor{Colors.RESET}")
    print(f"  {Colors.GRAY}Tweet  : \"{text[:80]}{'...' if len(text) > 80 else ''}\"{Colors.RESET}")
    print(f"  {Colors.GRAY}Hesap  : {len(accounts)}{Colors.RESET}")
    print(f"  {Colors.GRAY}Threads: {min(workers, len(accounts))}{Colors.RESET}\n")

    ai_variants: dict[str, tuple[bool, str, str | None]] = {}
    if ai_rewrite or ai_dry_run:
        ai_variants = build_ai_rewrites(
            accounts,
            text,
            base_url=ai_base_url,
            model=ai_model,
            timeout=ai_timeout,
            workers=workers,
        )

        ok_count = sum(1 for ok, _, _ in ai_variants.values() if ok)
        fail_count = len(accounts) - ok_count
        print(f"\n{Colors.BOLD}{'─' * 50}{Colors.RESET}")
        print(f"  {Colors.GREEN}AI hazır: {ok_count}{Colors.RESET}  "
              f"{Colors.RED}AI hata: {fail_count}{Colors.RESET}")

        if ai_dry_run:
            print(f"\n{Colors.YELLOW}[AI DRY-RUN] Tweet gönderilmedi.{Colors.RESET}")
            return

    success_count = 0
    fail_count    = 0
    lock          = threading.Lock()

    def task(acc: Account):
        post_text = text
        if ai_rewrite:
            ok, rewritten, err = ai_variants.get(acc.username, (False, text, "AI varyantı yok"))
            if not ok:
                result = {"success": False, "stdout": "", "stderr": err or "AI rewrite hatası"}
                tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → "
                       f"{Colors.RED}✗ AI varyantı yok, gönderim atlandı{Colors.RESET}")
                log_result(acc, "post_ai_rewrite", text, result)
                return False
            post_text = rewritten

        # Her thread kendi random gecikmesini uygular (opsiyonel)
        if delay_range[1] > 0:
            time.sleep(random.uniform(*delay_range))
        result = post_single(acc, post_text, reply_to=reply_to, images=images, max_retry=max_retry)
        return result["success"]

    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        futures = {pool.submit(task, acc): acc for acc in accounts}
        for future in as_completed(futures):
            try:
                ok = future.result()
            except Exception as exc:
                ok = False
                tprint(f"  {Colors.RED}✗ Thread hatası: {exc}{Colors.RESET}")
            with lock:
                if ok:
                    success_count += 1
                else:
                    fail_count += 1

    print_action_summary(success_count, fail_count, len(accounts))


def post_selected(
    accounts: list[Account],
    indices: list[int],
    text: str,
    delay_range: tuple = (0, 0),
    reply_to: str | None = None,
    images: list[str] | None = None,
    workers: int = DEFAULT_WORKERS,
    max_retry: int = DEFAULT_MAX_RETRY,
    ai_rewrite: bool = False,
    ai_dry_run: bool = False,
    ai_base_url: str = DEFAULT_AI_BASE_URL,
    ai_model: str = DEFAULT_AI_MODEL,
    ai_timeout: int = DEFAULT_AI_TIMEOUT,
):
    selected = []
    for idx in indices:
        if 1 <= idx <= len(accounts):
            selected.append(accounts[idx - 1])
        else:
            print(f"{Colors.YELLOW}⚠ Geçersiz hesap numarası: {idx}{Colors.RESET}")
    if not selected:
        print(f"{Colors.RED}✗ Geçerli hesap seçilmedi.{Colors.RESET}")
        return
    post_all(selected, text, delay_range=delay_range, reply_to=reply_to,
             images=images, workers=workers, max_retry=max_retry,
             ai_rewrite=ai_rewrite, ai_dry_run=ai_dry_run,
             ai_base_url=ai_base_url, ai_model=ai_model,
             ai_timeout=ai_timeout)

# ─── Like ───
def like_all(accounts: list[Account], tweet_id: str, workers: int = DEFAULT_WORKERS):
    def action(acc):
        result, _ = run_with_retry(acc, ["like", tweet_id, "--json"])
        ok, err   = parse_twitter_response(result)
        result["success"] = ok
        return ok, err or "Hata", result

    run_bulk_action(accounts, action, "❤️  Toplu Beğeni Başlıyor",
                    "like", tweet_id, workers=workers)

# ─── Retweet ───
def retweet_all(accounts: list[Account], tweet_id: str, workers: int = DEFAULT_WORKERS):
    def action(acc):
        result, _ = run_with_retry(acc, ["retweet", tweet_id, "--json"])
        ok, err   = parse_twitter_response(result)
        result["success"] = ok
        return ok, err or "Hata", result

    run_bulk_action(accounts, action, "🔄 Toplu Retweet Başlıyor",
                    "retweet", tweet_id, workers=workers)

# ─── Follow ───
def follow_all(accounts: list[Account], target_user: str, workers: int = DEFAULT_WORKERS):
    def action(acc):
        result, _ = run_with_retry(acc, ["follow", target_user, "--json"])
        ok, err   = parse_twitter_response(result)
        result["success"] = ok
        return ok, err or "Hata", result

    run_bulk_action(accounts, action, "👤 Toplu Takip Başlıyor",
                    "follow", f"@{target_user}", workers=workers)

# ─── Reply ───
def reply_all(
    accounts: list[Account],
    tweet_id: str,
    text: str,
    workers: int = DEFAULT_WORKERS,
    max_retry: int = DEFAULT_MAX_RETRY,
    delay_range: tuple = (0, 0),
    ai_rewrite: bool = False,
    ai_dry_run: bool = False,
    ai_base_url: str = DEFAULT_AI_BASE_URL,
    ai_model: str = DEFAULT_AI_MODEL,
    ai_timeout: int = DEFAULT_AI_TIMEOUT,
):
    """Toplu yanıt; --ai-rewrite ile aynı metnin hesap başına AI varyantı."""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}💬 Toplu Yanıt Başlıyor{Colors.RESET}")
    print(f"  {Colors.GRAY}Tweet ID: {tweet_id}{Colors.RESET}")
    print(f"  {Colors.GRAY}Metin   : \"{text[:70]}{'...' if len(text) > 70 else ''}\"{Colors.RESET}")
    print(f"  {Colors.GRAY}Hesap   : {len(accounts)}{Colors.RESET}")
    print(f"  {Colors.GRAY}Threads : {min(workers, len(accounts))}{Colors.RESET}\n")

    ai_variants: dict[str, tuple[bool, str, str | None]] = {}
    if ai_rewrite or ai_dry_run:
        ai_variants = build_ai_rewrites(
            accounts,
            text,
            base_url=ai_base_url,
            model=ai_model,
            timeout=ai_timeout,
            workers=workers,
        )
        ok_count = sum(1 for ok, _, _ in ai_variants.values() if ok)
        print(f"\n{Colors.BOLD}{'─' * 50}{Colors.RESET}")
        print(f"  {Colors.GREEN}AI hazır: {ok_count}{Colors.RESET}  "
              f"{Colors.RED}AI hata: {len(accounts) - ok_count}{Colors.RESET}")
        if ai_dry_run:
            print(f"\n{Colors.YELLOW}[AI DRY-RUN] Yanıt gönderilmedi.{Colors.RESET}")
            return

    success_count = 0
    fail_count    = 0
    lock          = threading.Lock()

    def task(acc: Account):
        reply_text = text
        if ai_rewrite:
            ok_r, rewritten, err = ai_variants.get(acc.username, (False, text, "AI yok"))
            if not ok_r:
                result = {"success": False, "stdout": "", "stderr": err or "AI rewrite hatası"}
                tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → "
                       f"{Colors.RED}✗ AI varyantı yok{Colors.RESET}")
                log_result(acc, "reply_ai_rewrite", tweet_id, result)
                return False
            reply_text = rewritten

        if delay_range[1] > 0:
            time.sleep(random.uniform(*delay_range))
        result, _ = run_with_retry(
            acc, ["reply", tweet_id, reply_text, "--json"], timeout=30, max_retry=max_retry
        )
        ok, msg = parse_twitter_response(result)
        result["success"] = ok
        line_ok   = f"{Colors.GREEN}✓ Başarılı{Colors.RESET}"
        line_fail = f"{Colors.RED}✗ {msg or 'Hata'}{Colors.RESET}"
        tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → {line_ok if ok else line_fail}")
        log_result(acc, "reply", f"ID:{tweet_id} → {reply_text[:60]}", result)
        return ok

    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        futures = {pool.submit(task, acc): acc for acc in accounts}
        for future in as_completed(futures):
            try:
                ok = future.result()
            except Exception as exc:
                ok = False
                tprint(f"  {Colors.RED}✗ Thread hatası: {exc}{Colors.RESET}")
            with lock:
                if ok:
                    success_count += 1
                else:
                    fail_count += 1

    print_action_summary(success_count, fail_count, len(accounts))

# ─── Bookmark ───
def bookmark_all(accounts: list[Account], tweet_id: str, workers: int = DEFAULT_WORKERS):
    def action(acc):
        result, _ = run_with_retry(acc, ["bookmark", tweet_id, "--json"])
        ok, err   = parse_twitter_response(result)
        result["success"] = ok
        return ok, err or "Hata", result

    run_bulk_action(accounts, action, "🔖 Toplu Bookmark Başlıyor",
                    "bookmark", tweet_id, workers=workers)

# ─── View Gönderimi ───

# Twitter/X public Bearer token'ı
_TW_BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I7wlcjwHDEs"
    "=4puVIpHa8lHMLMeb28HKkD9rDOpUvOpBfoxy9TNJLRY4kl98k6"
)

# TweetDetail GraphQL query ID
_TWEET_DETAIL_QID = "VWFGPVAGkZMGRKGe3GFFnA"

_TW_FEATURES = json.dumps({
    "rweb_lists_timeline_redesign_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
}, separators=(",", ":"))

# User-Agent havuzu — her istekte rastgele seçilir
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]


def _send_view_direct(account: Account, tweet_id: str) -> dict:
    """
    `twitter tweet TWEET_ID --json` komutuyla TweetDetail çağrısı yaparak
    view kaydeder. Bu yöntem:
      • like/RT ile aynı auth mekanizmasını kullanır (zaten çalışıyor)
      • run_twitter_command üzerinden rotating proxy geçer
      • Ek kütüphane gerektirmez
    """
    result = run_twitter_command(account, ["tweet", tweet_id, "--json"],
                                 timeout=DEFAULT_TIMEOUT)
    if result["returncode"] == 0:
        return {"success": True, "stdout": "view ok", "stderr": ""}

    stderr = result["stderr"]
    stdout = result["stdout"]

    # JSON hata mesajını çıkar
    for raw in (stdout, stderr):
        if raw:
            try:
                data = json.loads(raw)
                msg = (data.get("error", {}).get("message")
                       or data.get("errors", [{}])[0].get("message")
                       or "")
                if msg:
                    return {"success": False, "stdout": "", "stderr": msg[:120]}
            except (json.JSONDecodeError, IndexError, KeyError):
                pass

    err = (stderr or stdout or "bilinmeyen hata")[:120]
    return {"success": False, "stdout": "", "stderr": err}


def view_all(
    accounts: list[Account],
    tweet_id: str,
    repeat: int = 1,
    workers: int = DEFAULT_WORKERS,
    delay_range: tuple[float, float] = (0.5, 2.0),
):
    """
    Tüm hesaplardan tweet'e view gönderir.

    repeat     : Her hesap kaç kez view atsın
    workers    : Paralel thread sayısı
    delay_range: Aynı hesabın ardışık view'leri arasındaki bekleme aralığı (sn)

    Her istek:
      • Farklı rotating proxy kullanır (get_proxy())
      • Rastgele User-Agent seçer
      • Doğrudan GraphQL HTTP isteği yapar (twitter_cli gerekmez)
    """
    if not _REQUESTS_OK:
        print(f"{Colors.RED}✗ requests kütüphanesi bulunamadı — pip install requests{Colors.RESET}")
        return

    total = len(accounts) * repeat
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}👁  Toplu View Gönderimi Başlıyor{Colors.RESET}")
    print(f"  {Colors.GRAY}Tweet ID : {tweet_id}{Colors.RESET}")
    print(f"  {Colors.GRAY}Hesap    : {len(accounts)}{Colors.RESET}")
    print(f"  {Colors.GRAY}Tekrar   : {repeat}x / hesap{Colors.RESET}")
    print(f"  {Colors.GRAY}Toplam   : ~{total} view{Colors.RESET}")
    print(f"  {Colors.GRAY}Threads  : {min(workers, len(accounts))}{Colors.RESET}")
    if _PROXY_POOL:
        print(f"  {Colors.GRAY}Proxy    : {len(_PROXY_POOL)} proxy havuzu (rotating){Colors.RESET}")
    else:
        print(f"  {Colors.YELLOW}  ⚠ Proxy yok — tüm istekler aynı IP'den gidecek{Colors.RESET}")
    print()

    success_count = 0
    fail_count    = 0
    lock          = threading.Lock()

    def task(acc: Account):
        acc_ok = acc_fail = 0
        last_err = ""
        for i in range(repeat):
            r = _send_view_direct(acc, tweet_id)
            if r["success"]:
                acc_ok += 1
            else:
                acc_fail += 1
                last_err = r["stderr"]
            if i < repeat - 1:
                time.sleep(random.uniform(*delay_range))

        if acc_ok == repeat:
            status = f"{Colors.GREEN}✓ {acc_ok}/{repeat}{Colors.RESET}"
        elif acc_ok > 0:
            status = f"{Colors.YELLOW}~ {acc_ok}/{repeat}{Colors.RESET} {Colors.GRAY}{last_err[:50]}{Colors.RESET}"
        else:
            status = f"{Colors.RED}✗ 0/{repeat} — {last_err[:60]}{Colors.RESET}"

        tprint(f"  {Colors.CYAN}@{acc.username:<22}{Colors.RESET} → {status}")
        log_result(acc, "view", tweet_id,
                   {"success": acc_ok > 0, "stdout": f"{acc_ok}/{repeat} ok", "stderr": last_err})
        with lock:
            success_count += acc_ok
            fail_count    += acc_fail

    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        list(pool.map(task, accounts))

    print_action_summary(success_count, fail_count, total)


# ─── Gizlilik Ayarı (Protected / Unprotected) ───

def _set_protected(account: Account, protected: bool) -> dict:
    """
    account/settings.json REST endpoint'i ile hesabın protected ayarını değiştirir.
    TwitterClient'ın altyapısını (doğru URL + _build_headers) kullanır.
    protected=True → gizli hesap, protected=False → açık hesap
    """
    if not _TWCLIENT_OK:
        return {"success": False, "stdout": "", "stderr": "twitter_cli bulunamadı"}

    try:
        from twitter_cli.client import _get_cffi_session
    except ImportError:
        return {"success": False, "stdout": "", "stderr": "twitter_cli.client import hatası"}

    # twitter_cli'nın kullandığı doğru URL prefixi: x.com/i/api/
    url = "https://x.com/i/api/1.1/account/settings.json"

    client = _TwitterClient(account.auth_token, account.ct0)
    headers = client._build_headers(url=url, method="POST")
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    # GraphQL POST için ayarlanan Referer'ı settings için düzelt
    headers["Referer"] = "https://x.com/settings/account"
    headers["Sec-Fetch-Site"] = "same-origin"

    body = f"protected={'true' if protected else 'false'}"
    proxy = get_proxy()
    proxies = {"http": proxy, "https": proxy} if proxy else None
    session = _get_cffi_session()

    try:
        resp = session.post(
            url,
            headers=headers,
            data=body,
            proxies=proxies,
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {"success": True, "stdout": str(data)[:200], "stderr": ""}
        return {"success": False, "stdout": "",
                "stderr": f"HTTP {resp.status_code}: {resp.text[:150]}"}
    except Exception as exc:
        return {"success": False, "stdout": "", "stderr": str(exc)[:150]}


def follow_boost(accounts: list[Account], workers: int = DEFAULT_WORKERS, delay: float = 3.0):
    """
    Çapraz takip — Round-Robin yaklaşımı:
    Her turda her hesap 1 kişiyi takip eder (1→?, 2→?, …, N→?).
    Hedefler tamamen rastgele karıştırılır, böylece aynı hesap art arda
    birden fazla follow atmaz — rate-limit baskısı minimuma iner.

    Tur sayısı = N-1  →  toplam N×(N-1) follow işlemi.
    """
    n = len(accounts)
    if n < 2:
        print(f"{Colors.RED}✗ En az 2 hesap gerekli.{Colors.RESET}")
        return

    total_pairs = n * (n - 1)
    rounds      = n - 1

    print(f"\n{Colors.BOLD}{Colors.CYAN}{'━'*50}{Colors.RESET}")
    print(f"{Colors.BOLD}🔗 Çapraz Takip Boost  (Round-Robin){Colors.RESET}")
    print(f"  Hesaplar     : {Colors.CYAN}{n}{Colors.RESET}")
    print(f"  Toplam işlem : {Colors.CYAN}{total_pairs}{Colors.RESET}  ({n} hesap × {n-1} tur)")
    print(f"  Threads/tur  : {Colors.CYAN}{workers}{Colors.RESET}")
    print(f"  Tur arası bekleme : {Colors.CYAN}{delay}s{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'━'*50}{Colors.RESET}\n")

    # Her hesap için rastgele karıştırılmış hedef listesi oluştur
    queues: dict[str, list[Account]] = {}
    for acc in accounts:
        targets = [a for a in accounts if a.username != acc.username]
        random.shuffle(targets)
        queues[acc.username] = targets

    ok_count = fail_count = 0
    lock = threading.Lock()

    def follow_one(pair: tuple) -> None:
        nonlocal ok_count, fail_count
        follower, followee = pair
        r, _ = run_with_retry(follower, ["follow", followee.username, "--json"], timeout=20)
        ok, err = parse_twitter_response(r)
        status = (f"{Colors.GREEN}✓{Colors.RESET}"
                  if ok else f"{Colors.RED}✗ {err[:45]}{Colors.RESET}")
        tprint(f"  {Colors.CYAN}@{follower.username:<20}{Colors.RESET} → "
               f"{Colors.CYAN}@{followee.username:<20}{Colors.RESET} {status}")
        log_result(follower, "follow_boost", followee.username, r)
        with lock:
            if ok:
                ok_count += 1
            else:
                fail_count += 1

    for rnd in range(rounds):
        # Bu turda her hesap kendi sırasındaki hedefi takip eder
        round_pairs = []
        for acc in accounts:
            q = queues[acc.username]
            if rnd < len(q):
                round_pairs.append((acc, q[rnd]))

        # Tur içindeki sırayı da karıştır (ek rastgelelik)
        random.shuffle(round_pairs)

        tprint(f"{Colors.GRAY}  ── Tur {rnd+1}/{rounds}  "
               f"({len(round_pairs)} işlem) ──{Colors.RESET}")

        with ThreadPoolExecutor(max_workers=min(workers, len(round_pairs))) as pool:
            list(pool.map(follow_one, round_pairs))

        # Son tur değilse bekle
        if rnd < rounds - 1 and delay > 0:
            time.sleep(delay)

    print(f"\n{Colors.BOLD}{'─'*50}{Colors.RESET}")
    print(f"  {Colors.GREEN}✓ Başarılı: {ok_count}{Colors.RESET}  "
          f"{Colors.RED}✗ Başarısız: {fail_count}{Colors.RESET}  "
          f"{Colors.GRAY}Toplam: {total_pairs}{Colors.RESET}")


def unprotect_all(accounts: list[Account], workers: int = DEFAULT_WORKERS):
    """Tüm hesapları açık (public) yapar — protected=false."""
    def action(acc):
        r = _set_protected(acc, protected=False)
        return r["success"], r["stderr"] or "Hata", r

    run_bulk_action(accounts, action,
                    "🔓 Toplu Gizliliği Kaldır (Açık Yap)",
                    "unprotect", "protected=false", workers=workers)


def protect_all(accounts: list[Account], workers: int = DEFAULT_WORKERS):
    """Tüm hesapları gizli (protected) yapar — protected=true."""
    def action(acc):
        r = _set_protected(acc, protected=True)
        return r["success"], r["stderr"] or "Hata", r

    run_bulk_action(accounts, action,
                    "🔒 Toplu Gizli Yap (Protected)",
                    "protect", "protected=true", workers=workers)


# ─── Boost Modu ───
def boost_all(
    accounts: list[Account],
    tweet_text: str,
    reply_text: str = "🔥",
    workers: int = DEFAULT_WORKERS,
    max_retry: int = DEFAULT_MAX_RETRY,
    skip_follow: bool = False,
):
    """
    Boost modu — 4 aşama:
      1. Tüm hesaplar tweeti atar, tweet ID'leri toplanır
      2. Her hesap diğerlerinin tweetini like + retweet + bookmark atar
      3. Her hesap diğerlerinin tweetine yanıt atar
      4. Tüm hesaplar birbirini takip eder
    """
    n = len(accounts)
    total_interactions = n * (n - 1)

    print(f"\n{Colors.BOLD}{Colors.BG_BLUE} ⚡ BOOST MODU BAŞLIYOR {Colors.RESET}")
    print(f"  {Colors.GRAY}Tweet   : \"{tweet_text[:70]}{'...' if len(tweet_text) > 70 else ''}\"{Colors.RESET}")
    print(f"  {Colors.GRAY}Yanıt   : \"{reply_text[:50]}\"{Colors.RESET}")
    print(f"  {Colors.GRAY}Hesap   : {n}{Colors.RESET}")
    print(f"  {Colors.GRAY}Threads : {min(workers, n)}{Colors.RESET}")
    print(f"  {Colors.GRAY}Tahmini işlem: ~{total_interactions * (3 if skip_follow else 4) + n}{Colors.RESET}\n")

    # ── Aşama 1: Tüm hesaplar tweet atar ──────────────────────────────
    print(f"{Colors.BOLD}{Colors.CYAN}━━━ AŞAMA 1/{'3' if skip_follow else '4'}: Tweet Gönderimi ━━━{Colors.RESET}")
    posted: list[tuple[Account, str]] = []   # (account, tweet_id)
    post_lock = threading.Lock()

    def post_task(acc: Account):
        args = ["post", tweet_text, "--json"]
        result, _ = run_with_retry(acc, args, timeout=30, max_retry=max_retry)
        ok, err   = parse_twitter_response(result)
        tweet_id  = None
        if ok and result["stdout"]:
            try:
                data     = json.loads(result["stdout"])
                tweet_id = data.get("data", {}).get("id")
            except json.JSONDecodeError:
                pass
        if ok and tweet_id:
            tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → "
                   f"{Colors.GREEN}✓ {tweet_id}{Colors.RESET}")
            with post_lock:
                posted.append((acc, tweet_id))
        else:
            tprint(f"  {Colors.CYAN}@{acc.username:<20}{Colors.RESET} → "
                   f"{Colors.RED}✗ {err or 'ID alınamadı'}{Colors.RESET}")
        log_result(acc, "boost_post", tweet_text, result)

    with ThreadPoolExecutor(max_workers=min(workers, n)) as pool:
        list(pool.map(post_task, accounts))

    if not posted:
        print(f"\n{Colors.RED}✗ Hiç tweet gönderilemedi, boost iptal.{Colors.RESET}")
        return

    print(f"\n  {Colors.GREEN}✓ {len(posted)}/{n} tweet başarıyla gönderildi.{Colors.RESET}")

    # ── Aşama 2: Like + Retweet + Bookmark ────────────────────────────
    print(f"\n{Colors.BOLD}{Colors.CYAN}━━━ AŞAMA 2/{'3' if skip_follow else '4'}: Like · Retweet · Bookmark ━━━{Colors.RESET}")
    print(f"  {Colors.GRAY}{len(posted)} tweet × {n-1} hesap = ~{len(posted)*(n-1)*3} işlem{Colors.RESET}\n")

    engage_ok = engage_fail = 0
    engage_lock = threading.Lock()

    def engage_task(pair: tuple):
        nonlocal engage_ok, engage_fail
        actor, (owner, tweet_id) = pair
        if actor.username == owner.username:
            return
        results = []
        for cmd in (["like", tweet_id, "--json"],
                    ["retweet", tweet_id, "--json"],
                    ["bookmark", tweet_id, "--json"]):
            r, _ = run_with_retry(actor, cmd, timeout=20, max_retry=max_retry)
            ok, _ = parse_twitter_response(r)
            results.append(ok)
            log_result(actor, cmd[0], tweet_id, r)
        all_ok = all(results)
        icon   = Colors.GREEN + "✓" if all_ok else Colors.YELLOW + "~"
        tprint(f"  {Colors.CYAN}@{actor.username:<18}{Colors.RESET} ▸ "
               f"@{owner.username:<18} → {icon}{Colors.RESET} "
               f"{'like+RT+BM' if all_ok else str(results.count(True))+'/3 ok'}")
        with engage_lock:
            if all_ok:
                engage_ok += 1
            else:
                engage_fail += 1

    pairs = [(actor, post) for post in posted for actor in accounts
             if actor.username != post[0].username]

    with ThreadPoolExecutor(max_workers=min(workers, max(len(pairs), 1))) as pool:
        list(pool.map(engage_task, pairs))

    print(f"\n  {Colors.GREEN}✓ Başarılı: {engage_ok}{Colors.RESET}  "
          f"{Colors.YELLOW}~ Kısmi: {engage_fail}{Colors.RESET}")

    # ── Aşama 3: Yanıt ────────────────────────────────────────────────
    print(f"\n{Colors.BOLD}{Colors.CYAN}━━━ AŞAMA 3/{'3' if skip_follow else '4'}: Yanıtlar ━━━{Colors.RESET}")
    print(f"  {Colors.GRAY}{len(posted)} tweet × {n-1} hesap = ~{len(posted)*(n-1)} yanıt{Colors.RESET}\n")

    reply_ok = reply_fail = 0
    reply_lock = threading.Lock()

    def reply_task(pair: tuple):
        nonlocal reply_ok, reply_fail
        actor, (owner, tweet_id) = pair
        if actor.username == owner.username:
            return
        r, _ = run_with_retry(actor, ["reply", tweet_id, reply_text, "--json"],
                               timeout=30, max_retry=max_retry)
        ok, err = parse_twitter_response(r)
        tprint(f"  {Colors.CYAN}@{actor.username:<18}{Colors.RESET} ▸ "
               f"@{owner.username:<18} → "
               f"{Colors.GREEN}✓ yanıt{Colors.RESET}" if ok else
               f"  {Colors.CYAN}@{actor.username:<18}{Colors.RESET} ▸ "
               f"@{owner.username:<18} → {Colors.RED}✗ {err}{Colors.RESET}")
        log_result(actor, "boost_reply", tweet_id, r)
        with reply_lock:
            if ok:
                reply_ok += 1
            else:
                reply_fail += 1

    with ThreadPoolExecutor(max_workers=min(workers, max(len(pairs), 1))) as pool:
        list(pool.map(reply_task, pairs))

    print(f"\n  {Colors.GREEN}✓ Başarılı: {reply_ok}{Colors.RESET}  "
          f"{Colors.RED}✗ Başarısız: {reply_fail}{Colors.RESET}")

    # ── Aşama 4: Birbirini Takip Et ───────────────────────────────────
    if not skip_follow:
        print(f"\n{Colors.BOLD}{Colors.CYAN}━━━ AŞAMA 4/4: Karşılıklı Takip ━━━{Colors.RESET}")
        follow_pairs = n * (n - 1)
        print(f"  {Colors.GRAY}{n} hesap × {n-1} = {follow_pairs} follow işlemi{Colors.RESET}\n")

        follow_ok = follow_fail = 0
        follow_lock = threading.Lock()

        def follow_task(pair: tuple):
            nonlocal follow_ok, follow_fail
            follower, followee = pair
            r, _ = run_with_retry(follower, ["follow", followee.username, "--json"],
                                   timeout=20, max_retry=max_retry)
            ok, err = parse_twitter_response(r)
            tprint(f"  {Colors.CYAN}@{follower.username:<18}{Colors.RESET} → "
                   f"@{followee.username:<18} "
                   f"{Colors.GREEN}✓{Colors.RESET}" if ok else
                   f"  {Colors.CYAN}@{follower.username:<18}{Colors.RESET} → "
                   f"@{followee.username:<18} {Colors.RED}✗{Colors.RESET}")
            log_result(follower, "boost_follow", followee.username, r)
            with follow_lock:
                if ok:
                    follow_ok += 1
                else:
                    follow_fail += 1

        all_follow_pairs = [(a, b) for a in accounts for b in accounts if a.username != b.username]
        with ThreadPoolExecutor(max_workers=min(workers, max(len(all_follow_pairs), 1))) as pool:
            list(pool.map(follow_task, all_follow_pairs))

        print(f"\n  {Colors.GREEN}✓ Başarılı: {follow_ok}{Colors.RESET}  "
              f"{Colors.RED}✗ Başarısız: {follow_fail}{Colors.RESET}")

    # ── Genel Özet ────────────────────────────────────────────────────
    print(f"\n{Colors.BOLD}{Colors.BG_GREEN} ✓ BOOST TAMAMLANDI {Colors.RESET}")
    print(f"  {Colors.GREEN}Tweet   : {len(posted)}/{n}{Colors.RESET}")
    print(f"  {Colors.GREEN}Etkileşim: {engage_ok} başarılı{Colors.RESET}")
    print(f"  {Colors.GREEN}Yanıt   : {reply_ok} başarılı{Colors.RESET}")
    if not skip_follow:
        print(f"  {Colors.GREEN}Takip   : {follow_ok} başarılı{Colors.RESET}")


# ─── Proxy Ayarlama ───
def _set_proxy_interactive():
    """
    Çalışma anında proxy havuzunu değiştirir ve proxy.txt'ye kaydeder.

    Tek proxy  : http://user:pass@gw.dataimpulse.com:823
    Çok proxy  : Her satıra bir proxy — round-robin rotasyon yapılır
    DataImpulse: Tek satır yeterli; gateway her bağlantıda IP değiştirir
    """
    global _PROXY_POOL, _proxy_counter

    if _PROXY_POOL:
        print(f"\n  Mevcut havuz ({len(_PROXY_POOL)} proxy):")
        for i, p in enumerate(_PROXY_POOL, 1):
            print(f"  {Colors.CYAN}{i}. {_proxy_display_str(p)}{Colors.RESET}")
    else:
        print(f"\n  Mevcut proxy : {Colors.YELLOW}yok{Colors.RESET}")

    print(f"\n  {Colors.GRAY}Formatlar:{Colors.RESET}")
    print(f"  {Colors.GRAY}  DataImpulse : http://kullanici:sifre@gw.dataimpulse.com:823{Colors.RESET}")
    print(f"  {Colors.GRAY}  Standart    : http://host:port{Colors.RESET}")
    print(f"  {Colors.GRAY}  Çok proxy   : Virgülle ayır → proxy1,proxy2,proxy3{Colors.RESET}")
    print(f"  {Colors.GRAY}  (Boş bırakırsan proxy kaldırılır){Colors.RESET}")

    try:
        raw = input(f"{Colors.CYAN}Proxy(ler) ▸ {Colors.RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        return

    if not raw:
        _PROXY_POOL = []
        _proxy_counter = 0
        if PROXY_FILE.exists():
            PROXY_FILE.write_text("# proxy.txt — her satıra bir proxy\n")
        print(f"{Colors.YELLOW}✓ Proxy havuzu temizlendi{Colors.RESET}")
        return

    # Virgülle veya yeni satırla ayrılmış proxy listesi
    parts = [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]
    normalized = [_normalize_proxy(p) for p in parts]

    _PROXY_POOL = normalized
    _proxy_counter = 0

    # proxy.txt'ye kaydet
    PROXY_FILE.write_text("# DataImpulse / rotating proxy listesi\n" +
                           "\n".join(normalized) + "\n")

    if len(normalized) == 1:
        print(f"{Colors.GREEN}✓ Proxy ayarlandı: {_proxy_display_str(normalized[0])}{Colors.RESET}")
        print(f"  {Colors.GRAY}(DataImpulse gateway her bağlantıda otomatik IP değiştirir){Colors.RESET}")
    else:
        print(f"{Colors.GREEN}✓ {len(normalized)} proxy havuza eklendi (round-robin rotasyon aktif){Colors.RESET}")
        for i, p in enumerate(normalized, 1):
            print(f"  {Colors.GRAY}{i}. {_proxy_display_str(p)}{Colors.RESET}")


def _ask_ai_rewrite_interactive() -> tuple[bool, bool]:
    """İnteraktif modda AI rewrite tercihini alır."""
    raw = input(f"{Colors.CYAN}AI her hesap için ayrı yazsın mı? (e/h/dry) ▸ {Colors.RESET}").strip().lower()
    if raw in ("dry", "d", "deneme", "preview", "önizle", "onizle"):
        return True, True
    return raw in ("e", "evet", "y", "yes"), False


# ─── İnteraktif Mod ───
def interactive_mode(accounts: list[Account]):
    print_banner()
    show_accounts(accounts)

    workers = DEFAULT_WORKERS

    while True:
        print(f"\n{Colors.BOLD}{Colors.CYAN}━━━ KOMUTLAR ━━━{Colors.RESET}")
        print(f"  {Colors.BOLD}1{Colors.RESET}  → Tüm hesaplardan tweet at")
        print(f"  {Colors.BOLD}2{Colors.RESET}  → Seçili hesaplardan tweet at")
        print(f"  {Colors.BOLD}{Colors.MAGENTA}ai{Colors.RESET} → {Colors.MAGENTA}Yönerge ile AI tweet{Colors.RESET} (her hesaba özgün metin, openai-oauth)")
        print(f"  {Colors.BOLD}3{Colors.RESET}  → Toplu beğeni (like)")
        print(f"  {Colors.BOLD}4{Colors.RESET}  → Toplu retweet")
        print(f"  {Colors.BOLD}5{Colors.RESET}  → Toplu takip (follow)")
        print(f"  {Colors.BOLD}6{Colors.RESET}  → Toplu yanıt (reply)")
        print(f"  {Colors.BOLD}{Colors.MAGENTA}6a{Colors.RESET} → {Colors.MAGENTA}AI yanıt (yönerge){Colors.RESET} — her hesaba özgün metin")
        print(f"  {Colors.BOLD}7{Colors.RESET}  → Toplu bookmark")
        print(f"  {Colors.BOLD}v{Colors.RESET}  → {Colors.MAGENTA}👁  Toplu view gönder{Colors.RESET}")
        print(f"  {Colors.BOLD}8{Colors.RESET}  → Hesap durumlarını kontrol et")
        print(f"  {Colors.BOLD}8p{Colors.RESET} → Askıya alınmış hesapları temizle (purge)")
        print(f"  {Colors.BOLD}9{Colors.RESET}  → Hesap listesi")
        print(f"  {Colors.BOLD}{Colors.YELLOW}b{Colors.RESET}  → {Colors.YELLOW}⚡ Boost modu{Colors.RESET} (tweet + like + RT + BM + reply + follow)")
        print(f"  {Colors.BOLD}w{Colors.RESET}  → Thread sayısını ayarla (şu an: {workers})")
        if _PROXY_POOL:
            proxy_status = (f"{Colors.GREEN}{len(_PROXY_POOL)} proxy "
                            f"({_proxy_display_str(_PROXY_POOL[0])}{',...' if len(_PROXY_POOL) > 1 else ''})"
                            f"{Colors.RESET}")
        else:
            proxy_status = f"{Colors.GRAY}yok{Colors.RESET}"
        print(f"  {Colors.BOLD}p{Colors.RESET}  → Proxy havuzu (şu an: {proxy_status})")
        print(f"  {Colors.BOLD}0{Colors.RESET}  → Çıkış")

        try:
            choice = input(f"\n{Colors.CYAN}Seçiminiz ▸ {Colors.RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{Colors.YELLOW}👋 Hoşça kal!{Colors.RESET}")
            break

        if choice == "1":
            text = input(f"{Colors.CYAN}Tweet metni ▸ {Colors.RESET}").strip()
            if text:
                ai_rewrite, ai_dry_run = _ask_ai_rewrite_interactive()
                post_all(accounts, text, workers=workers,
                         ai_rewrite=ai_rewrite, ai_dry_run=ai_dry_run)

        elif choice == "2":
            show_accounts(accounts)
            indices_str = input(f"{Colors.CYAN}Hesap numaraları (virgülle) ▸ {Colors.RESET}").strip()
            try:
                indices = [int(x.strip()) for x in indices_str.split(",")]
            except ValueError:
                print(f"{Colors.RED}✗ Geçersiz numara{Colors.RESET}")
                continue
            text = input(f"{Colors.CYAN}Tweet metni ▸ {Colors.RESET}").strip()
            if text:
                ai_rewrite, ai_dry_run = _ask_ai_rewrite_interactive()
                post_selected(accounts, indices, text, workers=workers,
                              ai_rewrite=ai_rewrite, ai_dry_run=ai_dry_run)

        elif choice in ("ai", "AI"):
            instruction = input(
                f"{Colors.CYAN}Yönerge (AI buna göre her hesaba farklı tweet yazar) ▸ {Colors.RESET}"
            ).strip()
            if not instruction:
                print(f"{Colors.RED}✗ Yönerge boş olamaz{Colors.RESET}")
                continue
            scope = input(
                f"{Colors.CYAN}Tüm hesaplar mı? (e/h, h=seçili numaralar) ▸ {Colors.RESET}"
            ).strip().lower()
            target: list[Account] = accounts
            if scope in ("h", "hayır", "n", "no"):
                show_accounts(accounts)
                indices_str = input(f"{Colors.CYAN}Hesap numaraları (virgülle) ▸ {Colors.RESET}").strip()
                try:
                    idxs = [int(x.strip()) for x in indices_str.split(",")]
                except ValueError:
                    print(f"{Colors.RED}✗ Geçersiz numara{Colors.RESET}")
                    continue
                target = []
                for i in idxs:
                    if 1 <= i <= len(accounts):
                        target.append(accounts[i - 1])
                    else:
                        print(f"{Colors.YELLOW}⚠ Geçersiz: {i}{Colors.RESET}")
                if not target:
                    print(f"{Colors.RED}✗ Hesap seçilmedi{Colors.RESET}")
                    continue
            dry = input(
                f"{Colors.CYAN}Sadece önizleme (tweet gönderme)? (e/h) ▸ {Colors.RESET}"
            ).strip().lower()
            post_all_from_instruction(
                target,
                instruction,
                dry_run=dry in ("e", "evet", "y", "yes"),
                workers=workers,
            )

        elif choice == "3":
            tweet_id = input(f"{Colors.CYAN}Tweet ID ▸ {Colors.RESET}").strip()
            if tweet_id:
                like_all(accounts, tweet_id, workers=workers)

        elif choice == "4":
            tweet_id = input(f"{Colors.CYAN}Tweet ID ▸ {Colors.RESET}").strip()
            if tweet_id:
                retweet_all(accounts, tweet_id, workers=workers)

        elif choice == "5":
            target = input(f"{Colors.CYAN}Kullanıcı adı ▸ {Colors.RESET}").strip().lstrip("@")
            if target:
                follow_all(accounts, target, workers=workers)

        elif choice == "6":
            tweet_id = input(f"{Colors.CYAN}Tweet ID ▸ {Colors.RESET}").strip()
            text     = input(f"{Colors.CYAN}Yanıt metni ▸ {Colors.RESET}").strip()
            if tweet_id and text:
                ai_rewrite, ai_dry_run = _ask_ai_rewrite_interactive()
                reply_all(
                    accounts, tweet_id, text, workers=workers,
                    ai_rewrite=ai_rewrite, ai_dry_run=ai_dry_run,
                )

        elif choice in ("6a", "6A"):
            tweet_id = input(f"{Colors.CYAN}Tweet ID (yanıt verilecek) ▸ {Colors.RESET}").strip()
            instruction = input(
                f"{Colors.CYAN}Yönerge (AI her hesaba farklı yanıt yazar) ▸ {Colors.RESET}"
            ).strip()
            if not tweet_id or not instruction:
                print(f"{Colors.RED}✗ Tweet ID ve yönerge gerekli{Colors.RESET}")
                continue
            scope = input(
                f"{Colors.CYAN}Tüm hesaplar mı? (e/h, h=seçili) ▸ {Colors.RESET}"
            ).strip().lower()
            target: list[Account] = accounts
            if scope in ("h", "hayır", "n", "no"):
                show_accounts(accounts)
                indices_str = input(f"{Colors.CYAN}Hesap numaraları (virgülle) ▸ {Colors.RESET}").strip()
                try:
                    idxs = [int(x.strip()) for x in indices_str.split(",")]
                except ValueError:
                    print(f"{Colors.RED}✗ Geçersiz numara{Colors.RESET}")
                    continue
                target = []
                for i in idxs:
                    if 1 <= i <= len(accounts):
                        target.append(accounts[i - 1])
                    else:
                        print(f"{Colors.YELLOW}⚠ Geçersiz: {i}{Colors.RESET}")
                if not target:
                    print(f"{Colors.RED}✗ Hesap seçilmedi{Colors.RESET}")
                    continue
            dry = input(
                f"{Colors.CYAN}Sadece önizleme (yanıt gönderme)? (e/h) ▸ {Colors.RESET}"
            ).strip().lower()
            reply_all_from_instruction(
                target,
                tweet_id,
                instruction,
                dry_run=dry in ("e", "evet", "y", "yes"),
                workers=workers,
            )

        elif choice == "7":
            tweet_id = input(f"{Colors.CYAN}Tweet ID ▸ {Colors.RESET}").strip()
            if tweet_id:
                bookmark_all(accounts, tweet_id, workers=workers)

        elif choice == "v":
            tweet_id = input(f"{Colors.CYAN}Tweet ID ▸ {Colors.RESET}").strip()
            if tweet_id:
                try:
                    rep = int(input(f"{Colors.CYAN}Her hesap kaç kez view atsın? (önerilen: 3-10) ▸ {Colors.RESET}").strip() or "1")
                    rep = max(1, rep)
                except ValueError:
                    rep = 1
                try:
                    dmin = float(input(f"{Colors.CYAN}İstekler arası min bekleme sn (önerilen: 0.5) ▸ {Colors.RESET}").strip() or "0.5")
                    dmax = float(input(f"{Colors.CYAN}İstekler arası max bekleme sn (önerilen: 2.0) ▸ {Colors.RESET}").strip() or "2.0")
                except ValueError:
                    dmin, dmax = 0.5, 2.0
                view_all(accounts, tweet_id, repeat=rep, workers=workers,
                         delay_range=(min(dmin, dmax), max(dmin, dmax)))

        elif choice == "8":
            check_accounts(accounts, workers=workers)

        elif choice == "8p":
            d = input(f"{Colors.CYAN}Yazma kısıtlamasını da test et? (derin mod) (e/h) ▸ {Colors.RESET}").strip().lower()
            purge_accounts(accounts, workers=workers, deep=(d in ("e", "evet", "y", "yes")))
            accounts = load_accounts()  # listeyi yenile

        elif choice == "9":
            show_accounts(accounts)

        elif choice == "b":
            text = input(f"{Colors.CYAN}Tweet metni ▸ {Colors.RESET}").strip()
            if not text:
                print(f"{Colors.RED}✗ Tweet metni boş olamaz{Colors.RESET}")
                continue
            reply = input(f"{Colors.CYAN}Yanıt metni (boş bırak = 🔥) ▸ {Colors.RESET}").strip()
            if not reply:
                reply = "🔥"
            skip_f = input(f"{Colors.CYAN}Birbirini takip etsin mi? (e/h) ▸ {Colors.RESET}").strip().lower()
            boost_all(accounts, text, reply_text=reply,
                      workers=workers, skip_follow=(skip_f not in ("e", "evet", "y", "yes")))

        elif choice == "w":
            try:
                w = int(input(f"{Colors.CYAN}Thread sayısı ▸ {Colors.RESET}").strip())
                if w < 1:
                    raise ValueError
                workers = w
                print(f"{Colors.GREEN}✓ Thread sayısı {workers} olarak ayarlandı{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}✗ Geçersiz sayı{Colors.RESET}")

        elif choice == "p":
            _set_proxy_interactive()

        elif choice == "0":
            print(f"\n{Colors.YELLOW}👋 Hoşça kal!{Colors.RESET}")
            break

        else:
            print(f"{Colors.RED}✗ Geçersiz seçim{Colors.RESET}")

# ─── CLI Argüman İşleme ───
def main():
    parser = argparse.ArgumentParser(
        description="Tweeter - Çoklu Twitter Hesap Yönetim Sistemi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python tweeter.py                                         # İnteraktif mod
  python tweeter.py post "Merhaba!" --workers 20           # 20 thread ile tweet at
  python tweeter.py post "Merhaba!" --ai-rewrite           # Her hesap için AI varyantı üretip gönder
  python tweeter.py post "Merhaba!" --ai-dry-run           # AI varyantlarını göster, gönderme
  python tweeter.py post-ai "Yeni ürün için kısa hype yaz"  # Yönerge → her hesaba özgün tweet
  python tweeter.py post-ai "..." --dry-run                # Önizleme, gönderme
  python tweeter.py reply 123 "Harika!" --ai-rewrite       # Metni hesap başına AI ile çeşitlendir
  python tweeter.py reply-ai 123 "Kısa destek mesajı, emoji az"  # Yönerge → özgün yanıtlar
  python tweeter.py reply-ai 123 "..." --dry-run -a 1,2,3
  python tweeter.py post "Test" -a 1,2,3                   # Seçili hesaplardan tweet at
  python tweeter.py like 1234567890                        # Tüm hesaplardan beğen
  python tweeter.py retweet 1234567890 --workers 50        # 50 thread ile RT
  python tweeter.py follow elonmusk                        # Tüm hesaplardan takip et
  python tweeter.py reply 1234567890 "Harika!"             # Tüm hesaplardan yanıt
  python tweeter.py bookmark 1234567890                    # Tüm hesaplardan bookmark
  python tweeter.py view 1234567890                        # Tüm hesaplardan view
  python tweeter.py view 1234567890 --repeat 5             # Her hesap 5 kez view
  python tweeter.py check --workers 30                     # 30 thread ile kontrol
  python tweeter.py purge                                  # Askıya alınmış hesapları sil
  python tweeter.py purge --dry-run                        # Sadece listele, silme
  python tweeter.py list                                   # Hesapları listele
  python tweeter.py boost "Harika içerik!" --workers 20   # ⚡ Boost modu
  python tweeter.py boost "Test" --reply "Süper!" --no-follow  # Takipsiz boost
        """
    )

    # Ortak parent parser — tüm subcommand'lara --workers, --retry, --proxy ekler
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS,
        help=f"Paralel çalışan thread sayısı (varsayılan: {DEFAULT_WORKERS})"
    )
    common.add_argument(
        "--retry", type=int, default=DEFAULT_MAX_RETRY,
        help=f"Başarısız işlemde yeniden deneme sayısı (varsayılan: {DEFAULT_MAX_RETRY})"
    )
    common.add_argument(
        "--proxy", type=str, default=None,
        help="Proxy adresi (örn: http://host:port). proxy.txt'yi geçersiz kılar."
    )
    common.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"Komut başına timeout saniyesi (varsayılan: {DEFAULT_TIMEOUT})"
    )

    subparsers = parser.add_subparsers(dest="command")

    # Post komutu
    post_parser = subparsers.add_parser("post", help="Tweet gönder", parents=[common])
    post_parser.add_argument("text", help="Tweet metni")
    post_parser.add_argument("-a", "--accounts", help="Hesap numaraları (virgülle), boşsa tümü")
    post_parser.add_argument("-r", "--reply-to", help="Yanıt olarak gönderilecek tweet ID")
    post_parser.add_argument("-i", "--image", action="append", help="Eklenecek resim (en fazla 4)")
    post_parser.add_argument("--delay-min", type=float, default=0, help="Min gecikme (saniye, 0=yok)")
    post_parser.add_argument("--delay-max", type=float, default=0, help="Max gecikme (saniye, 0=yok)")
    post_parser.add_argument(
        "--ai-rewrite", action="store_true",
        help="Her hesap için tweet metnini AI ile ayrı yeniden yaz"
    )
    post_parser.add_argument(
        "--ai-dry-run", action="store_true",
        help="AI varyantlarını üret ve göster; tweet gönderme"
    )
    post_parser.add_argument(
        "--ai-base-url", default=DEFAULT_AI_BASE_URL,
        help=f"OpenAI-compatible base URL (varsayılan: {DEFAULT_AI_BASE_URL})"
    )
    post_parser.add_argument(
        "--ai-model", default=DEFAULT_AI_MODEL,
        help=f"AI model adı (varsayılan: {DEFAULT_AI_MODEL})"
    )
    post_parser.add_argument(
        "--ai-timeout", type=int, default=DEFAULT_AI_TIMEOUT,
        help=f"AI isteği timeout saniyesi (varsayılan: {DEFAULT_AI_TIMEOUT})"
    )

    # post-ai: yönergeden her hesaba özgün tweet
    post_ai_parser = subparsers.add_parser(
        "post-ai",
        help="Yönergeye göre AI ile her hesaba farklı tweet üret ve gönder (openai-oauth /v1)",
        parents=[common],
    )
    post_ai_parser.add_argument(
        "instruction",
        help="AI'ya verilecek yönerge (örn: kısa samimi duyuru, emoji az)",
    )
    post_ai_parser.add_argument("-a", "--accounts", help="Hesap numaraları (virgülle), boşsa tümü")
    post_ai_parser.add_argument("-r", "--reply-to", help="Yanıt olarak gönderilecek tweet ID")
    post_ai_parser.add_argument("-i", "--image", action="append", help="Eklenecek resim (en fazla 4)")
    post_ai_parser.add_argument("--delay-min", type=float, default=0, help="Min gecikme (saniye)")
    post_ai_parser.add_argument("--delay-max", type=float, default=0, help="Max gecikme (saniye)")
    post_ai_parser.add_argument(
        "--dry-run", action="store_true",
        help="AI metinlerini üret ve göster; Twitter'a gönderme",
    )
    post_ai_parser.add_argument(
        "--ai-base-url", default=DEFAULT_AI_BASE_URL,
        help=f"OpenAI-compatible base URL (varsayılan: {DEFAULT_AI_BASE_URL})",
    )
    post_ai_parser.add_argument(
        "--ai-model", default=DEFAULT_AI_MODEL,
        help=f"Model (varsayılan: {DEFAULT_AI_MODEL})",
    )
    post_ai_parser.add_argument(
        "--ai-timeout", type=int, default=DEFAULT_AI_TIMEOUT,
        help=f"AI HTTP timeout sn (varsayılan: {DEFAULT_AI_TIMEOUT})",
    )

    # Like
    like_parser = subparsers.add_parser("like", help="Toplu beğeni", parents=[common])
    like_parser.add_argument("tweet_id", help="Tweet ID")
    like_parser.add_argument("-a", "--accounts", help="Hesap numaraları (virgülle)")

    # Retweet
    rt_parser = subparsers.add_parser("retweet", help="Toplu retweet", parents=[common])
    rt_parser.add_argument("tweet_id", help="Tweet ID")
    rt_parser.add_argument("-a", "--accounts", help="Hesap numaraları (virgülle)")

    # Follow
    follow_parser = subparsers.add_parser("follow", help="Toplu takip", parents=[common])
    follow_parser.add_argument("username", help="Takip edilecek kullanıcı")
    follow_parser.add_argument("-a", "--accounts", help="Hesap numaraları (virgülle)")

    # Reply
    reply_parser = subparsers.add_parser("reply", help="Toplu yanıt", parents=[common])
    reply_parser.add_argument("tweet_id", help="Tweet ID")
    reply_parser.add_argument("text", help="Yanıt metni")
    reply_parser.add_argument("-a", "--accounts", help="Hesap numaraları (virgülle)")
    reply_parser.add_argument("--delay-min", type=float, default=0, help="Gönderimler arası min gecikme (sn)")
    reply_parser.add_argument("--delay-max", type=float, default=0, help="Gönderimler arası max gecikme (sn)")
    reply_parser.add_argument(
        "--ai-rewrite", action="store_true",
        help="Yanıt metnini her hesap için AI ile farklı yeniden yaz",
    )
    reply_parser.add_argument(
        "--ai-dry-run", action="store_true",
        help="AI yanıt varyantlarını üret ve göster; Twitter'a gönderme",
    )
    reply_parser.add_argument(
        "--ai-base-url", default=DEFAULT_AI_BASE_URL,
        help=f"OpenAI-compatible base URL (varsayılan: {DEFAULT_AI_BASE_URL})",
    )
    reply_parser.add_argument(
        "--ai-model", default=DEFAULT_AI_MODEL,
        help=f"AI model (varsayılan: {DEFAULT_AI_MODEL})",
    )
    reply_parser.add_argument(
        "--ai-timeout", type=int, default=DEFAULT_AI_TIMEOUT,
        help=f"AI HTTP timeout sn (varsayılan: {DEFAULT_AI_TIMEOUT})",
    )

    # reply-ai: yönergeden özgün yanıtlar
    reply_ai_parser = subparsers.add_parser(
        "reply-ai",
        help="Tweet'e yönergeye göre her hesaba farklı AI yanıtı gönder",
        parents=[common],
    )
    reply_ai_parser.add_argument("tweet_id", help="Yanıt verilecek tweet ID")
    reply_ai_parser.add_argument(
        "instruction",
        help="AI yönergesi (örn: nazik teşekkür, tek cümle, hashtag yok)",
    )
    reply_ai_parser.add_argument("-a", "--accounts", help="Hesap numaraları (virgülle), boşsa tümü")
    reply_ai_parser.add_argument("--delay-min", type=float, default=0, help="Min gecikme (sn)")
    reply_ai_parser.add_argument("--delay-max", type=float, default=0, help="Max gecikme (sn)")
    reply_ai_parser.add_argument(
        "--dry-run", action="store_true",
        help="AI metinlerini göster; yanıt gönderme",
    )
    reply_ai_parser.add_argument(
        "--ai-base-url", default=DEFAULT_AI_BASE_URL,
        help=f"OpenAI base URL (varsayılan: {DEFAULT_AI_BASE_URL})",
    )
    reply_ai_parser.add_argument(
        "--ai-model", default=DEFAULT_AI_MODEL,
        help=f"Model (varsayılan: {DEFAULT_AI_MODEL})",
    )
    reply_ai_parser.add_argument(
        "--ai-timeout", type=int, default=DEFAULT_AI_TIMEOUT,
        help=f"AI timeout sn (varsayılan: {DEFAULT_AI_TIMEOUT})",
    )

    # Bookmark
    bm_parser = subparsers.add_parser("bookmark", help="Toplu bookmark", parents=[common])
    bm_parser.add_argument("tweet_id", help="Tweet ID")
    bm_parser.add_argument("-a", "--accounts", help="Hesap numaraları (virgülle)")

    # View komutu
    view_parser = subparsers.add_parser(
        "view", help="👁  Toplu view gönder (GraphQL TweetDetail, rotating proxy)",
        parents=[common]
    )
    view_parser.add_argument("tweet_id", help="Tweet ID")
    view_parser.add_argument(
        "--repeat", type=int, default=1,
        help="Her hesap kaç kez view atsın (varsayılan: 1)"
    )
    view_parser.add_argument(
        "--delay-min", type=float, default=0.5,
        help="Ardışık view'ler arası min bekleme sn (varsayılan: 0.5)"
    )
    view_parser.add_argument(
        "--delay-max", type=float, default=2.0,
        help="Ardışık view'ler arası max bekleme sn (varsayılan: 2.0)"
    )
    view_parser.add_argument("-a", "--accounts", help="Hesap numaraları (virgülle)")

    # Boost komutu
    boost_parser = subparsers.add_parser(
        "boost", help="⚡ Boost modu: tweet + like + RT + bookmark + reply + follow",
        parents=[common]
    )
    boost_parser.add_argument("text", help="Atılacak tweet metni")
    boost_parser.add_argument(
        "--reply", default="🔥",
        help="Yanıt metni (varsayılan: 🔥)"
    )
    boost_parser.add_argument(
        "--no-follow", action="store_true",
        help="Karşılıklı takip aşamasını atla"
    )

    # Purge komutu
    purge_parser = subparsers.add_parser(
        "purge", help="Askıya alınmış / ölü hesapları accounts.txt'den sil",
        parents=[common]
    )
    purge_parser.add_argument("--dry-run", action="store_true",
                               help="Sadece listele, dosyaya dokunma")
    purge_parser.add_argument("--deep", action="store_true",
                               help="Yazma kısıtlamasını da test et (like testi)")
    purge_parser.add_argument("--deep-id", default="20",
                               help="Derin test için kullanılacak tweet ID (varsayılan: 20)")

    # Check komutu
    check_parser = subparsers.add_parser("check", help="Hesap durumlarını kontrol et",
                                          parents=[common])
    check_parser.add_argument("--deep", action="store_true",
                               help="Yazma kısıtlamasını da test et (like testi)")
    check_parser.add_argument("--deep-id", default="20",
                               help="Derin test için tweet ID (varsayılan: 20)")

    subparsers.add_parser("list", help="Hesapları listele")

    # fix-usernames komutu
    fu_parser = subparsers.add_parser(
        "fix-usernames",
        help="🔍 Credentials'ları API'dan doğrula, yanlış kullanıcı adlarını düzelt",
        parents=[common],
    )
    fu_parser.add_argument("--dry-run", action="store_true",
                           help="Sadece göster, accounts.txt'ye yazma")

    # Follow Boost komutu
    fb_parser = subparsers.add_parser(
        "follow-boost",
        help="🔗 Çapraz takip: tüm hesaplar birbirini takip eder",
        parents=[common],
    )
    fb_parser.add_argument(
        "--delay", type=float, default=0.5,
        help="Her follow işlemi arasındaki bekleme süresi saniye (varsayılan: 0.5)"
    )
    fb_parser.add_argument("-a", "--accounts", help="Hesap numaraları (virgülle)")

    # Protect / Unprotect komutları
    subparsers.add_parser("protect", help="🔒 Tüm hesapları gizli (protected) yap",
                          parents=[common])
    subparsers.add_parser("unprotect", help="🔓 Tüm hesapları açık (public) yap",
                          parents=[common])

    args = parser.parse_args()

    # Proxy / timeout CLI override
    global _PROXY_POOL, _proxy_counter  # noqa: PLW0603
    if hasattr(args, "proxy") and args.proxy:
        parts = [p.strip() for p in args.proxy.split(",") if p.strip()]
        _PROXY_POOL    = [_normalize_proxy(p) for p in parts]
        _proxy_counter = 0

    accounts = load_accounts()

    if not accounts:
        print(f"{Colors.RED}✗ Hiç hesap yüklenemedi!{Colors.RESET}")
        sys.exit(1)

    def get_selected(accounts_arg):
        if accounts_arg:
            indices = [int(x.strip()) for x in accounts_arg.split(",")]
            return [accounts[i - 1] for i in indices if 1 <= i <= len(accounts)]
        return accounts

    if args.command is None:
        interactive_mode(accounts)

    elif args.command == "post":
        selected = get_selected(args.accounts)
        delay    = (args.delay_min, args.delay_max)
        post_all(selected, args.text, delay_range=delay, reply_to=args.reply_to,
                 images=args.image, workers=args.workers, max_retry=args.retry,
                 ai_rewrite=args.ai_rewrite, ai_dry_run=args.ai_dry_run,
                 ai_base_url=args.ai_base_url, ai_model=args.ai_model,
                 ai_timeout=args.ai_timeout)

    elif args.command == "post-ai":
        selected = get_selected(args.accounts)
        delay    = (args.delay_min, args.delay_max)
        post_all_from_instruction(
            selected,
            args.instruction,
            dry_run=args.dry_run,
            delay_range=delay,
            reply_to=args.reply_to,
            images=args.image,
            workers=args.workers,
            max_retry=args.retry,
            ai_base_url=args.ai_base_url,
            ai_model=args.ai_model,
            ai_timeout=args.ai_timeout,
        )

    elif args.command == "like":
        selected = get_selected(args.accounts)
        like_all(selected, args.tweet_id, workers=args.workers)

    elif args.command == "retweet":
        selected = get_selected(args.accounts)
        retweet_all(selected, args.tweet_id, workers=args.workers)

    elif args.command == "follow":
        selected = get_selected(args.accounts)
        follow_all(selected, args.username.lstrip("@"), workers=args.workers)

    elif args.command == "reply":
        selected = get_selected(args.accounts)
        delay = (args.delay_min, args.delay_max)
        reply_all(
            selected,
            args.tweet_id,
            args.text,
            workers=args.workers,
            max_retry=args.retry,
            delay_range=delay,
            ai_rewrite=args.ai_rewrite,
            ai_dry_run=args.ai_dry_run,
            ai_base_url=args.ai_base_url,
            ai_model=args.ai_model,
            ai_timeout=args.ai_timeout,
        )

    elif args.command == "reply-ai":
        selected = get_selected(args.accounts)
        delay = (args.delay_min, args.delay_max)
        reply_all_from_instruction(
            selected,
            args.tweet_id,
            args.instruction,
            dry_run=args.dry_run,
            delay_range=delay,
            workers=args.workers,
            max_retry=args.retry,
            ai_base_url=args.ai_base_url,
            ai_model=args.ai_model,
            ai_timeout=args.ai_timeout,
        )

    elif args.command == "bookmark":
        selected = get_selected(args.accounts)
        bookmark_all(selected, args.tweet_id, workers=args.workers)

    elif args.command == "view":
        selected = get_selected(args.accounts)
        rep  = max(1, args.repeat)
        dmin = getattr(args, "delay_min", 0.5)
        dmax = getattr(args, "delay_max", 2.0)
        view_all(selected, args.tweet_id, repeat=rep, workers=args.workers,
                 delay_range=(min(dmin, dmax), max(dmin, dmax)))

    elif args.command == "boost":
        boost_all(
            accounts,
            tweet_text=args.text,
            reply_text=args.reply,
            workers=args.workers,
            max_retry=args.retry,
            skip_follow=args.no_follow,
        )

    elif args.command == "purge":
        purge_accounts(accounts, workers=args.workers, dry_run=args.dry_run,
                       deep=args.deep, deep_tweet_id=args.deep_id)

    elif args.command == "check":
        check_accounts(accounts, workers=args.workers,
                       deep=args.deep, deep_tweet_id=args.deep_id)

    elif args.command == "list":
        show_accounts(accounts)

    elif args.command == "fix-usernames":
        fix_usernames(accounts, workers=args.workers, dry_run=args.dry_run)

    elif args.command == "follow-boost":
        selected = get_selected(getattr(args, "accounts", None))
        follow_boost(selected, workers=args.workers, delay=args.delay)

    elif args.command == "protect":
        selected = get_selected(getattr(args, "accounts", None))
        protect_all(selected, workers=args.workers)

    elif args.command == "unprotect":
        selected = get_selected(getattr(args, "accounts", None))
        unprotect_all(selected, workers=args.workers)


if __name__ == "__main__":
    main()
