"""DevFlow premium license verification.

Offline-capable license gate. A premium command calls `require_premium(key)`
first. We verify a license key locally without phoning home on every run:

  - Format: KRYP-XXXX-XXXX-XXXX-XXXX (groups of 4 hex/upper-alnum)
  - Checksum: the final group is a CRC32 of the concatenated first four
    groups, uppercased base36. This makes keys self-validating and
    tamper-evident without a server.

If no key is supplied we fall back to a local `~/.config/devflow/license`
file (written by `devflow activate <key>`). If neither exists we print a
clear upsell and return False — never silently faking a feature.

This is deliberately lightweight: it proves genuine purchase intent, gates
premium atoms behind a real key, and avoids a brittle per-run network call.
"""

from __future__ import annotations

import binascii
import re
from pathlib import Path

LICENSE_DIR = Path.home() / ".config" / "devflow"
LICENSE_FILE = LICENSE_DIR / "license"
KEY_RE = re.compile(r"^KRYP-[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}$")
GUMROAD_URL = "https://kryptorious.gumroad.com/l/jbvet"


def _checksum_groups(groups: list[str]) -> str:
    payload = "".join(groups).encode("utf-8")
    crc = binascii.crc32(payload) & 0xFFFFFFFF
    # base36 of crc, uppercased, zero-padded to 4
    return _to_base36(crc).upper().zfill(4)[-4:]


def _to_base36(n: int) -> str:
    if n == 0:
        return "0"
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    out = ""
    while n:
        out = digits[n % 36] + out
        n //= 36
    return out


def is_valid_key(key: str) -> bool:
    key = (key or "").strip().upper()
    if not KEY_RE.match(key):
        return False
    parts = key.split("-")  # ['KRYP', g1, g2, g3, g4]
    if len(parts) != 5:
        return False
    payload_groups = parts[1:-1]
    expected = _checksum_groups(payload_groups)
    return expected == parts[-1]


def _read_stored() -> str | None:
    try:
        if LICENSE_FILE.exists():
            return LICENSE_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    return None


def require_premium(key: str | None = None) -> bool:
    """Return True if premium is unlocked; print upsell + return False otherwise."""
    candidate = (key or "").strip() or _read_stored() or ""
    if is_valid_key(candidate):
        return True
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    console.print()
    console.print(Panel(
        "[bold]DevFlow Premium required[/bold]\n\n"
        "This command generates production multi-environment configs, approval "
        "gates, and infrastructure-as-code templates — premium features.\n\n"
        f"[cyan]{GUMROAD_URL}[/cyan]\n\n"
        "Activate with: [green]devflow activate &lt;YOUR_KEY&gt;[/green]",
        border_style="yellow",
    ))
    return False


def activate(key: str) -> bool:
    """Validate and persist a license key. Returns success."""
    if not is_valid_key(key):
        return False
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(key.strip().upper(), encoding="utf-8")
    return True
