# No invisible formatting characters in the skill (change record)

## What was flagged
A skill scan reported two "High" findings: "hidden characters in text an agent reads".
- `rasrs/scripts/check_remember.py:22` held the nine direction-override characters (U+202A-U+202E,
  U+2066-U+2069) as literal characters: the set `check_remember` rejects in a memory claim.
- `tests/test_check_remember.py:59` held a literal U+202E: the sample claim that proves the rejection.

Both were inside string literals and hid nothing. But a literal direction override can make code read
differently from what it does ("Trojan Source"), so a scanner rejects any file that holds one.

## What changed
- Both lines spell the characters as escapes (`"\u202a..."`, `"a\u202eb"`). Python reads them as the
  same characters: `BIDI` still holds the same nine, and the rejection test still passes.
- `tests/test_no_hidden_characters.py` (new): no tracked text file may contain a Unicode format
  character (category Cf: direction overrides, zero-width characters and the like). It checks every
  file, so a new one cannot slip back in.

## Method
RED commit `05de74d`: the new test was locked (`tests.sha256` in this folder). It failed on exactly
the two flagged lines. GREEN changed only those two lines; the locked test is unchanged.

## Verification
`uv run --with pytest pytest -q -p no:cacheprovider tests/`: 12 passed (11 before, plus the new one).
