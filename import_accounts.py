#!/usr/bin/env python3
"""
import_accounts.py
Batch dosyasını accounts.txt formatına dönüştürür ve ekler.

Batch formatı  : username:password:email:email_password:2fa:ct0:auth_token
accounts.txt   : username:password:email:auth_token:ct0
"""

import sys
import argparse
import random
import os
from pathlib import Path

ACCOUNTS_FILE = Path(os.environ.get("TWEETER_DATA_DIR", Path(__file__).parent)).expanduser() / "accounts.txt"

# ─── Renk Kodları ───
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    GRAY   = "\033[90m"


def parse_batch_line(line: str, line_num: int) -> dict | None:
    """
    Batch satırını parse eder.
    Beklenen format (7 alan, ':' ayraçlı):
      username : password : email : email_password : 2fa : ct0 : auth_token
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = line.split(":")
    if len(parts) != 7:
        print(f"  {C.YELLOW}⚠ Satır {line_num}: {len(parts)} alan bulundu (7 bekleniyor), atlanıyor{C.RESET}")
        return None

    return {
        "username":       parts[0],
        "password":       parts[1],
        "email":          parts[2],
        "email_password": parts[3],
        "twofa":          parts[4],
        "ct0":            parts[5],
        "auth_token":     parts[6],
    }


def fake_phone() -> str:
    """10 haneli sahte telefon numarası üretir (alan kodu + 9 rakam)."""
    return "0" + "".join([str(random.randint(0, 9)) for _ in range(9)])


def to_accounts_line(parsed: dict) -> str:
    """
    accounts.txt satırı üretir:
    username:password:phone:auth_token:ct0
    (telefon alanı sahte numara ile doldurulur)
    """
    return ":".join([
        parsed["username"],
        parsed["password"],
        fake_phone(),
        parsed["auth_token"],
        parsed["ct0"],
    ])


def load_existing_usernames(filepath: Path) -> set[str]:
    """Mevcut accounts.txt'deki kullanıcı adlarını döndürür (duplicate kontrolü)."""
    usernames = set()
    if not filepath.exists():
        return usernames
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("@"):
                line = line[1:]
            username = line.split(":")[0]
            usernames.add(username.lower())
    return usernames


def convert(
    batch_file: Path,
    output_file: Path,
    append: bool = True,
    skip_duplicates: bool = True,
    dry_run: bool = False,
):
    if not batch_file.exists():
        print(f"{C.RED}✗ Dosya bulunamadı: {batch_file}{C.RESET}")
        sys.exit(1)

    existing = load_existing_usernames(output_file) if skip_duplicates else set()

    parsed_lines = []
    skipped_dup  = 0
    skipped_fmt  = 0

    with open(batch_file, "r", encoding="utf-8") as f:
        for line_num, raw in enumerate(f, 1):
            parsed = parse_batch_line(raw, line_num)
            if parsed is None:
                skipped_fmt += 1
                continue

            if skip_duplicates and parsed["username"].lower() in existing:
                print(f"  {C.GRAY}↷ @{parsed['username']} zaten mevcut, atlanıyor{C.RESET}")
                skipped_dup += 1
                continue

            parsed_lines.append(parsed)
            existing.add(parsed["username"].lower())

    if not parsed_lines:
        print(f"\n{C.YELLOW}⚠ Eklenecek yeni hesap bulunamadı.{C.RESET}")
        return

    # Önizleme
    print(f"\n{C.BOLD}{C.CYAN}{'─' * 65}{C.RESET}")
    print(f"  {'#':<4} {'Kullanıcı Adı':<22} {'E-posta':<30}")
    print(f"{C.GRAY}  {'─' * 63}{C.RESET}")
    for i, p in enumerate(parsed_lines, 1):
        print(f"  {C.CYAN}{i:<4}{C.RESET} {p['username']:<22} {C.GRAY}{p['email']:<30}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'─' * 65}{C.RESET}")

    print(f"\n  Eklenecek : {C.GREEN}{len(parsed_lines)}{C.RESET}")
    print(f"  Duplicate : {C.YELLOW}{skipped_dup}{C.RESET}")
    print(f"  Hatalı fmt: {C.RED}{skipped_fmt}{C.RESET}")

    if dry_run:
        print(f"\n{C.YELLOW}[DRY-RUN] Dosyaya yazılmadı.{C.RESET}")
        return

    # Onay
    try:
        confirm = input(f"\n{C.CYAN}Devam edilsin mi? (e/h) ▸ {C.RESET}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{C.YELLOW}İptal edildi.{C.RESET}")
        return

    if confirm not in ("e", "evet", "y", "yes"):
        print(f"{C.YELLOW}İptal edildi.{C.RESET}")
        return

    mode = "a" if append and output_file.exists() else "w"
    with open(output_file, mode, encoding="utf-8") as f:
        if mode == "a":
            # Dosya boş değilse ve son satır newline ile bitmiyorsa ekle
            output_file_size = output_file.stat().st_size
            if output_file_size > 0:
                with open(output_file, "rb") as rb:
                    rb.seek(-1, 2)
                    if rb.read(1) != b"\n":
                        f.write("\n")
        for p in parsed_lines:
            f.write(to_accounts_line(p) + "\n")

    print(f"\n{C.GREEN}✓ {len(parsed_lines)} hesap '{output_file}' dosyasına eklendi.{C.RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch dosyasını accounts.txt formatına dönüştür",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python import_accounts.py batch.txt               # accounts.txt'ye ekle
  python import_accounts.py batch.txt -o custom.txt # Farklı dosyaya yaz
  python import_accounts.py batch.txt --overwrite   # Üzerine yaz (append değil)
  python import_accounts.py batch.txt --dry-run     # Sadece önizle, yazma
  python import_accounts.py batch.txt --no-skip     # Duplicate kontrolü yapma
        """
    )
    parser.add_argument("batch_file", help="Dönüştürülecek batch dosyası")
    parser.add_argument(
        "-o", "--output", default=str(ACCOUNTS_FILE),
        help=f"Çıktı dosyası (varsayılan: {ACCOUNTS_FILE})"
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Mevcut dosyayı silip yeniden yaz (varsayılan: append)"
    )
    parser.add_argument(
        "--no-skip", action="store_true",
        help="Duplicate kontrolü yapma"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Sadece önizle, dosyaya yazma"
    )

    args = parser.parse_args()

    print(f"\n{C.BOLD}{C.CYAN}▶ Batch → accounts.txt Dönüştürücü{C.RESET}")
    print(f"  Kaynak : {args.batch_file}")
    print(f"  Hedef  : {args.output}")
    print(f"  Mod    : {'üzerine yaz' if args.overwrite else 'sonuna ekle'}")

    convert(
        batch_file=Path(args.batch_file),
        output_file=Path(args.output),
        append=not args.overwrite,
        skip_duplicates=not args.no_skip,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
