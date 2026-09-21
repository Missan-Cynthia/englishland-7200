"""Second-pass, evidence-based matching of English and Chinese phrase sources."""

import collections
import difflib
import json
import re
import sys
from pathlib import Path


PENDING = "待人工確認"


def norm(text):
    text = text.casefold().replace("’", "'").replace("–", "-")
    text = re.sub(r"\b(one[’']?s)\b", "one's", text)
    text = re.sub(r"\b(sb|sth)\.?\b", lambda m: m.group(1), text)
    return re.sub(r"[^a-z0-9']+", " ", text).strip()


def forms(text):
    """Conservative phrase variants explicitly present in a heading."""
    values = {norm(text)}
    for part in re.split(r"\s*=\s*", text):
        values.add(norm(part))
    no_parens = re.sub(r"\([^)]*\)", "", text)
    values.add(norm(no_parens))
    values.add(norm(text.split(",", 1)[0]))
    # Expand explicit alternatives such as "all (day, week, month) long".
    optional = re.search(r"\(([^)]*,[^)]*)\)", text)
    if optional:
        for choice in optional.group(1).split(","):
            values.add(norm(text[:optional.start()] + choice + text[optional.end():]))
    # A slash often introduces a second explicit alias. Preserve both the full
    # heading and each alternative, normalizing an omitted repeated "to".
    parts = re.split(r"\s*/\s*", text)
    if len(parts) > 1:
        values.update(norm(part) for part in parts)
        values.update(norm(re.sub(r"^to\s+", "", part, flags=re.I)) for part in parts)
    return {value for value in values if value}


def skeletons(text):
    """Reduced forms used only with uniqueness plus corroborating evidence."""
    results = set()
    placeholders = {
        "to", "be", "a", "an", "the", "sb", "sth", "someone", "something",
        "somebody", "oneself", "one's", "place", "somewhere",
    }
    for value in forms(text):
        tokens = value.split()
        results.add(" ".join(token for token in tokens if token not in placeholders))
        if tokens and tokens[-1] in {"with", "of", "for", "from", "at", "on", "to"}:
            results.add(" ".join(tokens[:-1]))
    return {value for value in results if len(value) >= 4}


def phrase_similarity(a, b):
    return max(difflib.SequenceMatcher(None, x, y).ratio() for x in forms(a) for y in forms(b))


def text_similarity(english_item, chinese_item):
    evidence = norm(chinese_item.get("evidenceText", ""))
    if not evidence:
        return 0.0
    samples = [english_item.get("meaningEn", ""), *english_item.get("examples", [])]
    scores = []
    for sample in samples:
        sample = norm(sample)
        if len(sample) < 12:
            continue
        if sample in evidence:
            scores.append(1.0)
            continue
        sample_words = set(sample.split())
        evidence_words = set(evidence.split())
        containment = len(sample_words & evidence_words) / max(1, len(sample_words))
        scores.append(containment)
    return max(scores, default=0.0)


english_path, chinese_path, output_path, review_path = map(Path, sys.argv[1:5])
english = json.loads(english_path.read_text(encoding="utf-8"))
chinese = json.loads(chinese_path.read_text(encoding="utf-8"))

# Pass 1: exact explicit heading forms, requiring one-to-one uniqueness.
form_to_english = collections.defaultdict(list)
form_to_chinese = collections.defaultdict(list)
for ei, item in enumerate(english):
    for value in forms(item["phrase"]):
        form_to_english[value].append(ei)
for ci, item in enumerate(chinese):
    for value in forms(item["phrase"]):
        form_to_chinese[value].append(ci)

matches = {}
used_chinese = set()
methods = {}
for value in sorted(set(form_to_english) & set(form_to_chinese)):
    eis, cis = form_to_english[value], form_to_chinese[value]
    if len(eis) == 1 and len(cis) == 1 and eis[0] not in matches and cis[0] not in used_chinese:
        matches[eis[0]] = cis[0]
        used_chinese.add(cis[0])
        methods[eis[0]] = "exact_heading"

# Exact reduced headings capture explicit object/auxiliary variants (for
# example "take something into account" vs "take into account"). They are
# accepted only when unique on both sides and still reasonably similar.
skeleton_to_english = collections.defaultdict(list)
skeleton_to_chinese = collections.defaultdict(list)
for ei, item in enumerate(english):
    if ei not in matches:
        for value in skeletons(item["phrase"]):
            skeleton_to_english[value].append(ei)
for ci, item in enumerate(chinese):
    if ci not in used_chinese:
        for value in skeletons(item["phrase"]):
            skeleton_to_chinese[value].append(ci)
for value in sorted(set(skeleton_to_english) & set(skeleton_to_chinese)):
    eis, cis = skeleton_to_english[value], skeleton_to_chinese[value]
    if len(eis) == 1 and len(cis) == 1:
        ei, ci = eis[0], cis[0]
        if ei not in matches and ci not in used_chinese and phrase_similarity(english[ei]["phrase"], chinese[ci]["phrase"]) >= 0.62:
            matches[ei] = ci
            used_chinese.add(ci)
            methods[ei] = "unique_reduced_heading"

# Lesson and Unit numbering align for the shared portion of these editions.
# Use that boundary together with heading similarity (and, where available,
# repeated example wording). A clear margin over the runner-up is required.
for ci, citem in enumerate(chinese):
    if ci in used_chinese:
        continue
    ranked = []
    for ei, eitem in enumerate(english):
        if ei in matches or eitem["lesson"] != citem["unit"]:
            continue
        ps = phrase_similarity(eitem["phrase"], citem["phrase"])
        ts = text_similarity(eitem, citem)
        ranked.append((ps + 0.2 * ts, ps, ts, ei))
    ranked.sort(reverse=True)
    if not ranked:
        continue
    best = ranked[0]
    margin = best[0] - (ranked[1][0] if len(ranked) > 1 else 0)
    _, ps, ts, ei = best
    if (ps >= 0.76 and margin >= 0.06) or (ps >= 0.64 and ts >= 0.62 and margin >= 0.045):
        matches[ei] = ci
        used_chinese.add(ci)
        methods[ei] = "same_lesson_heading_evidence"

# Within each aligned Lesson/Unit, confirmed pairs act as anchors. When the
# unmatched entries between two anchors have the same cardinality and preserve
# order, accept an aligned pair only if its heading or example evidence also
# supports the correspondence.
for unit in range(1, 31):
    c_indices = [ci for ci, item in enumerate(chinese) if item["unit"] == unit]
    e_indices = [ei for ei, item in enumerate(english) if item["lesson"] == unit]
    anchors = sorted(
        (c_indices.index(ci), e_indices.index(ei))
        for ei, ci in matches.items()
        if ci in c_indices and ei in e_indices
    )
    boundaries = [(-1, -1), *anchors, (len(c_indices), len(e_indices))]
    for (c0, e0), (c1, e1) in zip(boundaries, boundaries[1:]):
        cs = [c_indices[pos] for pos in range(c0 + 1, c1) if c_indices[pos] not in used_chinese]
        es = [e_indices[pos] for pos in range(e0 + 1, e1) if e_indices[pos] not in matches]
        if not cs or len(cs) != len(es):
            continue
        for ci, ei in zip(cs, es):
            ps = phrase_similarity(english[ei]["phrase"], chinese[ci]["phrase"])
            ts = text_similarity(english[ei], chinese[ci])
            if ps >= 0.70 or (ps >= 0.55 and ts >= 0.62):
                matches[ei] = ci
                used_chinese.add(ci)
                methods[ei] = "adjacent_anchor_order"


def neighbor_window(ci):
    anchors = sorted((c, e) for e, c in matches.items())
    before = [(c, e) for c, e in anchors if c < ci]
    after = [(c, e) for c, e in anchors if c > ci]
    low = before[-1][1] + 1 if before else 0
    high = after[0][1] - 1 if after else len(english) - 1
    return low, high


# Pass 2: score every still-unmatched Chinese heading. The acceptance rules
# require either near-identical wording, or two independent kinds of evidence.
candidates_by_chinese = {}
for ci, citem in enumerate(chinese):
    if ci in used_chinese:
        continue
    low, high = neighbor_window(ci)
    candidates = []
    for ei, eitem in enumerate(english):
        if ei in matches:
            continue
        ps = phrase_similarity(eitem["phrase"], citem["phrase"])
        if ps < 0.55:
            continue
        ts = text_similarity(eitem, citem)
        in_order_window = low <= ei <= high
        order_distance = 0 if in_order_window else min(abs(ei - low), abs(ei - high))
        same_segment = eitem["lesson"] == citem["unit"]
        score = ps + 0.22 * ts + (0.05 if in_order_window else 0) + (0.03 if same_segment else 0)
        candidates.append((score, ps, ts, order_distance, ei))
    candidates.sort(reverse=True)
    candidates_by_chinese[ci] = candidates
    if not candidates:
        continue
    best = candidates[0]
    second_score = candidates[1][0] if len(candidates) > 1 else 0
    score, ps, ts, order_distance, ei = best
    margin = score - second_score
    method = None
    if ps >= 0.965 and margin >= 0.025:
        method = "near_exact_heading"
    elif ps >= 0.84 and ts >= 0.72 and margin >= 0.035:
        method = "heading_and_example"
    elif ps >= 0.86 and order_distance == 0 and ts >= 0.52 and margin >= 0.04:
        method = "heading_order_example"
    elif ps >= 0.90 and order_distance == 0 and margin >= 0.055:
        method = "heading_and_neighbors"
    if method and ei not in matches:
        matches[ei] = ci
        used_chinese.add(ci)
        methods[ei] = method

# Diagnose unresolved English entries without converting weak candidates into
# translations. Categories are mutually exclusive and evidence-based.
reasons = {}
for ei, eitem in enumerate(english):
    if ei in matches:
        continue
    ranked = []
    for ci, citem in enumerate(chinese):
        ps = phrase_similarity(eitem["phrase"], citem["phrase"])
        ts = text_similarity(eitem, citem) if ps >= 0.45 else 0
        ranked.append((ps + 0.2 * ts, ps, ts, ci))
    ranked.sort(reverse=True)
    best = ranked[0]
    near = [row for row in ranked if row[1] >= 0.82]
    phrase = eitem["phrase"]
    if len(near) >= 2 and near[0][0] - near[1][0] < 0.04:
        reason = "多個近似候選，證據不足以唯一判定"
    elif best[1] >= 0.78 or best[2] >= 0.55:
        reason = "版本用語或片語寫法不同，現有證據不足"
    elif re.search(r"\b(to all it|one's self|etc\.|\?\?)\b", phrase, re.I):
        reason = "英文來源疑似排字／OCR 異常"
    elif eitem["lesson"] > 30:
        reason = "中文版僅至 Unit 30，無對應收錄範圍"
    else:
        reason = "中文版未找到可驗證的對應項目"
    reasons[ei] = reason

output = []
for ei, item in enumerate(english):
    meaning = chinese[matches[ei]]["meaningZh"] if ei in matches else PENDING
    output.append({
        "id": item["id"],
        "phrase": item["phrase"],
        "meaningZh": meaning,
        "meaningEn": item["meaningEn"],
        "examples": item["examples"][:3],
        "lesson": item["lesson"],
    })

reason_counts = collections.Counter(reasons.values())
method_counts = collections.Counter(methods.values())
unmatched_chinese = [chinese[ci] for ci in range(len(chinese)) if ci not in used_chinese]
output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

lines = [
    "狄克森片語第二輪配對報告",
    f"英文版：{len(english)} 筆（Lesson 1-39）",
    f"中文版可解析：{len(chinese)} 筆（Unit 1-30；第 17 單元標作 Lesson 17，已依編號重啟還原）",
    f"確定配對：{len(matches)} 筆",
    f"待人工確認：{len(reasons)} 筆",
    f"中文版未被採用：{len(unmatched_chinese)} 筆",
    "",
    "配對方法：",
    *[f"- {name}: {count}" for name, count in sorted(method_counts.items())],
    "",
    "待確認原因：",
    *[f"- {name}: {count}" for name, count in sorted(reason_counts.items())],
    "",
    "待確認明細：",
]
for ei, reason in reasons.items():
    item = english[ei]
    lines.append(f"{item['id']}\tLesson {item['lesson']}\t{item['phrase']}\t{reason}")
lines.extend(["", "中文版未被採用明細："])
for item in unmatched_chinese:
    lines.append(f"Unit {item['unit']} #{item['number']}\t{item['phrase']}\t{item['meaningZh']}")
review_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")

print(json.dumps({
    "total": len(output),
    "matched": len(matches),
    "pending": len(reasons),
    "methods": method_counts,
    "reasons": reason_counts,
    "unusedChinese": len(unmatched_chinese),
}, ensure_ascii=False))
