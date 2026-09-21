"""Repair examples in an already translated phrases.json from the English PDF."""

import json
import re
import sys
from pathlib import Path
from pypdf import PdfReader


data_path, pdf_path = map(Path, sys.argv[1:3])
data = json.loads(data_path.read_text(encoding="utf-8"))
text = "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages)
heading = re.compile(r"^[A-Za-z][A-Za-z0-9'’() ,./-]{1,90}:\s*.+$")


def is_heading(line):
    if not heading.match(line):
        return False
    prefix = line.split(":", 1)[0]
    return prefix.count("(") == prefix.count(")")

for row in data:
    if row["examples"]:
        row["examples"] = row["examples"][:3]
        continue
    best = []
    for match in re.finditer(re.escape(row["phrase"]) + r":", text, re.I):
        recovered = []
        for raw in text[match.end():match.end() + 2200].splitlines()[1:]:
            line = re.sub(r"\s+", " ", raw).strip()
            if recovered and is_heading(line) and not re.match(r"^[o○]\s+", line):
                break
            if re.match(r"^[o○]\s+", line):
                recovered.append(re.sub(r"^[o○]\s+", "", line))
            elif recovered and line and "PRENTICE HALL REGENTS" not in line and "ESSENTIAL IDIOMS" not in line:
                recovered[-1] += " " + line
        if len(recovered) > len(best):
            best = recovered
    row["examples"] = [re.sub(r"\s+", " ", x).strip() for x in best[:3]]

data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"count": len(data), "withoutExamples": sum(not x["examples"] for x in data)}, ensure_ascii=False))
