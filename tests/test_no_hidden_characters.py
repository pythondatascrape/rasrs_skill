"""No file in the skill contains invisible formatting characters.

Direction overrides (U+202A-U+202E, U+2066-U+2069), zero-width characters and other Unicode "format"
characters make text read differently from what it does ("Trojan Source"). A skill is text an agent
reads, so a scanner rejects any file holding one. Code that needs such a character (a list of them to
reject, a test sample) spells it as an escape, for example "\\u202e", which behaves the same.
"""

import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_tracked_file_contains_an_invisible_formatting_character():
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    hits = []
    for name in files:
        try:
            text = (ROOT / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # not text
        for n, line in enumerate(text.splitlines(), 1):
            found = sorted({f"U+{ord(c):04X}" for c in line if unicodedata.category(c) == "Cf"})
            if found:
                hits.append(f"{name}:{n} {' '.join(found)}")
    assert hits == [], hits
