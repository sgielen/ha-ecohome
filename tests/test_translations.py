"""All translation files must have the same keys and placeholders as en.json."""
import json
import re
from pathlib import Path

import pytest

import custom_components.ecohome as integration

TRANSLATIONS = Path(integration.__file__).parent / "translations"


def _flatten(tree: dict, prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in tree.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat


def _placeholders(text: str) -> set[str]:
    return set(re.findall(r"{(\w+)}", text))


ENGLISH = _flatten(json.loads((TRANSLATIONS / "en.json").read_text()))
OTHER_LANGUAGES = sorted(p for p in TRANSLATIONS.glob("*.json") if p.name not in ("en.json", "strings.json"))


def test_strings_json_is_english():
    assert _flatten(json.loads((TRANSLATIONS / "strings.json").read_text())) == ENGLISH


@pytest.mark.parametrize("path", OTHER_LANGUAGES, ids=lambda p: p.stem)
def test_same_keys_and_placeholders_as_english(path):
    translated = _flatten(json.loads(path.read_text()))
    assert set(translated) == set(ENGLISH)
    for key, text in ENGLISH.items():
        assert _placeholders(translated[key]) == _placeholders(text), key


def test_dutch_is_present():
    assert TRANSLATIONS / "nl.json" in OTHER_LANGUAGES
