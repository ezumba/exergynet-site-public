#!/usr/bin/env python3
"""Deterministic shared-chrome synchronization for exergynet-ui.css static pages."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTIALS = ROOT / "partials"

PAGES = {
    "index.html": "index.html#platform",
    "exergycode.html": "exergycode.html",
    "studio.html": "studio.html",
    "legal.html": "legal.html",
    "intellectual-property.html": "intellectual-property.html",
}

BLOCKS = [
    ("HEADER", "ui-header.html"),
    ("FOOTER", "ui-footer.html"),
    ("SEARCH", "ui-search-dialog.html"),
]


def render_header(template: str, active_href: str) -> str:
    def _add_current(match: re.Match[str]) -> str:
        attrs, href, label = match.group(1), match.group(2), match.group(3)
        if href == active_href:
            return f'<a{attrs} href="{href}" aria-current="page">{label}</a>'
        return f'<a{attrs} href="{href}">{label}</a>'

    nav_pattern = re.compile(
        r'(<nav class="navlinks" id="navlinks"[^>]*>)(.*?)(</nav>)',
        re.DOTALL,
    )

    def _replace_nav(nav_match: re.Match[str]) -> str:
        prefix, body, suffix = nav_match.groups()
        body = re.sub(
            r'<a([^>]*) href="([^"]+)"(?: aria-current="page")?>(.*?)</a>',
            _add_current,
            body,
        )
        return f"{prefix}{body}{suffix}"

    return nav_pattern.sub(_replace_nav, template, count=1)


def sync_file(page_name: str, active_href: str, check_only: bool) -> bool:
    page_path = ROOT / page_name
    raw = page_path.read_text(encoding="utf-8")
    # Normalize CRLF to LF for deterministic processing and clean git objects
    content = raw.replace("\r\n", "\n")

    updated = content
    for tag, partial_name in BLOCKS:
        partial_text = (PARTIALS / partial_name).read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
        if tag == "HEADER":
            partial_text = render_header(partial_text, active_href)

        start_marker = f"<!-- CANONICAL:{tag}:START -->"
        end_marker = f"<!-- CANONICAL:{tag}:END -->"
        pattern = re.compile(
            re.escape(start_marker) + r".*?" + re.escape(end_marker),
            re.DOTALL,
        )
        replacement = f"{start_marker}\n{partial_text}\n{end_marker}"
        if not pattern.search(updated):
            raise RuntimeError(f"Missing markers {start_marker}..{end_marker} in {page_name}")
        updated = pattern.sub(replacement, updated, count=1)

    if updated != raw:
        if check_only:
            print(f"DRIFT: {page_name} is out of sync with canonical partials", file=sys.stderr)
            return False
        page_path.write_bytes(updated.encode("utf-8"))
        print(f"SYNCED: {page_name}")
    else:
        print(f"OK: {page_name}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify sync without modifying files")
    args = parser.parse_args()

    all_ok = True
    for page_name, active_href in PAGES.items():
        if not sync_file(page_name, active_href, args.check):
            all_ok = False
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
