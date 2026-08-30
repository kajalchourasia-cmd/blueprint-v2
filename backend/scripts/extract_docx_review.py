"""Extract review text from DOCX package parts without changing the source files."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def paragraph_text(node: ET.Element) -> str:
    pieces: list[str] = []
    for item in node.iter():
        if item.tag == f"{W}t" and item.text:
            pieces.append(item.text)
        elif item.tag == f"{W}tab":
            pieces.append("\t")
        elif item.tag in (f"{W}br", f"{W}cr"):
            pieces.append("\n")
    return re.sub(r"[ \t]+", " ", "".join(pieces)).strip()


def extract_part(data: bytes, part: str) -> list[dict[str, object]]:
    root = ET.fromstring(data)
    rows: list[dict[str, object]] = []
    index = 0
    for node in root.iter():
        if node.tag != f"{W}p":
            continue
        text = paragraph_text(node)
        if not text:
            continue
        index += 1
        style = None
        ppr = node.find(f"{W}pPr")
        if ppr is not None:
            pstyle = ppr.find(f"{W}pStyle")
            if pstyle is not None:
                style = pstyle.attrib.get(f"{W}val")
        rows.append({"part": part, "index": index, "style": style, "text": text})
    return rows


def extract_docx(path: Path) -> dict[str, object]:
    wanted = re.compile(
        r"^word/(document|footnotes|endnotes|comments|header\d+|footer\d+)\.xml$"
    )
    paragraphs: list[dict[str, object]] = []
    with zipfile.ZipFile(path) as package:
        for name in sorted(package.namelist()):
            if wanted.match(name):
                paragraphs.extend(extract_part(package.read(name), name))
    return {
        "file": str(path.resolve()),
        "paragraph_count": len(paragraphs),
        "paragraphs": paragraphs,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("documents", nargs="+", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for document in args.documents:
        result = extract_docx(document)
        output = args.output_dir / f"{document.stem}.review.json"
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest.append(
            {
                "source": str(document.resolve()),
                "review": str(output.resolve()),
                "paragraph_count": result["paragraph_count"],
            }
        )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
