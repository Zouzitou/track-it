from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parents[1]


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(ROOT / "assets/fonts/HostGrotesk-Variable.ttf"), size)


def _icon() -> Image.Image:
    scale = 4
    image = Image.new("RGBA", (256 * scale, 256 * scale), "#11151b")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (8 * scale, 8 * scale, 248 * scale, 248 * scale),
        radius=52 * scale,
        fill="#11151b",
        outline="#303846",
        width=8 * scale,
    )
    width = 13 * scale
    for points in (
        ((77, 64), (58, 64), (58, 102)),
        ((179, 64), (198, 64), (198, 102)),
        ((77, 192), (58, 192), (58, 154)),
        ((179, 192), (198, 192), (198, 154)),
    ):
        draw.line(
            [(x * scale, y * scale) for x, y in points],
            fill="#6d87ff",
            width=width,
            joint="curve",
        )
    draw.polygon(
        [(111 * scale, 92 * scale), (168 * scale, 128 * scale), (111 * scale, 164 * scale)],
        fill="#f2f5f8",
    )
    draw.line((47 * scale, 116 * scale, 47 * scale, 140 * scale), fill="#ff8278", width=9 * scale)
    draw.line((209 * scale, 116 * scale, 209 * scale, 140 * scale), fill="#43ceba", width=9 * scale)
    return image.resize((256, 256), Image.Resampling.LANCZOS)


def _branding(output: Path) -> None:
    icon = _icon()
    icon.save(output / "track-it.png")
    icon.save(
        output / "track-it.ico",
        sizes=[
            (16, 16),
            (20, 20),
            (24, 24),
            (32, 32),
            (40, 40),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        ],
    )

    banner = Image.new("RGB", (493, 58), "#f7f9fc")
    banner_draw = ImageDraw.Draw(banner)
    banner_draw.text((18, 6), "Track it", font=_font(25), fill="#171b23")
    banner_draw.text(
        (20, 35),
        "Local video masking and motion tracking",
        font=_font(11),
        fill="#5e6979",
    )
    banner.paste(icon.resize((52, 52), Image.Resampling.LANCZOS).convert("RGB"), (435, 3))
    banner.save(output / "wix-banner.bmp")

    dialog = Image.new("RGB", (493, 312), "#ffffff")
    dialog_draw = ImageDraw.Draw(dialog)
    dialog_draw.rectangle((0, 0, 164, 312), fill="#11151b")
    dialog.paste(icon.resize((112, 112), Image.Resampling.LANCZOS).convert("RGB"), (26, 46))
    dialog_draw.text((28, 181), "TRACK IT", font=_font(25), fill="#f2f5f8")
    dialog_draw.text((29, 216), "Private by design", font=_font(13), fill="#98a3b3")
    dialog_draw.line((29, 251, 135, 251), fill="#6d87ff", width=4)
    dialog_draw.line((29, 263, 100, 263), fill="#ff8278", width=4)
    dialog_draw.line((29, 275, 121, 275), fill="#43ceba", width=4)
    dialog.save(output / "wix-dialog.bmp")


def _license(output: Path) -> None:
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    escaped = text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
    lines = escaped.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    rtf = r"{\rtf1\ansi\deff0{\fonttbl{\f0 Segoe UI;}}\fs18 " + r"\par ".join(lines) + "}"
    (output / "license.rtf").write_text(rtf, encoding="ascii", errors="xmlcharrefreplace")


def _version_info(output: Path, version: str) -> None:
    parts = [int(value) for value in version.split("-")[0].split(".")[:3]]
    parts.extend([0] * (4 - len(parts)))
    dotted = ".".join(str(value) for value in parts)
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tuple(parts)}, prodvers={tuple(parts)}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'Track it Open Source'),
    StringStruct('FileDescription', 'Track it - local video masking and motion tracking'),
    StringStruct('FileVersion', '{dotted}'),
    StringStruct('InternalName', 'TrackIt'),
    StringStruct('LegalCopyright', 'Copyright 2026 Track it contributors'),
    StringStruct('OriginalFilename', 'TrackIt.exe'),
    StringStruct('ProductName', 'Track it'),
    StringStruct('ProductVersion', '{version}')
  ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)"""
    (output / "version-info.txt").write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    _branding(args.output)
    _license(args.output)
    _version_info(args.output, args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
