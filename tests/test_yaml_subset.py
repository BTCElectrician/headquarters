"""The small YAML reader accepts what headquarters files use and refuses the rest."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

import hqlib

STARTER = Path(__file__).resolve().parent.parent


def test_reads_mappings_lists_and_scalars():
    text = (
        "name: shop\n"
        "count: 3\n"
        "ratio: 1.5\n"
        "live: true\n"
        "hidden: false\n"
        "nothing: null\n"
        "empty_list: []\n"
        "empty_map: {}\n"
        "tags: [a, \"b c\", 4]\n"
        "quoted: \"has: a colon\"  # trailing comment\n"
        "single: 'it''s'\n"
        "items:\n"
        "  - one\n"
        "  - id: two\n"
        "    size: 2\n"
        "same_indent_list:\n"
        "- x\n"
        "- y\n"
    )
    assert hqlib.parse_yaml(text) == {
        "name": "shop",
        "count": 3,
        "ratio": 1.5,
        "live": True,
        "hidden": False,
        "nothing": None,
        "empty_list": [],
        "empty_map": {},
        "tags": ["a", "b c", 4],
        "quoted": "has: a colon",
        "single": "it's",
        "items": ["one", {"id": "two", "size": 2}],
        "same_indent_list": ["x", "y"],
    }


def test_reads_folded_and_literal_text():
    text = "a: >\n  first line\n  second line\n\n  new paragraph\nb: |-\n  keep\n  lines\nc: >-\n  no newline\n"
    assert hqlib.parse_yaml(text) == {
        "a": "first line second line\nnew paragraph\n",
        "b": "keep\nlines",
        "c": "no newline",
    }


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("a:\n\t- x\n", "tabs"),
        ("live: yes\n", "ambiguous"),
        ("on: 1\n", "cannot be used as a key"),
        ("a: &anchor 1\n", "not supported"),
        ("a: b: c\n", "double quotes"),
        ("a: 1\na: 2\n", "appears twice"),
        ("a: [x, [y]]\n", "one-line lists"),
        ("a: \"open\n", "closing quote"),
        ("a: 1\n  b: 2\n", "indentation"),
        ("a: 0755\n", "leading zero"),
        ("a: {b: 1}\n", "not supported"),
    ],
)
def test_refuses_what_it_cannot_read_safely(text, fragment):
    with pytest.raises(hqlib.YamlSubsetError) as error:
        hqlib.parse_yaml(text, "sample.yaml")
    assert fragment in str(error.value)
    assert "line" in str(error.value)


def _normalize(value):
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, dt.date):
        return value.isoformat()
    return value


def _shipped_yaml_texts():
    texts = [("hq.yaml", (STARTER / "hq.yaml").read_text())]
    texts.append(("example hq.yaml", (STARTER / "examples/three-repo-shop/hq/hq.yaml").read_text()))
    markers = [
        ("<!-- work-queue:start -->", "<!-- work-queue:end -->"),
        ("<!-- operator-decisions:start -->", "<!-- operator-decisions:end -->"),
    ]
    for folder in (STARTER / "docs", STARTER / "examples/three-repo-shop/hq/docs"):
        for path in folder.glob("*.md"):
            text = path.read_text().replace("{{TODAY}}", "2026-11-12")
            for start, end in markers:
                if start in text:
                    texts.append((str(path), hqlib.extract_marked_yaml(text, start, end)))
    return texts


SHIPPED = _shipped_yaml_texts()


@pytest.mark.parametrize("name, text", SHIPPED, ids=[Path(name).parent.name + "/" + Path(name).name for name, _ in SHIPPED])
def test_shipped_files_read_the_same_as_full_yaml(name, text):
    """If PyYAML happens to be installed, the subset must agree with it exactly."""
    yaml = pytest.importorskip("yaml")
    assert hqlib.parse_yaml(text, name) == _normalize(yaml.safe_load(text))
