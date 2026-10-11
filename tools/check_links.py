#!/usr/bin/env python3
"""Check relative links and #anchors in every Markdown file (no network).

    python tools/check_links.py            # exit 1 on any broken link

External http(s) links are listed with --external but not fetched (CI has
no reason to depend on third-party uptime). archive/ is skipped: it is kept
unchanged on purpose.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"node_modules", ".git", "archive", "dist", "synthetic", ".pytest_cache"}
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
CODE_FENCE = re.compile(r"^```")


def slug(text: str) -> str:
    """GitHub-style heading anchor."""
    t = re.sub(r"`|\*|_(?=\w)|(?<=\w)_|\[|\]\([^)]*\)", "", text).strip().lower()
    t = re.sub(r"[^\w\- ]", "", t)
    return t.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    out, seen, fence = set(), {}, False
    for line in path.read_text(encoding="utf-8").splitlines():
        if CODE_FENCE.match(line):
            fence = not fence
            continue
        if fence:
            continue
        m = HEADING.match(line)
        if m:
            s = slug(m.group(2))
            n = seen.get(s, 0)
            out.add(s if n == 0 else f"{s}-{n}")
            seen[s] = n + 1
    return out


def md_files():
    for p in ROOT.rglob("*.md"):
        if not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            yield p


def main() -> int:
    show_ext = "--external" in sys.argv
    bad, external, n = [], set(), 0
    cache: dict[Path, set[str]] = {}
    for md in md_files():
        fence = False
        for ln, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            if CODE_FENCE.match(line):
                fence = not fence
            if fence:
                continue
            for target in LINK.findall(line):
                n += 1
                if target.startswith(("http://", "https://", "mailto:")):
                    external.add(target)
                    continue
                path_part, _, frag = target.partition("#")
                dest = md if not path_part else (md.parent / unquote(path_part)).resolve()
                if not dest.exists():
                    bad.append(f"{md.relative_to(ROOT)}:{ln}: missing {target}")
                    continue
                if frag and dest.suffix == ".md":
                    a = cache.setdefault(dest, anchors(dest))
                    if frag not in a:
                        bad.append(f"{md.relative_to(ROOT)}:{ln}: no anchor #{frag} in {dest.relative_to(ROOT)}")
    for b in bad:
        print(b)
    if show_ext:
        for e in sorted(external):
            print("external:", e)
    print(f"{n} links checked, {len(bad)} broken, {len(external)} external (not fetched)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
