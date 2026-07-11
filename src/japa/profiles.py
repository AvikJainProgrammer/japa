"""Voiceprint profiles — your own confirmed renditions of each mantra.

Training mode (--train) appends the IPA of renditions you confirm as
correct to voiceprints/<mantra-key>.txt (one per line). Chanting mode
auto-loads that file and matches against every saved rendition as well
as the built-in reference, so scoring adapts to your voice and accent.
The voiceprints/ directory is personal data and belongs in .gitignore.
"""

import re
import unicodedata
from pathlib import Path

DEFAULT_VOICEPRINTS_DIR = Path("voiceprints")


def slugify(text: str) -> str:
    """Stable file-safe key for a mantra or name's text.

    Diacritics are folded to plain ASCII (Durgā -> durga) so transliterated
    Sanskrit names produce readable filenames.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "custom"


def profile_path(voiceprints_dir: Path, key: str) -> Path:
    return Path(voiceprints_dir) / f"{key}.txt"


def load_profile(voiceprints_dir: Path, key: str) -> list[str]:
    """Return the saved IPA renditions for a mantra, oldest first."""
    path = profile_path(voiceprints_dir, key)
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def append_to_profile(voiceprints_dir: Path, key: str, ipa: str) -> Path:
    """Append one confirmed rendition; returns the profile path."""
    path = profile_path(voiceprints_dir, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(ipa.strip() + "\n")
    return path
