"""Save generated outputs to files with versioning and history."""
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional


def _slugify(text: str) -> str:
    """Convert text to a safe filename slug."""
    if not text or not text.strip():
        return "output"
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug[:50] or "output"


def get_output_filename(output_type: str, job_title: str = "") -> str:
    """Return the filename that would be used for saving."""
    return get_output_filename_with_ext(output_type, job_title, "txt")


def get_output_filename_with_ext(
    output_type: str,
    job_title: str = "",
    ext: str = "txt",
    version: Optional[int] = None,
) -> str:
    """Return the filename that would be used for saving with an extension."""
    safe_ext = (ext or "txt").lstrip(".").lower()
    slug = _slugify(job_title) if job_title else "output"
    today = date.today().strftime("%Y-%m-%d")
    if output_type.lower() in ("resume",):
        prefix = "Resume"
    elif output_type.lower() in ("cover_letter", "coverletter", "cover-letter"):
        prefix = "CoverLetter"
    else:
        prefix = output_type.replace(" ", "").title() or "Output"
    base = f"{prefix}-{slug}-{today}"
    if version is not None and version > 1:
        return f"{base}-v{version}.{safe_ext}"
    return f"{base}.{safe_ext}"


def _next_version(outputs_dir: Path, output_type: str, job_title: str, ext: str) -> int:
    """Find next version number for same job+day. Returns 1 for first save, 2 for second, etc."""
    slug = _slugify(job_title) if job_title else "output"
    today = date.today().strftime("%Y-%m-%d")
    if output_type.lower() in ("resume",):
        prefix = "Resume"
    elif output_type.lower() in ("cover_letter", "coverletter", "cover-letter"):
        prefix = "CoverLetter"
    else:
        prefix = "Output"
    base = f"{prefix}-{slug}-{today}"
    safe_ext = (ext or "md").lstrip(".").lower()
    versions_found = []
    if (outputs_dir / f"{base}.{safe_ext}").exists():
        versions_found.append(1)
    for p in outputs_dir.glob(f"{base}-v*.{safe_ext}"):
        try:
            v = int(p.stem.split("-v")[-1])
            versions_found.append(v)
        except ValueError:
            pass
    return max(versions_found) + 1 if versions_found else 1


def get_history_path(outputs_dir: Path) -> Path:
    """Path to generation history JSON."""
    return Path(outputs_dir) / "history.json"


def load_history(outputs_dir: Path) -> list[dict]:
    """Load generation history."""
    path = get_history_path(outputs_dir)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def append_to_history(
    outputs_dir: Path,
    output_type: str,
    job_title: str,
    filepath: Path,
) -> None:
    """Append an entry to generation history."""
    outputs_dir = Path(outputs_dir)
    history = load_history(outputs_dir)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": output_type,
        "job_title": job_title,
        "filepath": str(filepath),
        "filename": filepath.name,
    }
    history.insert(0, entry)
    # Keep last 100 entries
    history = history[:100]
    path = get_history_path(outputs_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=0)


def save_output(
    content: str,
    output_type: str,
    job_title: str = "",
    outputs_dir: Optional[Path] = None,
    ext: str = "txt",
    auto_version: bool = True,
    append_history: bool = True,
) -> Path:
    """
    Save generated content with optional versioning (v1, v2 for same job+day).
    Auto-saves with version increment when file exists. Appends to history.
    Returns the path to the saved file.
    """
    if outputs_dir is None:
        outputs_dir = Path(__file__).resolve().parent.parent.parent / "generated"
    outputs_dir = Path(outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    safe_ext = (ext or "md").lstrip(".").lower()
    version = None
    if auto_version:
        v = _next_version(outputs_dir, output_type, job_title, safe_ext)
        if v > 1:
            version = v
    filename = get_output_filename_with_ext(output_type, job_title, safe_ext, version)
    filepath = outputs_dir / filename

    filepath.write_text(content, encoding="utf-8")

    if append_history:
        append_to_history(outputs_dir, output_type, job_title, filepath)

    return filepath
