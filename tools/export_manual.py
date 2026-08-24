#!/usr/bin/env python3
"""Zapisuje instrukcję z programu do plików w repozytorium.

Instrukcja ma jedno źródło — app/ui/manual_content.py. Ten skrypt tworzy z niej
INSTRUKCJA.md (do przeglądania na GitHubie) oraz INSTRUKCJA.html (do wydruku),
żeby wersje nie rozjeżdżały się z tym, co widzi użytkownik w programie.

Uruchomienie:  python tools/export_manual.py
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ui.manual import full_html                    # noqa: E402
from app.ui.manual_content import INTRO, SECTIONS, TITLE  # noqa: E402


def _inline(text: str) -> str:
    """Zamienia znaczniki tekstowe HTML na odpowiedniki Markdowna."""
    text = re.sub(r"</?b>", "**", text)
    text = re.sub(r"</?i>", "_", text)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.S)
    text = re.sub(r"<br\s*/?>", " ", text)
    return html.unescape(text).strip()


def _cells(row: str, tag: str) -> list[str]:
    return [_inline(c) for c in re.findall(rf"<{tag}>(.*?)</{tag}>", row, re.S)]


def _table(block: str) -> list[str]:
    rows = re.findall(r"<tr>(.*?)</tr>", block, re.S)
    if not rows:
        return []
    header = _cells(rows[0], "th") or _cells(rows[0], "td")
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows[1:]:
        cells = _cells(row, "td")
        if cells:
            lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def to_markdown(section_html: str) -> list[str]:
    """Prosty konwerter obsługujący tylko znaczniki użyte w instrukcji."""
    out: list[str] = []
    pattern = re.compile(
        r"<(h2|h3|p|ul|ol|table)(?:\s+class=['\"]([^'\"]*)['\"])?>(.*?)</\1>", re.S
    )
    for tag, css_class, body in pattern.findall(section_html):
        if tag == "h2":
            out += [f"## {_inline(body)}", ""]
        elif tag == "h3":
            out += [f"### {_inline(body)}", ""]
        elif tag == "p":
            prefix = "> " if css_class == "warn" else ""
            out += [prefix + _inline(body), ""]
        elif tag in ("ul", "ol"):
            items = re.findall(r"<li>(.*?)</li>", body, re.S)
            for i, item in enumerate(items, 1):
                bullet = f"{i}." if tag == "ol" else "-"
                out.append(f"{bullet} {_inline(item)}")
            out.append("")
        elif tag == "table":
            out += _table(body)
    return out


def main() -> int:
    root = Path(__file__).resolve().parent.parent

    lines = [f"# {TITLE}", ""]
    lines += to_markdown(INTRO)
    lines += [
        "> Ta sama instrukcja jest dostępna w programie: **Pomoc → Instrukcja "
        "obsługi** albo klawisz **F1**.", "",
        "## Spis treści", "",
    ]
    for section_id, title, _ in SECTIONS:
        anchor = title.lower().replace(" ", "-").replace(",", "")
        lines.append(f"- [{title}](#{anchor})")
    lines.append("")
    for _, _, section_html in SECTIONS:
        lines += to_markdown(section_html)

    md = root / "INSTRUKCJA.md"
    md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    page = root / "INSTRUKCJA.html"
    page.write_text(
        "<!doctype html>\n<html lang='pl'>\n<head>\n<meta charset='utf-8'>\n"
        f"<title>{TITLE}</title>\n</head>\n<body>\n{full_html()}\n</body>\n</html>\n",
        encoding="utf-8",
    )

    print(f"zapisano {md.relative_to(root)} ({md.stat().st_size // 1024} kB)")
    print(f"zapisano {page.relative_to(root)} ({page.stat().st_size // 1024} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
