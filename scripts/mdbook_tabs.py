#!/usr/bin/env python3
"""Minimal mdbook preprocessor that converts tab blocks to HTML.

Installed as a preprocessor in book.toml:

    [preprocessor.tabs]
    command = "python3 ./mdbook_tabs.py"

Two equivalent syntaxes are supported:

1. MkDocs Material syntax (preferred — kept verbatim in source files):

    === "Tab 1"

        content (any markdown, indented 4 spaces)

    === "Tab 2"

        content

   A tab group is a maximal run of consecutive `=== "..."` lines at column 0.
   Tab content is any indented (≥4 spaces) or blank line that follows the
   header until the next header or an un-indented non-blank line.

2. Explicit mdbook syntax (legacy — produced by the old convert_mkdocs.py):

    {{#tabs }}
    {{#tab name="Tab 1" }}
    content (any markdown)
    {{#endtab }}
    {{#tab name="Tab 2" }}
    content
    {{#endtab }}
    {{#endtabs }}

   Global tabs (same name = same active selection across all containers):

    {{#tabs global="example" }}
    ...
    {{#endtabs }}

HTML output uses .mdbook-tabs-container / .mdbook-tabs / .mdbook-tab /
.mdbook-tab-content classes (matched by theme/css/tabs.css + theme/js/tabs.js).

Content is kept as raw markdown surrounded by blank lines so that mdbook's
CommonMark renderer (pulldown-cmark) processes it normally (fenced code blocks
get syntax-highlighted, etc.).
"""
import json
import re
import sys
import textwrap

# ---- regex patterns -------------------------------------------------------

# Matches an entire {{#tabs ...}} ... {{#endtabs}} block.
# The content may span many lines, so re.DOTALL is required.
_TABS_RE = re.compile(
    r'\{\{#tabs(?:\s+global="(?P<global>[^"]*)")?\s*\}\}'
    r'(?P<inner>.*?)'
    r'\{\{#endtabs\s*\}\}',
    re.DOTALL,
)

# Matches a single {{#tab name="..."}} ... {{#endtab}} inside the outer block.
_TAB_RE = re.compile(
    r'\{\{#tab\s+name="(?P<name>[^"]*)"\s*\}\}'
    r'(?P<body>.*?)'
    r'\{\{#endtab\s*\}\}',
    re.DOTALL,
)

# Matches a MkDocs Material tab header: === "Tab name"
_MKDOCS_HEADER_RE = re.compile(r'^={3} "(.+)"$')


# ---- MkDocs tab conversion ------------------------------------------------

def _convert_mkdocs_tabs(content: str) -> str:
    """Convert MkDocs Material === "..." tab groups to {{#tabs}} syntax.

    A group is a maximal sequence of === "..." blocks at column 0.  Each
    tab's body is the indented (≥4 spaces) or blank lines that immediately
    follow the header, dedented by 4 spaces.
    """
    lines = content.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = _MKDOCS_HEADER_RE.match(lines[i].rstrip("\n"))
        if not m:
            out.append(lines[i])
            i += 1
            continue

        # Collect all consecutive tabs in this group.
        tabs: list[tuple[str, str]] = []
        while i < len(lines):
            hdr = _MKDOCS_HEADER_RE.match(lines[i].rstrip("\n"))
            if not hdr:
                break
            name = hdr.group(1)
            i += 1  # consume the === line

            body_lines: list[str] = []
            while i < len(lines):
                raw = lines[i].rstrip("\n")
                if raw == "":
                    body_lines.append("")
                    i += 1
                elif raw.startswith("    "):
                    body_lines.append(raw[4:])  # dedent 4 spaces
                    i += 1
                else:
                    break

            # Strip leading/trailing blank lines from the body.
            while body_lines and body_lines[0] == "":
                body_lines.pop(0)
            while body_lines and body_lines[-1] == "":
                body_lines.pop()

            tabs.append((name, "\n".join(body_lines)))

        # Emit the {{#tabs}} block.
        out.append("{{#tabs }}\n")
        for name, body in tabs:
            out.append(f'{{{{#tab name="{name}" }}}}\n')
            if body:
                out.append(body + "\n")
            out.append("\n")
            out.append("{{#endtab }}\n")
        out.append("{{#endtabs }}\n")

    return "".join(out)


# ---- {{#tabs}} → HTML conversion ------------------------------------------

def _tabs_to_html(match: re.Match) -> str:
    global_name = match.group("global")
    inner = match.group("inner")

    tabs = _TAB_RE.findall(inner)  # list of (name, body)
    if not tabs:
        return match.group(0)  # nothing to do

    container_attrs = 'class="mdbook-tabs-container"'
    if global_name:
        container_attrs += f' data-tabglobal="{global_name}"'

    # --- nav bar ---
    nav_buttons = []
    for i, (name, _body) in enumerate(tabs):
        extra = " active" if i == 0 else ""
        nav_buttons.append(
            f'<button class="mdbook-tab{extra}" data-tabname="{name}">{name}</button>'
        )
    nav = "<nav class=\"mdbook-tabs\">\n" + "\n".join(nav_buttons) + "\n</nav>"

    # --- content panels ---
    # Surround each tab body with blank lines so that pulldown-cmark renders
    # the markdown content (fenced code blocks, etc.) instead of treating it
    # as raw HTML.
    panels = []
    for i, (name, body) in enumerate(tabs):
        hidden = " hidden" if i > 0 else ""
        # textwrap.dedent strips any residual common leading whitespace.
        body_clean = textwrap.dedent(body.strip("\n")).strip()
        panel = (
            f'<div class="mdbook-tab-content{hidden}" data-tabname="{name}">\n'
            f'\n'
            f'{body_clean}\n'
            f'\n'
            f'</div>'
        )
        panels.append(panel)

    return (
        f"<div {container_attrs}>\n"
        f"{nav}\n"
        + "\n".join(panels)
        + "\n</div>"
    )


def convert_content(content: str) -> str:
    # Step 1: normalise MkDocs === "..." groups to {{#tabs}} syntax.
    if '=== "' in content:
        content = _convert_mkdocs_tabs(content)
    # Step 2: render {{#tabs}} blocks to HTML.
    return _TABS_RE.sub(_tabs_to_html, content)


# ---- mdbook preprocessor protocol ----------------------------------------

def process_chapter(chapter: dict) -> None:
    if chapter.get("content"):
        chapter["content"] = convert_content(chapter["content"])
    for item in chapter.get("sub_items", []):
        if isinstance(item, dict) and "Chapter" in item:
            process_chapter(item["Chapter"])


def main() -> None:
    # mdbook calls preprocessors with "supports <renderer>" to check support.
    if len(sys.argv) > 1 and sys.argv[1] == "supports":
        sys.exit(0)  # 0 = yes, we support it

    data = json.load(sys.stdin)
    _ctx, book = data[0], data[1]

    for section in book.get("sections", []):
        if isinstance(section, dict) and "Chapter" in section:
            process_chapter(section["Chapter"])

    print(json.dumps(book))


if __name__ == "__main__":
    main()
