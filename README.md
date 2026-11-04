# rasrs skill

A Claude Code skill for using [RASRS](https://github.com/pythondatascrape/rasrs), the project
memory served over MCP: recall before planning, cite and verify Atoms, remember evidence-backed
facts, and handle every disposition and error. The skill is the `rasrs/` folder.

| File | Does |
|---|---|
| `rasrs/SKILL.md` | The agent protocol, limits, dispositions and errors |
| `rasrs/scripts/check_remember.py` | Checks a `remember` request against the server's rules before it is sent |
| `rasrs/scripts/freshness.py` | Compares the evidence of a `recall` result with a checkout (fresh, moved, changed, missing, unknown) |
| `rasrs/scripts/status.py` | Summarizes the server's request log, including empty recalls by caller |

Python 3.10+, standard library only.

## Install

```sh
git clone git@github.com:pythondatascrape/rasrs_skill.git ~/dev/rasrs_skill
mv ~/.claude/skills/rasrs ~/.claude/skills/rasrs.old 2>/dev/null   # an earlier copy, if any
ln -s ~/dev/rasrs_skill/rasrs ~/.claude/skills/rasrs
```

`git -C ~/dev/rasrs_skill pull` then updates the skill in place.

## Keeping it current

`SKILL.md` names the rasrs commit it was synced with. When rasrs changes, re-read its
`docs/information/state_machine.md`, `docs/agent-integration.md`, `contracts/v2/policy-defaults.json`,
`contracts/v2/errors.json` and `internal/atom/validate.go`, update the skill and its tests, and
move the synced commit forward.

## Tests

```sh
uvx pytest -q
```
