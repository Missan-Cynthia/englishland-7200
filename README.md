# 英文學習樂園 MVP

這是獨立英文版專案，不會讀寫「認字樂園 V3」。請以本機 HTTP 伺服器開啟（不可直接雙擊 `index.html`）：

```powershell
python -m http.server 8000
```

再開啟 `http://localhost:8000`。預設以瀏覽器 `localStorage` 依帳號保存。若要啟用雲端，請建立**全新的英文版 Firebase 專案**，將 Web 設定填入 `js/firebase-config.js`；程式會拒絕國字版 `elementary-chinese` 專案，且英文資料只寫入 `englishUsers` 集合。

## 資料說明

- `data/basic.json`：由資料夾內 1200 PDF 擷取，共 1200 筆，含中文意思。
- `data/advanced.json`：由高中英文 7000 字 PDF 擷取，共 6035 個不重複詞項。來源只有英文與詞性，沒有中文翻譯，因此第一版先保留 `meaningPending`，進階區的「中文選英文」暫停啟用；聽音選英文可使用。
