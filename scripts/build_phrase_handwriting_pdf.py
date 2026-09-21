import json
import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "狄克生片語中文填寫表.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\msjh.ttc")
pdfmetrics.registerFont(TTFont("JhengHei", str(FONT_PATH), subfontIndex=0))

items = [
    p for p in json.loads((ROOT / "data" / "phrases.json").read_text(encoding="utf-8"))
    if p.get("meaningZh") == "待人工確認"
]

rows_per_column = 17
per_page = rows_per_column * 2
pages = math.ceil(len(items) / per_page)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
c = canvas.Canvas(str(OUTPUT), pagesize=A4)
width, height = A4
left, right = 34, width - 34
gap = 16
column_w = (right - left - gap) / 2
row_h = 40

for page_no in range(pages):
    page_items = items[page_no * per_page:(page_no + 1) * per_page]
    c.setFont("JhengHei", 16)
    c.setFillColor(colors.black)
    c.drawString(left, height - 40, "狄克生片語中文填寫表")
    c.setFont("JhengHei", 9)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawString(left, height - 57, "在橫線上手寫中文，按頁碼拍照傳回即可。")
    c.drawRightString(right, height - 57, f"第 {page_no + 1} / {pages} 頁")
    c.setStrokeColor(colors.HexColor("#AAAAAA"))
    c.line(left, height - 66, right, height - 66)

    for i, item in enumerate(page_items):
        col = i // rows_per_column
        row = i % rows_per_column
        x = left + col * (column_w + gap)
        top = height - 82 - row * row_h
        c.setFillColor(colors.HexColor("#555555"))
        c.setFont("JhengHei", 8)
        c.drawString(x, top, item["id"])
        c.setFillColor(colors.black)
        phrase = item["phrase"]
        size = 9
        phrase_w = column_w - 44
        while pdfmetrics.stringWidth(phrase, "JhengHei", size) > phrase_w and size > 6:
            size -= 0.5
        c.setFont("JhengHei", size)
        c.drawString(x + 43, top, phrase)
        c.setStrokeColor(colors.HexColor("#B5B5B5"))
        c.line(x, top - 25, x + column_w, top - 25)

    c.setFont("JhengHei", 8)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(left, 26, f"本頁：{page_items[0]['id']}－{page_items[-1]['id']}    共 {len(page_items)} 筆")
    c.drawRightString(right, 26, "狄克生片語")
    c.showPage()

c.save()
print(f"{OUTPUT} | {len(items)} items | {pages} pages")
