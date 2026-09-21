"""Build a standalone, local-only phrase matching review page."""

import difflib
import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHRASES = ROOT / "data" / "phrases.json"
CHINESE = ROOT / "data" / "phrase-translations.json"
REPORT = ROOT / "data" / "phrases-unmatched.txt"
DECISIONS = ROOT / "data" / "phrase-manual-decisions.json"
OUTPUT = ROOT / "phrase-manual-review.html"

INCLUDED_REASONS = {
    "版本用語或片語寫法不同，現有證據不足",
    "多個近似候選，證據不足以唯一判定",
    "英文來源疑似排字／OCR 異常",
}


def norm(text):
    text = text.casefold().replace("’", "'")
    return re.sub(r"[^a-z0-9']+", " ", text).strip()


def phrase_score(left, right):
    return difflib.SequenceMatcher(None, norm(left), norm(right)).ratio()


def evidence_score(item, candidate):
    evidence_words = set(norm(candidate.get("evidenceText", "")).split())
    scores = []
    for sample in [item.get("meaningEn", ""), *item.get("examples", [])]:
        words = set(norm(sample).split())
        if words:
            scores.append(len(words & evidence_words) / len(words))
    return max(scores, default=0)


phrases = json.loads(PHRASES.read_text(encoding="utf-8"))
chinese = json.loads(CHINESE.read_text(encoding="utf-8"))
manual_decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))["decisions"]

reason_by_id = {}
in_details = False
for line in REPORT.read_text(encoding="utf-8-sig").splitlines():
    if line == "待確認明細：":
        in_details = True
        continue
    if line == "中文版未被採用明細：":
        break
    if not in_details or not line.startswith("p"):
        continue
    parts = line.split("\t")
    if len(parts) >= 4:
        reason_by_id[parts[0]] = parts[3]

# Reconstruct the 83 Chinese rows not consumed by the 240 confirmed matches.
# Exact Chinese meaning plus the closest heading is sufficient here because it
# is used only to prevent offering an already-confirmed row for reassignment.
used = set()
manual_confirmed_ids = {x["id"] for x in manual_decisions if x["decision"] == "confirmed"}
manual_candidate_ids = {x["candidateId"] for x in manual_decisions if x["decision"] == "confirmed"}
for ci, candidate in enumerate(chinese):
    candidate_id = f"zh-u{candidate['unit']:02d}-{candidate['number']:02d}-o{candidate['order']:03d}"
    if candidate_id in manual_candidate_ids:
        used.add(ci)
for item in phrases:
    if item["meaningZh"] == "待人工確認" or item["id"] in manual_confirmed_ids:
        continue
    options = [
        (phrase_score(item["phrase"], candidate["phrase"]), ci)
        for ci, candidate in enumerate(chinese)
        if ci not in used and candidate["meaningZh"] == item["meaningZh"]
    ]
    if options:
        used.add(max(options)[1])

available = [(ci, item) for ci, item in enumerate(chinese) if ci not in used]
review_items = []
for item in phrases:
    reason = reason_by_id.get(item["id"])
    if reason not in INCLUDED_REASONS:
        continue
    ranked = []
    for ci, candidate in available:
        ps = phrase_score(item["phrase"], candidate["phrase"])
        es = evidence_score(item, candidate)
        same_unit = item["lesson"] == candidate["unit"]
        score = ps + 0.22 * es + (0.12 if same_unit else 0)
        if same_unit or ps >= 0.48 or es >= 0.42:
            ranked.append((score, ps, es, ci, candidate))
    ranked.sort(reverse=True, key=lambda row: (row[0], row[1], row[2]))
    if not ranked:
        candidates = []
    else:
        best = ranked[0][0]
        limit = 8 if reason.startswith("多個") else 5
        candidates = ranked[:limit]
        candidates = [row for row in candidates if row[0] >= best - (0.18 if reason.startswith("多個") else 0.13)]
        if reason.startswith("多個") and len(candidates) < 2:
            candidates = ranked[:2]
    review_items.append({
        "id": item["id"],
        "lesson": item["lesson"],
        "phrase": item["phrase"],
        "meaningEn": item["meaningEn"],
        "examples": item["examples"],
        "reason": reason,
        "candidates": [
            {
                "candidateId": f"zh-u{row[4]['unit']:02d}-{row[4]['number']:02d}-o{row[4]['order']:03d}",
                "unit": row[4]["unit"],
                "number": row[4]["number"],
                "phrase": row[4]["phrase"],
                "meaningZh": row[4]["meaningZh"],
            }
            for row in candidates
        ],
    })

assert len(review_items) == 100, f"Expected 100 remaining review rows, got {len(review_items)}"
payload = json.dumps(review_items, ensure_ascii=False).replace("</", "<\\/")

document = r'''<!doctype html>
<html lang="zh-Hant-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>狄克森片語人工配對審核</title>
  <style>
    :root { color-scheme: light; font-family: system-ui, "Noto Sans TC", sans-serif; color: #30343b; background: #fffcf7; }
    * { box-sizing: border-box; }
    body { margin: 0; }
    header { position: sticky; top: 0; z-index: 2; padding: 16px 20px; background: #fff; border-bottom: 1px solid #e8e1e7; }
    h1 { margin: 0 0 10px; color: #5e3fa3; font-size: 22px; }
    .toolbar, .progress, .nav, .actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    .progress { font-weight: 700; }
    main { width: min(980px, calc(100% - 32px)); margin: 24px auto 48px; }
    .panel, .candidate { background: #fff; border: 1px solid #e8e1e7; border-radius: 14px; padding: 18px; }
    .meta { color: #747078; font-weight: 700; }
    .phrase { margin: 8px 0 18px; font-size: 28px; color: #5e3fa3; }
    h2 { margin-top: 22px; font-size: 18px; }
    .examples { padding-left: 24px; }
    .reason { padding: 12px; border-left: 4px solid #ffc21a; background: #fff8de; }
    .candidates { display: grid; gap: 12px; }
    .candidate.selected { border-color: #7e57c2; box-shadow: 0 0 0 2px #d8cce8; }
    .candidate h3 { margin: 0 0 8px; font-size: 19px; }
    .meaning { margin: 6px 0 14px; font-size: 18px; }
    button { min-height: 40px; padding: 8px 14px; border: 1px solid #d8cce8; border-radius: 9px; background: #fff; color: #6d4bae; font-weight: 700; cursor: pointer; }
    button:hover { background: #f3eefa; }
    button.primary { border-color: #7e57c2; background: #7e57c2; color: #fff; }
    button.danger { color: #a33a62; border-color: #f3b6cd; }
    button:disabled { opacity: .45; cursor: not-allowed; }
    .nav { justify-content: space-between; margin-top: 18px; }
    .empty { color: #a33a62; font-weight: 700; }
    .status { margin-left: auto; color: #6d4bae; font-weight: 700; }
    @media (max-width: 640px) { .status { width: 100%; margin-left: 0; } .phrase { font-size: 23px; } }
  </style>
</head>
<body>
  <header>
    <h1>狄克森片語人工配對審核</h1>
    <div>配對標準：只確認同一片語或明確形式差異；近義片語、不同介系詞搭配一律不視為同一筆。</div>
    <div class="toolbar">
      <div id="progress" class="progress"></div>
      <button id="export" class="primary" type="button">匯出審核結果 JSON</button>
    </div>
  </header>
  <main>
    <section id="review" class="panel"></section>
    <nav class="nav" aria-label="審核項目導覽">
      <button id="previous" type="button">上一筆</button>
      <button id="next" type="button">下一筆</button>
    </nav>
  </main>
  <script>
    const items = __PAYLOAD__;
    const storageKey = "english-land-phrase-manual-review-v1";
    const indexKey = `${storageKey}-current-index`;
    let decisions = {};
    let currentIndex = Math.min(Number(localStorage.getItem(indexKey)) || 0, items.length - 1);

    try { decisions = JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch { decisions = {}; }
    const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));

    function saveDecision(item, decision, candidate = null) {
      decisions[item.id] = { decision, candidate, reviewedAt: new Date().toISOString() };
      localStorage.setItem(storageKey, JSON.stringify(decisions));
      render();
    }

    function renderProgress() {
      const values = Object.values(decisions);
      const confirmed = values.filter(x => x.decision === "confirmed").length;
      const rejected = values.filter(x => x.decision === "none").length;
      const later = values.filter(x => x.decision === "later").length;
      const untouched = items.length - confirmed - rejected - later;
      document.querySelector("#progress").textContent = `已確認 ${confirmed} / ${items.length}｜都不是 ${rejected}｜稍後處理 ${later}｜未處理 ${untouched}`;
    }

    function render() {
      const item = items[currentIndex];
      const selected = decisions[item.id];
      const examples = item.examples.map(text => `<li>${escapeHtml(text)}</li>`).join("");
      const candidates = item.candidates.length ? item.candidates.map(candidate => {
        const active = selected?.decision === "confirmed" && selected.candidate?.candidateId === candidate.candidateId;
        const encoded = encodeURIComponent(JSON.stringify(candidate));
        return `<article class="candidate ${active ? "selected" : ""}">
          <h3>中文版 Unit ${candidate.unit} #${candidate.number}：${escapeHtml(candidate.phrase)}</h3>
          <div class="meaning">${escapeHtml(candidate.meaningZh)}</div>
          <div class="actions">
            <button class="primary" data-action="confirm" data-candidate="${encoded}" type="button">確認此配對</button>
            <button class="danger" data-action="none" type="button">都不是</button>
            <button data-action="later" type="button">稍後處理</button>
          </div>
        </article>`;
      }).join("") : `<p class="empty">目前沒有可列出的中文版候選，請選擇「都不是」或「稍後處理」。</p>
        <div class="actions"><button class="danger" data-action="none" type="button">都不是</button><button data-action="later" type="button">稍後處理</button></div>`;
      const statusText = selected ? ({confirmed:"已確認配對", none:"已標記：都不是", later:"已標記：稍後處理"}[selected.decision]) : "尚未處理";
      document.querySelector("#review").innerHTML = `
        <div class="meta">${currentIndex + 1} / ${items.length}｜英文 Lesson ${item.lesson}｜${escapeHtml(item.id)}</div>
        <div class="status">目前狀態：${statusText}</div>
        <h2 class="phrase">${escapeHtml(item.phrase)}</h2>
        <h2>英文原始解釋</h2><p>${escapeHtml(item.meaningEn)}</p>
        <h2>英文原始例句</h2><ol class="examples">${examples}</ol>
        <h2>無法自動確認的原因</h2><p class="reason">${escapeHtml(item.reason)}</p>
        <h2>中文版候選項目</h2><div class="candidates">${candidates}</div>`;
      document.querySelector("#previous").disabled = currentIndex === 0;
      document.querySelector("#next").disabled = currentIndex === items.length - 1;
      document.querySelectorAll("[data-action]").forEach(button => button.addEventListener("click", () => {
        const action = button.dataset.action;
        const candidate = action === "confirm" ? JSON.parse(decodeURIComponent(button.dataset.candidate)) : null;
        saveDecision(item, action === "confirm" ? "confirmed" : action, candidate);
      }));
      localStorage.setItem(indexKey, String(currentIndex));
      renderProgress();
      window.scrollTo({top: 0, behavior: "smooth"});
    }

    document.querySelector("#previous").addEventListener("click", () => { if (currentIndex > 0) { currentIndex--; render(); } });
    document.querySelector("#next").addEventListener("click", () => { if (currentIndex < items.length - 1) { currentIndex++; render(); } });
    document.querySelector("#export").addEventListener("click", () => {
      const result = {
        formatVersion: 1,
        exportedAt: new Date().toISOString(),
        total: items.length,
        results: items.map(item => ({
          id: item.id,
          lesson: item.lesson,
          englishPhrase: item.phrase,
          reason: item.reason,
          ...(decisions[item.id] || {decision: "unreviewed", candidate: null}),
        })),
      };
      const blob = new Blob([JSON.stringify(result, null, 2)], {type: "application/json"});
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `phrase-manual-review-results-${new Date().toISOString().slice(0,10)}.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    });
    render();
  </script>
</body>
</html>
'''.replace("__PAYLOAD__", payload)

OUTPUT.write_text(document, encoding="utf-8")
print(json.dumps({
    "output": str(OUTPUT),
    "items": len(review_items),
    "reasonCounts": dict(sorted(__import__("collections").Counter(x["reason"] for x in review_items).items())),
    "candidateCounts": {"min": min(len(x["candidates"]) for x in review_items), "max": max(len(x["candidates"]) for x in review_items)},
}, ensure_ascii=False))
