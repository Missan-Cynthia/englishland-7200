"""Extract the two supplied PDF word lists into compact JSON for the MVP."""

import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader


SOURCE_DIR = Path(sys.argv[1])
OUTPUT_DIR = Path(sys.argv[2])


def page_text(path):
    return [page.extract_text() or "" for page in PdfReader(str(path)).pages]


def clean(value):
    return re.sub(r"\s+", " ", value).strip()


def extract_basic(path):
    text = "\n".join(page_text(path))
    # PDF extraction occasionally joins the next item number to the previous word.
    matches = list(re.finditer(r"(?<!\d)(\d{1,4})\.\s*([^\n]*)", text))
    rows = []
    for index, match in enumerate(matches):
        number = int(match.group(1))
        if not 1 <= number <= 1200:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = [clean(match.group(2))] + [clean(x) for x in text[match.end():end].splitlines()]
        block = [x for x in block if x and not re.search(r"教育部國中小|1200 字", x)]
        english_candidates = [x for x in block if re.fullmatch(r"[A-Za-z][A-Za-z .,'()/-]*", x)]
        if not english_candidates:
            continue
        word = english_candidates[0]
        meaning_parts = []
        for value in block:
            if value == word:
                break
            if re.search(r"[\u3400-\u9fff]", value):
                meaning_parts.append(value)
        meaning = clean(" ".join(meaning_parts))
        if meaning:
            rows.append({"id": f"b{number:04d}", "word": word, "meaning": meaning, "level": (number - 1) // 20 + 1})
    unique = {row["id"]: row for row in rows}
    # Five lines are merged by the source PDF's text layer; restore them explicitly.
    merged_rows = {
        702: ("o'clock", "點鐘"),
        853: ("ruler", "尺"),
        854: ("run", "跑"),
        887: ("(TV) set", "電視機"),
        984: ("(beef) steak", "牛排"),
        1108: ("two", "二"),
        1109: ("type", "打字"),
    }
    for number, (word, meaning) in merged_rows.items():
        unique[f"b{number:04d}"] = {
            "id": f"b{number:04d}", "word": word, "meaning": meaning,
            "level": (number - 1) // 20 + 1,
        }
    return [unique[key] for key in sorted(unique)]


POS = r"(?:n|v|adj|adv|prep|conj|pron|interj|art|aux)\."


def extract_advanced(path):
    pages = page_text(path)
    rows = []
    level = 1
    for text in pages:
        level_match = re.search(r"第([一二三四五六])級", text)
        if level_match:
            level = "一二三四五六".index(level_match.group(1)) + 1
        for raw in text.splitlines():
            line = clean(raw)
            if not line or not re.search(POS, line):
                continue
            line = re.sub(rf"\s+(?:{POS})(?:/(?:{POS}))*.*$", "", line).strip()
            if not re.fullmatch(r"[A-Za-z][A-Za-z'() /-]*", line):
                continue
            for word in re.split(r"/", line):
                word = clean(re.sub(r"\([^)]*\)", "", word))
                if word and len(word) > 1:
                    rows.append((word, level))
    seen = set()
    output = []
    for word, word_level in rows:
        key = word.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append({
            "id": f"a{len(output) + 1:04d}",
            "word": word,
            "meaning": "原始詞表未提供中文意思",
            "level": word_level,
            "meaningPending": True,
        })
    return output


basic_pdf = next(SOURCE_DIR.glob("*1200*.pdf"))
advanced_pdf = next(SOURCE_DIR.glob("*7000*.pdf"))
basic = extract_basic(basic_pdf)
advanced = extract_advanced(advanced_pdf)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "basic.json").write_text(json.dumps(basic, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
(OUTPUT_DIR / "advanced.json").write_text(json.dumps(advanced, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(json.dumps({"basic": len(basic), "advanced": len(advanced)}, ensure_ascii=False))
