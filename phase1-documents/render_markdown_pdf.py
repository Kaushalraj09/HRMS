#!/usr/bin/env python3
"""Render a plain-text PDF from a Markdown file without external dependencies.

Supports optional JPEG appendix pages for diagram screenshots.
"""

from __future__ import annotations

import math
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT_MARGIN = 42
TOP_MARGIN = 800
BOTTOM_MARGIN = 42
FONT_SIZE = 9
LINE_HEIGHT = 12
MAX_CHARS = 94


def escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def normalize_lines(markdown: str) -> list[str]:
    normalized: list[str] = []
    for raw_line in markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.rstrip()

        if not line:
            normalized.append("")
            continue

        if line.startswith("```"):
            normalized.append(line)
            continue

        prefix = ""
        body = line

        if line.startswith("#"):
            body = line.lstrip("#").strip()
            prefix = ""
        elif line.startswith("- "):
            body = line[2:].strip()
            prefix = "- "
        elif line[:2].isdigit() and line[1:3] == ". ":
            prefix = line[:3]
            body = line[3:].strip()
        elif line.startswith("|"):
            normalized.append(line)
            continue

        available = max(20, MAX_CHARS - len(prefix))
        wrapped = textwrap.wrap(body, width=available, break_long_words=False, break_on_hyphens=False)

        if not wrapped:
            normalized.append(prefix.rstrip())
            continue

        for index, part in enumerate(wrapped):
            if index == 0:
                normalized.append(f"{prefix}{part}".rstrip())
            else:
                normalized.append(f"{' ' * len(prefix)}{part}".rstrip())

    return normalized


def build_pages(lines: list[str]) -> list[list[str]]:
    lines_per_page = math.floor((TOP_MARGIN - BOTTOM_MARGIN) / LINE_HEIGHT)
    pages: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        current.append(line)
        if len(current) >= lines_per_page:
            pages.append(current)
            current = []

    if current or not pages:
        pages.append(current)

    return pages


def build_content_stream(page_lines: list[str]) -> bytes:
    commands = ["BT", f"/F1 {FONT_SIZE} Tf", f"{LEFT_MARGIN} {TOP_MARGIN} Td", f"{LINE_HEIGHT} TL"]

    for line in page_lines:
        commands.append(f"({escape_pdf_text(line)}) Tj")
        commands.append("T*")

    commands.append("ET")
    data = "\n".join(commands).encode("latin-1", errors="replace")
    return data


def get_image_dimensions(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    width = height = None
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if line.startswith("pixelWidth:"):
            width = int(line.split(":", 1)[1].strip())
        elif line.startswith("pixelHeight:"):
            height = int(line.split(":", 1)[1].strip())
    if width is None or height is None:
        raise ValueError(f"Unable to read image dimensions for {path}")
    return width, height


def convert_to_jpeg(path: Path) -> Path:
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return path

    temp_dir = Path(tempfile.gettempdir())
    output_path = temp_dir / f"{path.stem}.jpg"
    subprocess.run(
        ["sips", "-s", "format", "jpeg", str(path), "--out", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return output_path


def build_image_content_stream(image_width: int, image_height: int) -> bytes:
    usable_width = PAGE_WIDTH - LEFT_MARGIN * 2
    usable_height = PAGE_HEIGHT - 72
    scale = min(usable_width / image_width, usable_height / image_height)
    draw_width = image_width * scale
    draw_height = image_height * scale
    x = (PAGE_WIDTH - draw_width) / 2
    y = (PAGE_HEIGHT - draw_height) / 2

    commands = [
        "q",
        f"{draw_width:.2f} 0 0 {draw_height:.2f} {x:.2f} {y:.2f} cm",
        "/Im1 Do",
        "Q",
    ]
    return "\n".join(commands).encode("latin-1", errors="replace")


def write_pdf(input_path: Path, output_path: Path, image_paths: list[Path]) -> None:
    text = input_path.read_text(encoding="utf-8")
    text_pages = build_pages(normalize_lines(text))
    jpeg_images: list[tuple[Path, int, int]] = []
    for image_path in image_paths:
        jpeg_path = convert_to_jpeg(image_path)
        width, height = get_image_dimensions(jpeg_path)
        jpeg_images.append((jpeg_path, width, height))

    objects: list[bytes] = []

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

    total_pages = len(text_pages) + len(jpeg_images)
    page_kids = " ".join(f"{index} 0 R" for index in range(3, 3 + total_pages * 2, 2))
    objects.append(f"<< /Type /Pages /Count {total_pages} /Kids [{page_kids}] >>".encode())

    font_object_number = 3 + total_pages * 2
    next_object_number = font_object_number + 1

    image_object_numbers: list[int] = []
    for _ in jpeg_images:
        image_object_numbers.append(next_object_number)
        next_object_number += 1

    for page_index, page_lines in enumerate(text_pages):
        page_object_number = 3 + page_index * 2
        content_object_number = page_object_number + 1
        page_obj = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_object_number} 0 R >> >> "
            f"/Contents {content_object_number} 0 R >>"
        ).encode()
        objects.append(page_obj)

        stream = build_content_stream(page_lines)
        content_obj = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        objects.append(content_obj)

    for image_index, (_, width, height) in enumerate(jpeg_images):
        page_number = len(text_pages) + image_index
        page_object_number = 3 + page_number * 2
        content_object_number = page_object_number + 1
        image_object_number = image_object_numbers[image_index]

        page_obj = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /XObject << /Im1 {image_object_number} 0 R >> >> "
            f"/Contents {content_object_number} 0 R >>"
        ).encode()
        objects.append(page_obj)

        stream = build_image_content_stream(width, height)
        content_obj = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        objects.append(content_obj)

    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    for image_index, (image_path, width, height) in enumerate(jpeg_images):
        data = image_path.read_bytes()
        image_obj = (
            f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
            f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(data)} >>\nstream\n"
        ).encode() + data + b"\nendstream"
        objects.append(image_obj)

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    ).encode()
    pdf.extend(trailer)

    output_path.write_bytes(pdf)


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: render_markdown_pdf.py <input.md> <output.pdf> [image ...]", file=sys.stderr)
        return 1

    input_path = Path(sys.argv[1]).resolve()
    output_path = Path(sys.argv[2]).resolve()
    image_paths = [Path(arg).resolve() for arg in sys.argv[3:]]
    write_pdf(input_path, output_path, image_paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
