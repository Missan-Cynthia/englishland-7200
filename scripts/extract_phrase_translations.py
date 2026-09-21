"""Extract ordered Chinese phrase entries from the supplied three-column PDF."""

import json
import re
import sys
from pathlib import Path

import pdfplumber


UNIT_RE = re.compile(r"\bUnit\s+(\d+)\b", re.I)
ENTRY_RE = re.compile(
    r"^\s*(\d+)\.\s*([A-Za-z][A-Za-z0-9 &'’()=/.?,!-]*?)\s*([\u3400-\u9fff].*)$"
)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'")).strip()


def clean_meaning(text: str) -> str:
    text = clean(text)
    # Parenthesized English at the end is supporting evidence, not Chinese meaning.
    text = re.sub(r"\s*\([A-Za-z][A-Za-z ,.;/'=-]*\)\s*$", "", text)
    return text.strip(" ，,;；")


source, output = map(Path, sys.argv[1:3])
entries = []
current_unit = None
current = None

with pdfplumber.open(source) as pdf:
    for page_number, page in enumerate(pdf.pages, start=1):
        width = page.width
        # Reading order is page -> left/middle/right column. Small overlap keeps
        # characters at column edges, while numbered-heading de-duplication below
        # prevents overlap from creating duplicate records.
        for column_number in range(3):
            left = max(0, column_number * width / 3 - 3)
            right = min(width, (column_number + 1) * width / 3 + 3)
            text = page.crop((left, 0, right, page.height)).extract_text() or ""
            for raw_line in text.splitlines():
                line = clean(raw_line)
                unit_match = UNIT_RE.search(line)
                if unit_match:
                    current_unit = int(unit_match.group(1))
                    if current:
                        entries.append(current)
                        current = None
                    continue

                match = ENTRY_RE.match(line)
                if match and current_unit is not None:
                    incoming_number = int(match.group(1))
                    # The PDF switches from "Unit" to "Lesson 17", so the Unit
                    # regex does not see it. Its item numbering visibly restarts;
                    # preserve that structural boundary instead of merging both.
                    if current and incoming_number <= 2 and current["number"] >= 7 and current_unit == current["unit"]:
                        current_unit += 1
                    if current:
                        entries.append(current)
                    number, phrase, meaning = match.groups()
                    current = {
                        "unit": current_unit,
                        "number": int(number),
                        "phrase": clean(phrase),
                        "meaningZh": clean_meaning(meaning),
                        "evidence": [line],
                        "page": page_number,
                        "column": column_number + 1,
                    }
                elif current:
                    current["evidence"].append(line)

if current:
    entries.append(current)

# Remove only genuine crop-overlap duplicates; retain repeated phrases in
# different Units because their context/order is evidence for matching.
deduped = []
seen = set()
for entry in entries:
    signature = (entry["unit"], entry["number"], entry["phrase"].casefold())
    if signature in seen:
        continue
    seen.add(signature)
    entry["order"] = len(deduped) + 1
    entry["evidenceText"] = " ".join(entry.pop("evidence"))
    deduped.append(entry)

output.write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"count": len(deduped), "units": sorted({x['unit'] for x in deduped})}, ensure_ascii=False))
