from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
ICON_ROOT = ROOT / "assets" / "icons" / "material-symbols"
MANIFEST = ROOT / "third_party" / "material-symbols-manifest.json"
MATERIAL_SHA = "abd7f5c0e179c83f068c770650bd14ebac5d5a09"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_manifest() -> dict[str, object]:
    icons = []
    for path in sorted(ICON_ROOT.glob("*.svg")):
        name = path.stem
        icons.append(
            {
                "name": name,
                "style": "materialsymbolsoutlined",
                "source_path": f"symbols/web/{name}/materialsymbolsoutlined/{name}_24px.svg",
                "source_sha": MATERIAL_SHA,
                "local_sha256": digest(path),
                "use_location": "Track it menus, toolbars, dialogs, status, and workspace",
            }
        )
    return {
        "schema_version": 1,
        "upstream": "https://github.com/google/material-design-icons",
        "commit": MATERIAL_SHA,
        "icons": icons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    expected = expected_manifest()
    if args.write:
        MANIFEST.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    elif not MANIFEST.exists() or json.loads(MANIFEST.read_text(encoding="utf-8")) != expected:
        raise SystemExit("Material Symbol manifest does not match bundled SVG hashes.")
    upstreams = json.loads(
        (ROOT / "third_party" / "upstreams.lock.json").read_text(encoding="utf-8")
    )
    for name, item in upstreams["upstreams"].items():
        if not re.fullmatch(r"[0-9a-f]{40}", item["commit"]):
            raise SystemExit(f"Invalid upstream commit for {name}")
    required = [
        ROOT / "LICENSE",
        ROOT / "assets/fonts/OFL-HostGrotesk.txt",
        ROOT / "assets/fonts/OFL-JetBrainsMono.txt",
        ROOT / "third_party/licenses/Material-Symbols-LICENSE.txt",
    ]
    missing = [str(path) for path in required if not path.exists() or not path.stat().st_size]
    if missing:
        raise SystemExit(f"Missing license assets: {missing}")
    print(
        f"Verified {len(expected['icons'])} Material Symbols and {len(upstreams['upstreams'])} pinned upstreams."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
