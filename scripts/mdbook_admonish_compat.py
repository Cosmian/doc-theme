#!/usr/bin/env python3
"""mdBook preprocessor: MkDocs-style admonition → mdbook-admonish conversion.

Converts the MkDocs `!!!` / `???` admonition syntax to the fenced-code-block
syntax expected by mdbook-admonish, so that source files written in MkDocs
style render correctly without any prior migration step.

Syntax supported:

    !!! warning "Optional title"
        Body (indented by 4 spaces).

    ???+ note
        Collapsible (starts open). Body (indented by 4 spaces).

    ??? danger
        Collapsible (starts closed).

Output (mdbook-admonish fenced-code format):

    ```admonish warning title="Optional title"
    Body
    ```

Install in book.toml BEFORE the admonish preprocessor:

    [preprocessor.admonish_compat]
    command = "python3 ./theme/scripts/mdbook_admonish_compat.py"
    before = ["admonish"]
"""
from __future__ import annotations

import json
import re
import sys

# ── Regex patterns ─────────────────────────────────────────────────────────

ADM_RE = re.compile(
    r'^(?P<indent> *)(?P<marker>!!!|\?\?\?\+?)\s*'
    r'(?P<type>[\w-]+)'
    r'(?:\s+(?:"(?P<title>[^"]*)"'
    r'|(?P<title_plain>[^"]\S.*?)))?\s*$')

FENCE_RE = re.compile(r'^(?P<indent> *)(?P<ticks>`{3,})(?P<rest>.*)$')

TYPE_MAP = {
    'note': 'note',       'seealso': 'note',
    'abstract': 'abstract', 'summary': 'abstract', 'tldr': 'abstract',
    'info': 'info',       'todo': 'info',
    'tip': 'tip',         'hint': 'tip',        'important': 'tip',
    'success': 'success', 'check': 'success',   'done': 'success',
    'question': 'question', 'help': 'question', 'faq': 'question',
    'warning': 'warning', 'caution': 'warning', 'attention': 'warning',
    'failure': 'failure', 'fail': 'failure',    'missing': 'failure',
    'danger': 'danger',   'error': 'danger',
    'bug': 'bug',
    'example': 'example',
    'quote': 'quote',     'cite': 'quote',
}


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(' '))


def _max_backtick_run(lines: list[str]) -> int:
    best = 0
    for ln in lines:
        m = re.match(r'^ *(`{3,})', ln)
        if m:
            best = max(best, len(m.group(1)))
    return best


def _emit_admonish(atype: str, title: str | None, collapsible: bool,
                   body: list[str]) -> list[str]:
    directive = TYPE_MAP.get(atype.lower(), 'note')
    n = max(3, _max_backtick_run(body) + 1)
    fence = '`' * n
    header = f'{fence}admonish {directive}'
    if title is not None:
        clean = title.replace('`', '').replace('"', "'")
        header += f' title="{clean}"'
    if collapsible:
        header += ' collapsible=true'
    return [header, *body, fence, '']


def _gather_indented(lines: list[str], start: int,
                     body_indent: int) -> tuple[list[str], int]:
    body: list[str] = []
    j = start
    n = len(lines)
    while j < n:
        ln = lines[j]
        if ln.strip() == '':
            body.append('')
            j += 1
            continue
        if _indent_of(ln) >= body_indent:
            body.append(ln[body_indent:])
            j += 1
        else:
            break
    while body and body[-1] == '':
        body.pop()
    while body and body[0] == '':
        body.pop(0)
    return body, j


def _process(lines: list[str]) -> list[str]:
    out: list[str] = []
    i, n = 0, len(lines)
    fence_ticks = 0
    while i < n:
        line = lines[i]
        # Inside a fenced code block — pass through unchanged.
        if fence_ticks:
            out.append(line)
            m = FENCE_RE.match(line)
            if m and len(m.group('ticks')) >= fence_ticks and not m.group('rest').strip():
                fence_ticks = 0
            i += 1
            continue
        # Opening fence — track depth, pass through.
        fm = FENCE_RE.match(line)
        if fm:
            fence_ticks = len(fm.group('ticks'))
            out.append(line)
            i += 1
            continue
        # MkDocs admonition marker.
        m_adm = ADM_RE.match(line)
        if m_adm:
            indent = len(m_adm.group('indent'))
            body_indent = indent + 4
            collapsible = m_adm.group('marker').startswith('???')
            body, j = _gather_indented(lines, i + 1, body_indent)
            out.extend(_emit_admonish(
                m_adm.group('type'),
                m_adm.group('title') or m_adm.group('title_plain'),
                collapsible,
                _process(body),
            ))
            i = j
            continue
        out.append(line)
        i += 1
    return out


def convert_markdown(text: str) -> str:
    return '\n'.join(_process(text.split('\n')))


# ── mdBook preprocessor plumbing ───────────────────────────────────────────

def process_chapter(chapter: dict) -> None:
    if 'content' in chapter:
        chapter['content'] = convert_markdown(chapter['content'])
    for sub in chapter.get('sub_items', []):
        if isinstance(sub, dict) and 'Chapter' in sub:
            process_chapter(sub['Chapter'])


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == 'supports':
        sys.exit(0)  # 0 = we support this renderer

    data = json.load(sys.stdin)
    _ctx, book = data[0], data[1]

    for section in book.get('sections', []):
        if isinstance(section, dict) and 'Chapter' in section:
            process_chapter(section['Chapter'])

    print(json.dumps(book))


if __name__ == '__main__':
    main()
