r"""Labeled overview sheets and a gallery page for the matrix_states.py screenshots.

    ..\Order_Parser\.venv\Scripts\python.exe demos\matrix_sheets.py demos\out\matrix-light-states
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(sys.argv[1])
FONTS = Path(r"C:\Windows\Fonts")
TEXT = ImageFont.truetype(str(FONTS / "seguisym.ttf"), 17)  # has the badge glyphs (◐ ↻ ⚠ ⇄ ✕)
SECTION = ImageFont.truetype(str(FONTS / "segoeuib.ttf"), 19)
TITLE = ImageFont.truetype(str(FONTS / "segoeuib.ttf"), 26)
BG, INK, MUTED, RULE = (242, 244, 247), (23, 33, 47), (90, 101, 116), (206, 212, 221)
PAD, GAP = 28, 18

FINDINGS = [
    "The ⇄ in the sharing badge reads like “=” at this size. It is One Desk's sharing glyph (tokens.json), "
    "so a different glyph is a change to the Design package.",
    "Detail chart: the price above a B or S dot on the FV lane is drawn across the ANOM lane's rule line, "
    "so it reads like part of the ANOM row.",
]

ORDER = [
    "Studio windows",
    "Studio top bar: Schwab connection",
    "Studio top bar: authorization",
    "Studio top bar: recorder",
    "Studio top bar: sharing with the work PC",
    "Studio top bar: quote footprint line",
    "Viewer windows",
    "Viewer top bar: link to the mini PC",
    "Viewer top bar: relayed from the mini PC",
    "Dialogs",
    "Native Windows pop-ups",
    "Tooltips",
]


def load_items() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for name in ("manifest-studio.json", "manifest-viewer.json"):
        path = OUT / name
        if path.exists():
            items += json.loads(path.read_text(encoding="utf-8"))
    return [item for item in items if (OUT / item["file"]).exists()]


def wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) <= width or not line:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def line_height(font) -> int:
    ascent, descent = font.getmetrics()
    return ascent + descent + 3


def stack_sheet(title: str, sections: list[tuple[str, list[dict[str, str]]]], path: Path) -> None:
    """Crops one under another, each with its caption, grouped by section."""
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    images = {item["file"]: Image.open(OUT / item["file"]).convert("RGB") for _, items in sections for item in items}
    width = max(img.width for img in images.values()) + 2 * PAD
    height = PAD + line_height(TITLE) + GAP
    for _, items in sections:
        height += line_height(SECTION) + 8
        for item in items:
            height += line_height(TEXT) * len(wrap(probe, item["caption"], TEXT, width - 2 * PAD)) + 4
            height += images[item["file"]].height + GAP
        height += GAP
    sheet = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(sheet)
    y = PAD
    draw.text((PAD, y), title, font=TITLE, fill=INK)
    y += line_height(TITLE) + GAP
    for name, items in sections:
        draw.text((PAD, y), name, font=SECTION, fill=INK)
        y += line_height(SECTION) + 8
        for item in items:
            for line in wrap(draw, item["caption"], TEXT, width - 2 * PAD):
                draw.text((PAD, y), line, font=TEXT, fill=MUTED)
                y += line_height(TEXT)
            y += 4
            image = images[item["file"]]
            sheet.paste(image, (PAD, y))
            draw.rectangle((PAD - 1, y - 1, PAD + image.width, y + image.height), outline=RULE)
            y += image.height + GAP
        y += GAP
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    print("sheet", path.name, sheet.size)


def grid_sheet(title: str, items: list[dict[str, str]], path: Path, columns: int = 2, thumb: int = 640) -> None:
    """Whole windows as thumbnails in a grid, captions under each."""
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    thumbs = []
    for item in items:
        image = Image.open(OUT / item["file"]).convert("RGB")
        scale = min(1.0, thumb / image.width)
        resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
        lines = wrap(probe, item["caption"], TEXT, thumb)
        thumbs.append((resized, lines))
    rows = [thumbs[i:i + columns] for i in range(0, len(thumbs), columns)]
    row_heights = [max(img.height + 8 + line_height(TEXT) * len(lines) for img, lines in row) for row in rows]
    width = PAD * 2 + columns * thumb + (columns - 1) * GAP
    height = PAD + line_height(TITLE) + GAP + sum(h + GAP * 2 for h in row_heights) + PAD
    sheet = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((PAD, PAD), title, font=TITLE, fill=INK)
    y = PAD + line_height(TITLE) + GAP
    for row, row_height in zip(rows, row_heights):
        for index, (image, lines) in enumerate(row):
            x = PAD + index * (thumb + GAP)
            sheet.paste(image, (x, y))
            draw.rectangle((x - 1, y - 1, x + image.width, y + image.height), outline=RULE)
            text_y = y + image.height + 8
            for line in lines:
                draw.text((x, text_y), line, font=TEXT, fill=MUTED)
                text_y += line_height(TEXT)
        y += row_height + GAP * 2
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    print("sheet", path.name, sheet.size)


def gallery(items: list[dict[str, str]]) -> None:
    groups: dict[str, list[dict[str, str]]] = {}
    for item in items:
        groups.setdefault(item["group"], []).append(item)
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>Matrix light mode states</title><style>",
        "body{margin:0;padding:24px;background:#f2f4f7;color:#17212f;font:15px/1.5 'Segoe UI',sans-serif}",
        "h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 12px;border-top:1px solid #ced4dd;padding-top:16px}",
        "p{color:#5a6574;margin:0 0 8px}figure{margin:0 0 20px}figcaption{color:#5a6574;margin-top:4px}",
        "img{max-width:100%;height:auto;border:1px solid #ced4dd;background:#fff}",
        "</style></head><body><h1>Options Matrix Studio and Viewer, light mode</h1>",
        "<p>Demo data. Every screenshot is a real window of the current code; a few states were set "
        "the way the app sets them (see each caption).</p>",
        "<h2>Issues spotted</h2><ul>",
        *(f"<li>{html.escape(finding)}</li>" for finding in FINDINGS),
        "</ul>",
    ]
    for name in ORDER + sorted(set(groups) - set(ORDER)):
        if name not in groups:
            continue
        parts.append(f"<h2>{html.escape(name)}</h2>")
        for item in groups[name]:
            parts.append(
                f"<figure><img src='{html.escape(item['file'])}' alt='{html.escape(item['caption'])}' loading='lazy'>"
                f"<figcaption>{html.escape(item['caption'])}</figcaption></figure>"
            )
    parts.append("</body></html>")
    (OUT / "index.html").write_text("\n".join(parts), encoding="utf-8")
    print("gallery index.html")


def main() -> None:
    items = load_items()
    by_group: dict[str, list[dict[str, str]]] = {}
    for item in items:
        by_group.setdefault(item["group"], []).append(item)
    sheets = OUT / "sheets"
    studio_windows = by_group.get("Studio windows", [])
    matrix = [i for i in studio_windows if "recording" not in i["file"]]
    recording = [i for i in studio_windows if "recording" in i["file"]]
    if matrix:
        grid_sheet("Options Matrix Studio (mini PC): matrix states", matrix, sheets / "1-studio-matrix.png")
    if recording:
        grid_sheet("Options Matrix Studio (mini PC): Recording tab", recording, sheets / "2-studio-recording.png")
    studio_bar = [(g, by_group[g]) for g in ORDER if g.startswith("Studio top bar") and g in by_group]
    if studio_bar:
        stack_sheet("Options Matrix Studio: top bar states", studio_bar, sheets / "3-studio-top-bar.png")
    if by_group.get("Viewer windows"):
        grid_sheet("Options Matrix Viewer (work PC): window states", by_group["Viewer windows"], sheets / "4-viewer-windows.png")
    viewer_bar = [(g, by_group[g]) for g in ORDER if g.startswith("Viewer top bar") and g in by_group]
    if viewer_bar:
        stack_sheet("Options Matrix Viewer: top bar states", viewer_bar, sheets / "5-viewer-top-bar.png")
    dialogs = by_group.get("Dialogs", []) + by_group.get("Native Windows pop-ups", [])
    if dialogs:
        grid_sheet("Dialogs and pop-ups", dialogs, sheets / "6-dialogs.png")
    if by_group.get("Tooltips"):
        stack_sheet("Tooltips", [("Hover text on the top-bar badges", by_group["Tooltips"])], sheets / "7-tooltips.png")
    gallery(items)


if __name__ == "__main__":
    main()
