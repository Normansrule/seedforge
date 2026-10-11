#!/usr/bin/env python3
"""docs/modules/*.md and website/public/data/modules.json from tools/modules_source.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from modules_source import MODULES  # noqa: E402

SECTIONS = [("purpose", "1. Purpose"), ("inputs", "2. Inputs"), ("outputs", "3. Outputs"), ("printed", "4. Printed components"),
            ("purchased", "5. Purchased components"), ("electronics", "6. Electronics"), ("software", "7. Software responsibility"),
            ("calibration", "8. Calibration method"), ("acceptance", "9. Acceptance criteria"), ("risks", "10. Known risks")]


def main():
    out = ROOT / "docs" / "modules"
    out.mkdir(parents=True, exist_ok=True)
    index = ["# Modules", "", "| module | name | phase | status |", "|---|---|---|---|"]
    for m in MODULES:
        lines = [f"# {m['id']} - {m['name']}", "", f"**Build phase:** {m['phase']}  |  **Status:** {m['status']}", ""]
        for key, title in SECTIONS:
            lines.append(f"## {title}")
            lines.append("")
            v = m[key]
            lines += [f"* {x}" for x in v] if isinstance(v, list) else [v]
            lines.append("")
        lines += ["## 11. CAD preview", ""]
        if m["cad"]:
            lines += [f"Interactive: the website module explorer loads `{m['cad']}`. Files: `hardware/cad/glb/{m['cad']}`, "
                      "STEP/STL/3MF of every part in `hardware/cad/`.", ""]
        else:
            lines += ["Parts only (no assembly yet): see `hardware/cad/manifest.csv`.", ""]
        lines += ["## 12. Assembly figure", "", f"![{m['name']}](../{m['figure']})", "",
                  "Figures are CAD renders, not photographs, and are not evidence that the module works.", ""]
        (out / f"{m['slug']}.md").write_text("\n".join(lines))
        index.append(f"| [{m['id']}]({m['slug']}.md) | {m['name']} | {m['phase']} | {m['status']} |")
    (out / "README.md").write_text("\n".join(index) + "\n")
    site = ROOT / "website" / "public" / "data"
    site.mkdir(parents=True, exist_ok=True)
    (site / "modules.json").write_text(json.dumps(MODULES, indent=1))
    print(f"{len(MODULES)} module docs")


if __name__ == "__main__":
    main()
