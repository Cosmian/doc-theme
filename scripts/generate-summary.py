#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate-summary.py  —  Unified mdBook assembler and SUMMARY.md generator.

Replaces migration/migrate.py and migration/build_standalone.py.

Modes
─────
  --combined          Assemble the combined aggregated book.
                      Expects docs/ to be pre-populated by assemble-docs.sh.
                      Writes src/ and src/SUMMARY.md.

  <doc_dir>           Build a standalone section.
                      Auto-detects format from doc_dir:
                        nav.yml present    → new format (no conversion needed)
                        mkdocs.yml present → old format (MkDocs→mdBook conversion)
                      Writes doc_dir/src/ and doc_dir/src/SUMMARY.md.
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# Markdown conversion — for old MkDocs-format tags
# ═══════════════════════════════════════════════════════════════

ADM_RE = re.compile(
    r'^(?P<indent> *)(?P<marker>!!!|\?\?\?\+?)\s*'
    r'(?P<type>[\w-]+)'
    r'(?:\s+(?:"(?P<title>[^"]*)"'
    r'|(?P<title_plain>[^"]\S.*?)))?\s*$')
TAB_RE = re.compile(r'^(?P<indent> *)===\s+"(?P<name>[^"]*)"\s*$')
FENCE_RE = re.compile(r'^(?P<indent> *)(?P<ticks>`{3,})(?P<rest>.*)$')
INCLUDE_RE = re.compile(r'\{!\s*(?P<path>[^!]+?)\s*!\}')
FENCE_ATTR_RE = re.compile(
    r'^(?P<pre> *`{3,}\s*[\w+.-]*)\s+.*(?:title=|hl_lines=|linenums=).*$')

TYPE_MAP = {
    'note': 'note',      'seealso': 'note',
    'abstract': 'abstract', 'summary': 'abstract', 'tldr': 'abstract',
    'info': 'info',      'todo': 'info',
    'tip': 'tip',        'hint': 'tip',        'important': 'tip',
    'success': 'success', 'check': 'success',  'done': 'success',
    'question': 'question', 'help': 'question', 'faq': 'question',
    'warning': 'warning', 'caution': 'warning', 'attention': 'warning',
    'failure': 'failure', 'fail': 'failure',   'missing': 'failure',
    'danger': 'danger',  'error': 'danger',
    'bug': 'bug',
    'example': 'example',
    'quote': 'quote',    'cite': 'quote',
}


def strip_front_matter(text: str) -> str:
    if text.startswith('---\n') or text.startswith('---\r\n'):
        lines = text.split('\n')
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                return '\n'.join(lines[i + 1:]).lstrip('\n')
    return text


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


def _emit_tabs(tabs: list[tuple[str, list[str]]]) -> list[str]:
    # Use mdbook-tabs compatible class names so that theme/css/tabs.css and
    # theme/js/tabs.js work without a separate preprocessor.
    out = ['<div class="mdbook-tabs-container">',
           '<nav class="mdbook-tabs">']
    for idx, (name, _) in enumerate(tabs):
        label = html.escape(name.replace('`', ''))
        active = ' active' if idx == 0 else ''
        out.append(
            f'<button class="mdbook-tab{active}" data-tabname="{label}">{label}</button>'
        )
    out.append('</nav>')
    for idx, (name, body) in enumerate(tabs):
        label = html.escape(name.replace('`', ''))
        hidden = ' hidden' if idx > 0 else ''
        out.extend(['', f'<div class="mdbook-tab-content{hidden}" data-tabname="{label}">', ''])
        out.extend(body)
        out.extend(['', '</div>'])
    out.extend(['', '</div>', ''])
    return out


def _fix_fence_line(line: str) -> str:
    m = FENCE_ATTR_RE.match(line)
    return m.group('pre') if m else line


def _fix_includes(line: str) -> str:
    def repl(m: re.Match) -> str:
        p = m.group('path').strip()
        if p.startswith('kms_clients/'):
            # Files inside kms_clients/ use section-prefixed includes:
            # {!kms_clients/file.md!} → {{#include file.md}}
            p = p[len('kms_clients/'):]
        elif p.startswith('../documentation/docs/'):
            # Corresponding pattern in old KMS server docs tags.
            p = p[len('../documentation/docs/'):]
        return '{{#include %s}}' % p
    return INCLUDE_RE.sub(repl, line)


def _gather_indented(lines: list[str], start: int, body_indent: int,
                     stop) -> tuple[list[str], int]:
    body: list[str] = []
    j = start
    n = len(lines)
    while j < n:
        ln = lines[j]
        if ln.strip() == '':
            body.append('')
            j += 1
            continue
        if stop is not None and stop(ln):
            break
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
        if fence_ticks:
            out.append(line)
            m = FENCE_RE.match(line)
            if m and len(m.group('ticks')) >= fence_ticks and not m.group('rest').strip():
                fence_ticks = 0
            i += 1
            continue
        fm = FENCE_RE.match(line)
        if fm:
            fence_ticks = len(fm.group('ticks'))
            out.append(_fix_fence_line(line))
            i += 1
            continue
        m_adm = ADM_RE.match(line)
        if m_adm:
            indent = len(m_adm.group('indent'))
            body_indent = indent + 4
            collapsible = m_adm.group('marker').startswith('???')
            body, j = _gather_indented(lines, i + 1, body_indent, stop=None)
            out.extend(_emit_admonish(m_adm.group('type'),
                                      m_adm.group('title') or m_adm.group('title_plain'),
                                      collapsible, _process(body)))
            i = j
            continue
        m_tab = TAB_RE.match(line)
        if m_tab:
            indent = len(m_tab.group('indent'))
            body_indent = indent + 4
            tabs: list[tuple[str, list[str]]] = []
            j = i
            while j < n:
                mt = TAB_RE.match(lines[j])
                if not (mt and len(mt.group('indent')) == indent):
                    break
                name = mt.group('name')
                stop = lambda ln, _ind=indent: bool(
                    TAB_RE.match(ln) and len(TAB_RE.match(ln).group('indent')) == _ind)
                body, j = _gather_indented(lines, j + 1, body_indent, stop=stop)
                tabs.append((name, _process(body)))
            out.extend(_emit_tabs(tabs))
            i = j
            continue
        if line.strip() == '[TOC]':
            i += 1
            continue
        if 'emgithub.com/embed-v2.js' in line:
            out.extend(['<div class="emgithub-embed">', line, '</div>'])
            i += 1
            continue
        out.append(_fix_includes(line))
        i += 1
    return out


def convert_markdown(text: str) -> str:
    text = strip_front_matter(text)
    return '\n'.join(_process(text.split('\n')))


# ═══════════════════════════════════════════════════════════════
# Nav loading
# ═══════════════════════════════════════════════════════════════

def _parse_nav_yml(text: str) -> list:
    """Stdlib-only parser for the nav.yml subset used by this project.

    Handles:
      nav:
        - Label: file.md
        - Section:
          - Sub: file.md

    No PyYAML required.
    """
    result: list = []
    stack: list = [(-1, result)]

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#') or stripped == '---':
            continue
        indent = len(line) - len(stripped)
        if stripped == 'nav:':
            continue
        if not stripped.startswith('- '):
            continue
        content = stripped[2:]
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
        key, sep, val = content.partition(':')
        if not sep:
            continue
        val = val.strip()
        if val:
            stack[-1][1].append({key.strip(): val})
        else:
            new_list: list = []
            stack[-1][1].append({key.strip(): new_list})
            stack.append((indent, new_list))

    return result


def load_nav_yml(path: Path) -> list:
    """Load nav list from a new-format nav.yml file (no external deps)."""
    return _parse_nav_yml(path.read_text())


def load_mkdocs_nav(path: Path) -> tuple[list, str]:
    """Load nav list and site name from an old-format mkdocs.yml file.

    Requires PyYAML (installed as a mkdocs dependency).
    """
    import yaml

    class _Loader(yaml.SafeLoader):
        pass

    _Loader.add_multi_constructor(
        'tag:yaml.org,2002:python/', lambda ldr, suffix, node: None)
    _Loader.add_multi_constructor('!', lambda ldr, suffix, node: None)
    data = yaml.load(path.read_text(), Loader=_Loader)
    return data['nav'], str(data.get('site_name', 'Documentation'))


def detect_format(doc_dir: Path) -> str:
    """Return 'new' if nav.yml present, 'old' if mkdocs.yml present."""
    if (doc_dir / 'nav.yml').exists():
        return 'new'
    if (doc_dir / 'mkdocs.yml').exists():
        return 'old'
    raise FileNotFoundError(
        f'Neither nav.yml nor mkdocs.yml found in {doc_dir}')


def load_nav(doc_dir: Path, fmt: str) -> list:
    if fmt == 'new':
        return load_nav_yml(doc_dir / 'nav.yml')
    nav, _ = load_mkdocs_nav(doc_dir / 'mkdocs.yml')
    return nav


# ═══════════════════════════════════════════════════════════════
# SUMMARY.md generation
# ═══════════════════════════════════════════════════════════════

def _summary_lines(items: list, src_dir: Path, prefix: str, depth: int,
                   missing: list[str]) -> list[str]:
    pad = '  ' * depth
    lines: list[str] = []
    for item in items:
        (title, value), = item.items()
        title = html.unescape(str(title)).strip()
        if isinstance(value, list):
            lines.append(f'{pad}- [{title}]()')
            lines.extend(_summary_lines(value, src_dir, prefix, depth + 1, missing))
        else:
            rel = str(value).strip()
            full_path = prefix + rel if prefix else rel
            if not (src_dir / full_path).exists():
                missing.append(full_path)
                continue
            lines.append(f'{pad}- [{title}]({full_path})')
    return lines


def build_summary_block(nav: list, src_dir: Path, prefix: str = '') -> list[str]:
    """Return SUMMARY.md lines for one section (no top-level section header).

    prefix: prepended to every file path, e.g. 'key_management_system/'.
    """
    missing: list[str] = []
    lines = _summary_lines(nav, src_dir, prefix, 0, missing)
    if missing:
        print(f'  WARNING: {len(missing)} nav targets missing (skipped):',
              file=sys.stderr)
        for p in missing:
            print(f'    - {p}', file=sys.stderr)
    return lines


def _write_default_book_toml(doc_dir: Path, title: str) -> None:
    """Write a standard book.toml for old-format (MkDocs-era) doc directories."""
    toml = f"""\
[book]
title = "{title}"
authors = ["Cosmian"]
language = "en"
src = "src"

[build]
build-dir = "book"
create-missing = false

[output.html]
default-theme = "light"
preferred-dark-theme = "navy"
site-url = "https://docs.cosmian.com/"
additional-css = ["theme/css/eviden.css", "theme/css/mdbook-admonish.css", "theme/css/tabs.css"]
additional-js = ["theme/mermaid.min.js", "theme/js/mermaid-init.js", "theme/js/tabs.js", "theme/js/theme-invert.js", "theme/js/version-switcher.js"]

[output.html.search]
enable = true

[output.html.fold]
enable = true
level = 1

[preprocessor.admonish]
command = "mdbook-admonish"
assets_version = "3.1.0"

[preprocessor.mermaid]
command = "mdbook-mermaid"
"""
    (doc_dir / 'book.toml').write_text(toml, encoding='utf-8')
    print(f'  wrote {doc_dir}/book.toml (generated for old-format tag)')


# ═══════════════════════════════════════════════════════════════
# Standalone mode  (python3 generate-summary.py <doc_dir>)
# ═══════════════════════════════════════════════════════════════

def build_standalone(doc_dir: Path) -> None:
    docs = doc_dir / 'docs'

    if not docs.exists():
        print(f'ERROR: {docs} not found', file=sys.stderr)
        sys.exit(1)

    fmt = detect_format(doc_dir)
    nav = load_nav(doc_dir, fmt)

    # For old-format (MkDocs-era) tags that pre-date the mdBook migration,
    # generate a standard book.toml so mdbook can build the worktree.
    book_toml_path = doc_dir / 'book.toml'
    if fmt == 'old' and not book_toml_path.exists():
        _, title = load_mkdocs_nav(doc_dir / 'mkdocs.yml')
        _write_default_book_toml(doc_dir, title)

    # Determine src directory (read from book.toml, default "src")
    src_rel = 'src'
    if book_toml_path.exists():
        m = re.search(r'^src\s*=\s*["\']([^"\']+)["\']',
                      book_toml_path.read_text(encoding='utf-8'), re.MULTILINE)
        if m:
            src_rel = m.group(1)
    src = doc_dir / src_rel
    in_place = src.resolve() == docs.resolve()

    if not in_place:
        # Copy docs/ → src/, then generate SUMMARY.md there
        if src.exists():
            shutil.rmtree(src)
        shutil.copytree(docs, src, symlinks=True)

        converted = 0
        for md in src.rglob('*.md'):
            original = md.read_text(encoding='utf-8', errors='replace')
            new_text = convert_markdown(original)
            if new_text != original:
                md.write_text(new_text, encoding='utf-8')
                converted += 1
        label = 'old/MkDocs' if fmt == 'old' else 'new/mdBook'
        print(f'  assembled ({label} format): {converted} .md files converted')
    else:
        # src == docs: write SUMMARY.md in-place, no copy needed
        print(f'  in-place mode (src = "{src_rel}"): generating SUMMARY.md only')

    lines = ['# Summary', ''] + build_summary_block(nav, src) + ['']
    (src / 'SUMMARY.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'  wrote {src}/SUMMARY.md')


# ═══════════════════════════════════════════════════════════════
# Combined mode  (python3 generate-summary.py --combined)
# ═══════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent.parent.parent  # public_documentation/

# Sections in display order.
# nav_source_rel: path to the directory containing nav.yml or mkdocs.yml,
#                 relative to ROOT.
# prefix:         directory name under docs/ / src/ where this section lives.
#                 Empty string for the root "Getting started" section.
SECTIONS: list[tuple[str, str, str]] = [
    # (display_title,           prefix,                 nav_source_rel)
    ('Getting started',        '',                     '.'),
    ('Key Management System',  'key_management_system', 'kms/documentation'),
    ('Eviden VM',              'eviden_vm',              'cosmian_vm/documentation'),
    ('Eviden AI',              'eviden_ai',              'cosmian_ai'),
    ('Eviden Enclave',         'eviden_enclave',         'cosmian_enclave'),
    ('Findex',                 'findex',                 'findex-server/documentation'),
]

# Directories under docs/ that are not documentation pages (build artefacts).
SKIP_TOP = {'cbom', 'sbom'}

# Specific download artefacts referenced from documentation pages.
_ARTIFACTS = [
    ('cbom/cbom.cdx.json',                   'cbom/cbom.cdx.json'),
    ('sbom/server/fips/static/bom.cdx.json', 'sbom/server/fips/static/bom.cdx.json'),
]


def build_combined() -> None:
    docs = ROOT / 'docs'
    src = ROOT / 'src'

    # ── Step 1: copy docs/ → src/ (skip cbom/sbom build artefacts)
    if src.exists():
        shutil.rmtree(src)
    src.mkdir()
    md_count = 0
    for entry in sorted(docs.iterdir()):
        if entry.name in SKIP_TOP:
            continue
        dest = src / entry.name
        if entry.is_dir():
            shutil.copytree(entry, dest, symlinks=True)
        else:
            shutil.copy2(entry, dest)
    for _ in src.rglob('*.md'):
        md_count += 1
    print(f'  copied docs/ -> src/  ({md_count} markdown files)')

    # ── Step 1b: strip YAML frontmatter AND convert MkDocs syntax from ALL
    #             copied .md files in one pass (covers root section and any
    #             section not separately listed in SECTIONS below).
    fm_stripped = 0
    converted_root = 0
    for md in src.rglob('*.md'):
        original = md.read_text(encoding='utf-8', errors='replace')
        after_fm = strip_front_matter(original)
        new_text = convert_markdown(after_fm)
        if original != after_fm:
            fm_stripped += 1
        if new_text != original:
            md.write_text(new_text, encoding='utf-8')
            converted_root += 1
    if fm_stripped:
        print(f'  stripped frontmatter from {fm_stripped} .md file(s)')
    if converted_root:
        print(f'  converted {converted_root} .md file(s) (MkDocs admonitions/tabs)')

    # ── Step 2: (legacy) per-section conversion for old-format (mkdocs.yml) sections.
    #   Step 1b above already converts ALL sections universally; this loop is
    #   retained only to emit per-section log output for old-format sections.
    for _, prefix, nav_source_rel in SECTIONS:
        if not prefix:
            continue
        nav_source = ROOT / nav_source_rel
        if not nav_source.exists():
            continue
        try:
            fmt = detect_format(nav_source)
        except FileNotFoundError:
            continue
        # No additional conversion needed — step 1b already handled everything.

    # ── Step 3: build combined SUMMARY.md
    summary_lines = ['# Summary', '']
    for top_title, prefix, nav_source_rel in SECTIONS:
        nav_source = ROOT / nav_source_rel
        if not nav_source.exists():
            print(f'  WARNING: nav source {nav_source_rel!r} not found, '
                  f'skipping "{top_title}"', file=sys.stderr)
            continue
        try:
            fmt = detect_format(nav_source)
        except FileNotFoundError:
            print(f'  WARNING: no nav file in {nav_source_rel!r}, '
                  f'skipping "{top_title}"', file=sys.stderr)
            continue

        nav = load_nav(nav_source, fmt)
        prefix_slash = prefix + '/' if prefix else ''
        block = build_summary_block(nav, src, prefix_slash)

        summary_lines.append(f'- [{top_title}]()')
        summary_lines.extend('  ' + ln if ln.strip() else ln for ln in block)
        summary_lines.append('')

    (src / 'SUMMARY.md').write_text('\n'.join(summary_lines), encoding='utf-8')
    print(f'  wrote src/SUMMARY.md')

    # ── Step 4: copy download artefacts referenced by documentation pages
    for src_rel, dst_rel in _ARTIFACTS:
        src_file = docs / src_rel
        dst_file = src / dst_rel
        if src_file.exists():
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            print(f'  copied artefact: {dst_rel}')


# ═══════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--combined', action='store_true',
        help='Build the combined aggregated book (reads all section nav files)')
    parser.add_argument(
        'doc_dir', nargs='?',
        help='Path to a documentation directory for standalone build')
    args = parser.parse_args()

    if args.combined:
        print('Building combined aggregated book ...')
        build_combined()
        print('Done.')
    elif args.doc_dir:
        doc_dir = Path(args.doc_dir).resolve()
        print(f'Building standalone: {doc_dir}')
        build_standalone(doc_dir)
        print('Done.')
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
