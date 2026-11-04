"""The skill is MIT licensed, and the license travels with the folder that is uploaded (rasrs/)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_repository_and_the_uploaded_skill_folder_carry_the_same_mit_license():
    root, skill = ROOT / "LICENSE", ROOT / "rasrs" / "LICENSE"
    assert root.is_file() and skill.is_file()
    assert root.read_text(encoding="utf-8") == skill.read_text(encoding="utf-8")
    text = root.read_text(encoding="utf-8")
    assert text.startswith("MIT License") and "Permission is hereby granted, free of charge" in text


def test_the_skill_header_names_the_license():
    header = (ROOT / "rasrs" / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
    assert "\nlicense: MIT" in header
