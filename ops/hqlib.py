#!/usr/bin/env python3
"""Shared helpers for the headquarters scripts.

This module has no third-party dependencies. It contains:

* a small, strict reader for the subset of YAML that headquarters files use,
* helpers that find the headquarters folder and read the registry (hq.yaml),
* a helper that pulls one fenced YAML block out of a Markdown file.

The YAML reader accepts plain mappings, lists, quoted and unquoted text,
whole numbers, true/false, null, empty [] and {}, one-line lists such as
[a, b], and long text written with > or |. It refuses anything else (anchors,
tags, tabs, yes/no booleans, nested one-line structures) with a message that
names the line, so a typo never turns into a silent misreading.

Run `python3 ops/hqlib.py repos` to print the registered repositories as
tab-separated lines. ops/status_all.sh uses that output.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REGISTRY_FILE = "hq.yaml"


class HQError(Exception):
    """A problem a person needs to fix before a script can run."""


class YamlSubsetError(HQError):
    """The text is not in the YAML subset headquarters files use."""

    def __init__(self, message: str, line: Optional[int] = None, source: str = "") -> None:
        where = ""
        if source and line:
            where = f"{source}, line {line}: "
        elif line:
            where = f"line {line}: "
        elif source:
            where = f"{source}: "
        super().__init__(f"{where}{message}")


# ---------------------------------------------------------------------------
# YAML subset reader
# ---------------------------------------------------------------------------

_KEY_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):(?:\s+(.*))?$")
_INT_RE = re.compile(r"^[-+]?(0|[1-9][0-9]*)$")
_FLOAT_RE = re.compile(r"^[-+]?[0-9]+\.[0-9]+$")
_LEADING_ZERO_RE = re.compile(r"^[-+]?0[0-9]+$")
_NULLS = {"null", "Null", "NULL", "~"}
_TRUES = {"true", "True", "TRUE"}
_FALSES = {"false", "False", "FALSE"}
_AMBIGUOUS_BOOLS = {"yes", "no", "on", "off", "Yes", "No", "On", "Off", "YES", "NO", "ON", "OFF"}
_FORBIDDEN_STARTS = ("&", "*", "!", "%", "@", "`", "{", "|", ">")


class _Line:
    __slots__ = ("number", "indent", "text")

    def __init__(self, number: int, indent: int, text: str) -> None:
        self.number = number
        self.indent = indent
        self.text = text


def _strip_comment(value: str) -> str:
    """Remove a trailing ` # comment` from unquoted text."""
    for index, char in enumerate(value):
        if char == "#" and (index == 0 or value[index - 1] in " \t"):
            return value[:index].rstrip()
    return value.rstrip()


def _parse_quoted(value: str, line: int, source: str) -> Tuple[str, str]:
    """Parse a quoted string at the start of value. Return (text, remainder)."""
    quote = value[0]
    out: List[str] = []
    index = 1
    while index < len(value):
        char = value[index]
        if quote == "'":
            if char == "'":
                if index + 1 < len(value) and value[index + 1] == "'":
                    out.append("'")
                    index += 2
                    continue
                return "".join(out), value[index + 1 :]
            out.append(char)
            index += 1
            continue
        if char == "\\":
            if index + 1 >= len(value):
                break
            escape = value[index + 1]
            mapping = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "/": "/"}
            if escape not in mapping:
                raise YamlSubsetError(
                    f"unsupported escape \\{escape} inside double quotes", line, source
                )
            out.append(mapping[escape])
            index += 2
            continue
        if char == '"':
            return "".join(out), value[index + 1 :]
        out.append(char)
        index += 1
    raise YamlSubsetError("a quoted value is missing its closing quote", line, source)


def _split_flow_items(inner: str, line: int, source: str) -> List[str]:
    items: List[str] = []
    current: List[str] = []
    quote: Optional[str] = None
    for char in inner:
        if quote:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
            current.append(char)
            continue
        if char in "[]{}":
            raise YamlSubsetError(
                "lists inside one-line lists are not supported; write one item per line",
                line,
                source,
            )
        if char == ",":
            items.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if quote:
        raise YamlSubsetError("a quoted value is missing its closing quote", line, source)
    last = "".join(current).strip()
    if last:
        items.append(last)
    elif items:
        raise YamlSubsetError("a one-line list ends with a comma", line, source)
    if any(item == "" for item in items):
        raise YamlSubsetError("a one-line list has an empty item", line, source)
    return items


def _parse_scalar(raw: str, line: int, source: str) -> Any:
    value = raw.strip()
    if not value:
        return None
    if value[0] in ("'", '"'):
        text, rest = _parse_quoted(value, line, source)
        if _strip_comment(rest).strip():
            raise YamlSubsetError(
                "unexpected text after a quoted value", line, source
            )
        return text
    value = _strip_comment(value)
    if not value:
        return None
    if value.startswith("["):
        if not value.endswith("]"):
            raise YamlSubsetError("a one-line list is missing its closing ]", line, source)
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item, line, source) for item in _split_flow_items(inner, line, source)]
    if value == "{}":
        return {}
    if value.startswith(_FORBIDDEN_STARTS):
        raise YamlSubsetError(
            f"values starting with {value[0]!r} are not supported here; put the value in quotes",
            line,
            source,
        )
    if value.startswith("- ") or value == "-":
        raise YamlSubsetError("a list item cannot start on the same line as its key", line, source)
    if ": " in value or value.endswith(":"):
        raise YamlSubsetError(
            "this value contains ': ' — put the whole value in double quotes", line, source
        )
    if value in _NULLS:
        return None
    if value in _TRUES:
        return True
    if value in _FALSES:
        return False
    if value in _AMBIGUOUS_BOOLS:
        raise YamlSubsetError(
            f"'{value}' is ambiguous; write true or false (or quote it if you mean the word)",
            line,
            source,
        )
    if _LEADING_ZERO_RE.match(value):
        raise YamlSubsetError(
            f"'{value}' has a leading zero; put it in quotes", line, source
        )
    if _INT_RE.match(value):
        return int(value)
    if _FLOAT_RE.match(value):
        return float(value)
    return value


def _tokenize(text: str, source: str) -> List[_Line]:
    lines: List[_Line] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.rstrip()
        content = stripped.lstrip(" ")
        indent = len(stripped) - len(content)
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlSubsetError("tabs are not allowed for indentation; use spaces", number, source)
        lines.append(_Line(number, indent, stripped[indent:] if stripped else ""))
    return lines


class _Reader:
    def __init__(self, text: str, source: str) -> None:
        self.source = source
        self.lines = _tokenize(text, source)
        self.pos = 0

    # A "significant" line is not blank and not a whole-line comment.
    def _skip_insignificant(self) -> None:
        while self.pos < len(self.lines):
            text = self.lines[self.pos].text
            if text and not text.startswith("#"):
                return
            self.pos += 1

    def peek(self) -> Optional[_Line]:
        self._skip_insignificant()
        if self.pos < len(self.lines):
            return self.lines[self.pos]
        return None

    def error(self, message: str, line: Optional[_Line]) -> YamlSubsetError:
        return YamlSubsetError(message, line.number if line else None, self.source)

    def parse_document(self) -> Any:
        first = self.peek()
        if first is not None and first.text == "---":
            self.pos += 1
            first = self.peek()
        if first is None:
            return None
        if first.indent != 0:
            raise self.error("the first line must not be indented", first)
        value = self.parse_block(0)
        leftover = self.peek()
        if leftover is not None:
            raise self.error("unexpected indentation or text here", leftover)
        return value

    def parse_block(self, indent: int) -> Any:
        line = self.peek()
        assert line is not None
        if _is_item(line.text):
            return self.parse_sequence(indent)
        if _KEY_RE.match(line.text):
            return self.parse_mapping(indent)
        raise self.error(
            "expected 'key: value' or '- item' here", line
        )

    def parse_mapping(self, indent: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        while True:
            line = self.peek()
            if line is None or line.indent < indent:
                return result
            if line.indent > indent:
                raise self.error("unexpected indentation", line)
            if _is_item(line.text):
                if result:
                    raise self.error("a list item appeared where a key was expected", line)
                raise self.error("expected 'key: value' here", line)
            match = _KEY_RE.match(line.text)
            if not match:
                raise self.error(
                    "expected 'key: value'; keys use letters, numbers, '_', '-' or '.'",
                    line,
                )
            key, rest = match.group(1), match.group(2) or ""
            if key in _AMBIGUOUS_BOOLS or key in _TRUES or key in _FALSES or key in _NULLS:
                raise self.error(f"'{key}' cannot be used as a key; pick another name", line)
            if key in result:
                raise self.error(f"the key '{key}' appears twice", line)
            self.pos += 1
            result[key] = self.parse_value_after_key(line, indent, rest)

    def parse_value_after_key(self, line: _Line, indent: int, rest: str) -> Any:
        rest_clean = _strip_comment(rest).strip() if not rest.lstrip().startswith(("'", '"')) else rest.strip()
        if rest_clean in (">", ">-", "|", "|-"):
            return self.parse_block_scalar(indent, rest_clean)
        if rest_clean:
            value = _parse_scalar(rest, line.number, self.source)
            following = self.peek()
            if following is not None and following.indent > indent:
                raise self.error(
                    "unexpected indentation; for long text start the value with > on the key line",
                    following,
                )
            return value
        following = self.peek()
        if following is None:
            return None
        if following.indent > indent:
            return self.parse_block(following.indent)
        if following.indent == indent and _is_item(following.text):
            return self.parse_sequence(indent)
        return None

    def parse_block_scalar(self, indent: int, style: str) -> str:
        collected: List[Tuple[int, str]] = []
        block_indent: Optional[int] = None
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            if not line.text:
                collected.append((-1, ""))
                self.pos += 1
                continue
            if line.indent <= indent:
                break
            if block_indent is None:
                block_indent = line.indent
            if line.indent < block_indent:
                raise self.error("long text lines must line up with the first line", line)
            collected.append((line.indent, " " * (line.indent - block_indent) + line.text))
            self.pos += 1
        # Trailing blank lines do not belong to the text.
        while collected and collected[-1][0] == -1:
            collected.pop()
        if not collected:
            return ""
        texts = [text for _, text in collected]
        if style.startswith("|"):
            body = "\n".join(texts)
        else:
            parts: List[str] = []
            for index, text in enumerate(texts):
                if index == 0:
                    parts.append(text)
                    continue
                previous = texts[index - 1]
                if text == "":
                    parts.append("\n")
                elif previous == "":
                    parts.append(text)
                elif text.startswith(" ") or previous.startswith(" "):
                    parts.append("\n" + text)
                else:
                    parts.append(" " + text)
            body = "".join(parts)
        if style.endswith("-"):
            return body
        return body + "\n"

    def parse_sequence(self, indent: int) -> List[Any]:
        result: List[Any] = []
        while True:
            line = self.peek()
            if line is None or line.indent < indent:
                return result
            if line.indent > indent:
                raise self.error("unexpected indentation inside a list", line)
            if not _is_item(line.text):
                return result
            rest = line.text[1:].lstrip(" ")
            offset = len(line.text) - len(rest)
            self.pos += 1
            if not rest or rest.startswith("#"):
                following = self.peek()
                if following is None or following.indent <= indent:
                    result.append(None)
                else:
                    result.append(self.parse_block(following.indent))
                continue
            if _KEY_RE.match(rest) and not rest.startswith(("'", '"')):
                # "- key: value" starts a mapping whose keys sit at indent + offset.
                self.pos -= 1
                self.lines[self.pos] = _Line(line.number, indent + offset, rest)
                result.append(self.parse_mapping(indent + offset))
                continue
            if _is_item(rest):
                raise self.error("lists directly inside lists are not supported", line)
            value = _parse_scalar(rest, line.number, self.source)
            following = self.peek()
            if following is not None and following.indent > indent:
                raise self.error("unexpected indentation after a list item", following)
            result.append(value)


def _is_item(text: str) -> bool:
    return text == "-" or text.startswith("- ")


def parse_yaml(text: str, source: str = "") -> Any:
    """Parse text written in the headquarters YAML subset."""
    return _Reader(text, source).parse_document()


def load_yaml_file(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HQError(f"cannot read {path}: {exc.strerror or exc}") from exc
    return parse_yaml(text, str(path))


def extract_marked_yaml(text: str, start: str, end: str, source: str = "") -> str:
    """Return the fenced ```yaml block that sits between two marker comments."""
    if text.count(start) != 1 or text.count(end) != 1:
        raise HQError(
            f"{source or 'the file'} must contain the marker lines {start} and {end} exactly once"
        )
    block = text.split(start, 1)[1].split(end, 1)[0].strip()
    if not block.startswith("```yaml\n") or not block.endswith("```"):
        raise HQError(
            f"{source or 'the file'}: the text between the markers must be one ```yaml fenced block"
        )
    return block[len("```yaml\n") : -len("```")]


def load_marked_yaml(path: Path, start: str, end: str) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HQError(f"cannot read {path}: {exc.strerror or exc}") from exc
    block = extract_marked_yaml(text, start, end, str(path))
    # Report line numbers relative to the whole file.
    offset = text.split(start, 1)[0].count("\n") + text.split(start, 1)[1].split("```yaml\n", 1)[0].count("\n") + 1
    try:
        return parse_yaml(block, str(path))
    except YamlSubsetError as exc:
        message = str(exc)
        match = re.search(r"line (\d+)", message)
        if match:
            message = message.replace(
                f"line {match.group(1)}", f"line {int(match.group(1)) + offset}", 1
            )
        raise HQError(message) from exc


def git_env() -> Dict[str, str]:
    """The current environment minus GIT_* settings, for running git safely.

    When a script runs inside a git hook, variables such as GIT_DIR and
    GIT_INDEX_FILE point at the repository that owns the hook. Dropping them
    makes every git command act on the folder it was given, and nothing else.
    """
    clean = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    clean["GIT_OPTIONAL_LOCKS"] = "0"
    return clean


# ---------------------------------------------------------------------------
# Small value helpers shared by the validators
# ---------------------------------------------------------------------------


def is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def as_date(value: Any) -> Optional[dt.date]:
    if isinstance(value, dt.datetime):
        return None
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def parse_today(value: Optional[str]) -> dt.date:
    if not value:
        return dt.date.today()
    parsed = as_date(value)
    if parsed is None:
        raise HQError(f"--today must be a date written as YYYY-MM-DD, not '{value}'")
    return parsed


# ---------------------------------------------------------------------------
# Finding headquarters and reading the registry
# ---------------------------------------------------------------------------


def find_root(explicit: Optional[str] = None) -> Path:
    """Return the headquarters folder (the one that holds hq.yaml).

    Uses --root when given; otherwise the folder above ops/.
    """
    if explicit:
        root = Path(explicit).expanduser().resolve()
    else:
        root = Path(__file__).resolve().parent.parent
    if not (root / REGISTRY_FILE).is_file():
        raise HQError(
            f"no {REGISTRY_FILE} found in {root}. Pass --root with the headquarters folder."
        )
    return root


class Repo:
    def __init__(self, name: str, entry: Dict[str, Any], path: Path) -> None:
        self.name = name
        self.entry = entry
        self.path = path

    @property
    def rules_file(self) -> Optional[str]:
        value = self.entry.get("rules_file")
        return value if is_text(value) else None

    @property
    def deploys_from_main(self) -> Any:
        return self.entry.get("main_deploys_to_production")


def load_registry_data(root: Path) -> Dict[str, Any]:
    data = load_yaml_file(root / REGISTRY_FILE)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise HQError(f"{REGISTRY_FILE} must be a set of 'key: value' lines at the top level")
    return data


def repos_root(root: Path, data: Dict[str, Any]) -> Path:
    hq = data.get("hq")
    configured = hq.get("repos_root") if isinstance(hq, dict) else None
    if not is_text(configured):
        configured = ".."
    path = Path(os.path.expanduser(str(configured)))
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def registered_repos(root: Path, data: Optional[Dict[str, Any]] = None) -> List[Repo]:
    """Return every registered repo with its resolved path (which may not exist)."""
    if data is None:
        data = load_registry_data(root)
    repos = data.get("repos")
    if repos is None:
        return []
    if not isinstance(repos, dict):
        raise HQError(f"{REGISTRY_FILE}: 'repos' must be a set of named entries")
    base = repos_root(root, data)
    out: List[Repo] = []
    for name, entry in repos.items():
        if not isinstance(entry, dict):
            entry = {}
        configured = entry.get("path") if is_text(entry.get("path")) else name
        path = Path(os.path.expanduser(str(configured)))
        if not path.is_absolute():
            path = base / path
        out.append(Repo(name, entry, path.resolve()))
    return out


def find_repo(root: Path, name: str) -> Repo:
    for repo in registered_repos(root):
        if repo.name == name:
            return repo
    known = ", ".join(repo.name for repo in registered_repos(root)) or "none yet"
    raise HQError(f"'{name}' is not registered in {REGISTRY_FILE}. Registered repos: {known}")


DEPLOY_HINT_FILES = (
    "vercel.json", "netlify.toml", "render.yaml", "fly.toml", "Procfile",
    "app.yaml", "serverless.yml", "Dockerfile",
)


def _yaml_quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _readme_summary(repo: Path) -> str:
    for name in ("README.md", "README", "readme.md", "README.rst", "README.txt"):
        path = repo / name
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[:60]
        except OSError:
            return ""
        paragraph: List[str] = []
        for line in lines:
            text = line.strip()
            if paragraph and (not text or text.startswith(("#", "```", "|"))):
                break
            if not text or text.startswith(("#", "<", "!", "[", "```", "=", "-", "|")):
                continue
            paragraph.append(text)
        if paragraph:
            summary = " ".join(" ".join(paragraph).split())
            if len(summary) > 200:
                summary = summary[:197].rsplit(" ", 1)[0] + "..."
            return summary
    return ""


def discover(folder: Path, hq_root: Optional[Path] = None) -> str:
    """Draft registry entries for the git repositories directly inside folder.

    Read-only. The output is a draft for a person or agent to review; it
    deliberately leaves the release rule unanswered so the check fails until
    someone asks the operator.
    """
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise HQError(f"{folder} is not a folder")
    out = [f"# Draft entries for git repositories in {folder}", "# Review every line before copying it into hq.yaml.", "repos:"]
    found = 0
    for child in sorted(folder.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or not (child / ".git").exists():
            continue
        if hq_root is not None and child.resolve() == hq_root.resolve():
            continue
        found += 1
        summary = _readme_summary(child)
        rules = "AGENTS.md" if (child / "AGENTS.md").is_file() else None
        status = next((n for n in ("STATUS.md", "docs/STATUS.md") if (child / n).is_file()), None)
        hints = [n for n in DEPLOY_HINT_FILES if (child / n).exists()]
        workflows = child / ".github" / "workflows"
        if workflows.is_dir():
            for wf in sorted(workflows.glob("*.y*ml")):
                try:
                    if "deploy" in wf.read_text(encoding="utf-8", errors="replace").lower():
                        hints.append(f".github/workflows/{wf.name}")
                except OSError:
                    pass
        out.append(f"  {child.name}:")
        out.append(f"    path: {_yaml_quote(child.name)}")
        out.append(f"    purpose: {_yaml_quote(summary or 'Ask the operator what this repository is for.')}")
        out.append(f"    rules_file: {_yaml_quote(rules) if rules else 'null  # no AGENTS.md yet; offer the template'}")
        if status:
            out.append(f"    status_file: {_yaml_quote(status)}")
        hint = f"  # deploy hints: {', '.join(hints)}" if hints else "  # no deploy files found"
        out.append(f"    main_deploys_to_production: ask-the-operator{hint}")
    if not found:
        out.append("  # no git repositories found directly inside this folder")
    return "\n".join(out)


def _cli(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Registry helpers: 'repos' prints registered repos as tab-separated lines; 'discover FOLDER' drafts entries for the git repos in FOLDER.")
    parser.add_argument("command", choices=["repos", "discover"])
    parser.add_argument("folder", nargs="?", help="for discover: the folder that holds your repositories")
    parser.add_argument("--root", help="headquarters folder (default: the folder above ops/)")
    args = parser.parse_args(argv)
    try:
        if args.command == "discover":
            if not args.folder:
                raise HQError("discover needs the folder that holds your repositories")
            here = Path(args.root).expanduser().resolve() if args.root else Path(__file__).resolve().parent.parent
            print(discover(Path(args.folder), here))
            return 0
        root = find_root(args.root)
        for repo in registered_repos(root):
            deploys = repo.deploys_from_main
            if not isinstance(deploys, bool):
                release = "unknown"
            else:
                release = "main-deploys" if deploys else "no-auto-deploy"
            print(f"{repo.name}\t{repo.path}\t{release}")
    except HQError as exc:
        print(f"Problem: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
