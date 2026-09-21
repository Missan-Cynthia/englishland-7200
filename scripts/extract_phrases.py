"""Extract Dixson idioms PDF into structured JSON. Translation is a separate step."""

import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader


HEADER = "ESSENTIAL IDIOMS IN ENGLISH by ROBERT J. DIXSON"
FOOTER = "PRENTICE HALL REGENTS"
ENTRY = re.compile(r"^([A-Za-z][A-Za-z0-9'’() ,./-]{1,90}):\s*(.+)$")


def clean(text):
    return re.sub(r"\s+", " ", text.replace("’", "'")).strip()


def usable(line):
    line = clean(line)
    if not line or HEADER in line or FOOTER in line:
        return ""
    if re.fullmatch(r"-?\s*\d+\s*-?", line):
        return ""
    return line


def extract(pdf_path):
    rows = []
    current = None
    lesson = None
    mode = None

    def finish():
        nonlocal current
        if not current:
            return
        current["meaningEn"] = clean(" ".join(current.pop("_meaning")))
        current["examples"] = [clean(x) for x in current["examples"] if clean(x)]
        current["meaningZh"] = ""
        current["translationStatus"] = "pending"
        current["level"] = None
        rows.append(current)
        current = None

    page_texts = [page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages]
    for page_text in page_texts:
        for raw in page_text.splitlines():
            line = usable(raw)
            if not line:
                continue
            lesson_match = re.fullmatch(r"LESSON\s+(\d+)", line, re.I)
            if lesson_match:
                finish()
                lesson = int(lesson_match.group(1))
                mode = None
                continue
            if lesson is None:
                continue
            match = ENTRY.match(line)
            if match and not line.lower().startswith(("note:", "example:")):
                phrase = clean(match.group(1))
                # Entry headings are short idiomatic expressions, not prose sentences.
                if len(phrase.split()) <= 10 and phrase[0].islower():
                    finish()
                    current = {"phrase": phrase, "_meaning": [match.group(2)], "examples": [], "lesson": lesson}
                    mode = "meaning"
                    continue
            if not current:
                continue
            if re.match(r"^[o○]\s+", line):
                current["examples"].append(re.sub(r"^[o○]\s+", "", line))
                mode = "example"
            elif mode == "example" and current["examples"]:
                current["examples"][-1] += " " + line
            elif mode == "meaning":
                current["_meaning"].append(line)
    finish()

    # Remove accidental duplicates from repeated PDF text layers while preserving order.
    unique = []
    positions = {}
    for row in rows:
        if row["phrase"].lower() in {"o a", "o b", "doing (also", "accompany (also", "someone else doesn't want to same way) (also", "for a brief time (also"}:
            continue
        key = (row["lesson"], row["phrase"].casefold())
        if key not in positions:
            positions[key] = len(unique)
            unique.append(row)
        else:
            old_index = positions[key]
            old = unique[old_index]
            if len(row["examples"]) > len(old["examples"]):
                unique[old_index] = row
    for index, row in enumerate(unique, 1):
        if not row["examples"]:
            # Some headings first occur in an exercise index. Find the later
            # definition occurrence and recover its original bullet examples.
            best = []
            for match in re.finditer(re.escape(row["phrase"]) + r":", "\n".join(page_texts), re.I):
                recovered = []
                for raw in "\n".join(page_texts)[match.end():match.end() + 2200].splitlines()[1:]:
                    line = usable(raw)
                    if not line:
                        continue
                    if ENTRY.match(line) and not line.startswith(("o ", "○ ")):
                        break
                    if re.match(r"^[o○]\s+", line):
                        recovered.append(re.sub(r"^[o○]\s+", "", line))
                    elif recovered:
                        recovered[-1] += " " + line
                if len(recovered) > len(best):
                    best = recovered
            row["examples"] = [clean(x) for x in best[:3]]
        else:
            row["examples"] = row["examples"][:3]
        row["id"] = f"p{index:04d}"
    return unique


if __name__ == "__main__":
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    data = extract(source)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "count": len(data),
        "lessons": sorted({x["lesson"] for x in data}),
        "without_examples": sum(not x["examples"] for x in data),
        "first": data[:2],
        "last": data[-2:],
    }, ensure_ascii=False))
