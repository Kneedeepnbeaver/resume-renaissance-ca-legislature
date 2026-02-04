"""Contact info persistence and vCard import."""
import json
import re
from pathlib import Path
from typing import Optional

CONTACT_KEYS = ("my_name", "my_email", "my_phone", "my_address")


def get_contact_config_path() -> Path:
    """Path to persisted contact config."""
    return Path(__file__).resolve().parent.parent.parent / "config" / "contact.json"


def load_contact_config() -> dict[str, str]:
    """Load saved contact info from config/contact.json."""
    path = get_contact_config_path()
    if not path.exists():
        return {k: "" for k in CONTACT_KEYS}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: (data.get(k) or "") for k in CONTACT_KEYS}
    except Exception:
        return {k: "" for k in CONTACT_KEYS}


def save_contact_config(data: dict[str, str]) -> None:
    """Save contact info to config/contact.json."""
    path = get_contact_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    out = {k: (data.get(k) or "") for k in CONTACT_KEYS}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


def parse_vcard(vcf_content: str) -> dict[str, str]:
    """
    Parse vCard 3.0/4.0 content. Returns dict with my_name, my_email, my_phone, my_address.
    Handles folded lines (continuation with space/tab).
    """
    result = {k: "" for k in CONTACT_KEYS}

    # Unfold lines (RFC 2426: lines ending with CRLF+space continue)
    text = re.sub(r"\r?\n[ \t]", "", vcf_content)

    # FN = formatted name
    fn_match = re.search(r"FN:(.+?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if fn_match:
        result["my_name"] = fn_match.group(1).strip()

    # TEL
    tel_match = re.search(r"TEL[^:]*:(.+?)(?:\n[A-Z]|\n\n|$)", text, re.IGNORECASE | re.DOTALL)
    if tel_match:
        result["my_phone"] = re.sub(r"\s+", " ", tel_match.group(1).strip())

    # EMAIL
    email_match = re.search(r"EMAIL[^:]*:(.+?)(?:\n[A-Z]|\n\n|$)", text, re.IGNORECASE | re.DOTALL)
    if email_match:
        result["my_email"] = email_match.group(1).strip()

    # ADR (semicolon-separated: ;;;street;city;state;zip;country)
    adr_match = re.search(r"ADR[^:]*:(.+?)(?:\n[A-Z]|\n\n|$)", text, re.IGNORECASE | re.DOTALL)
    if adr_match:
        parts = [p.strip() for p in adr_match.group(1).split(";")]
        # Typically: pobox, ext, street, city, region, postal, country
        if len(parts) >= 7:
            street = parts[2] or ""
            city = parts[3] or ""
            state = parts[4] or ""
            zipcode = parts[5] or ""
            result["my_address"] = ", ".join(filter(None, [street, city, state, zipcode]))
        else:
            result["my_address"] = "; ".join(filter(None, parts))

    return result
