# me.asdtw.org 個人網站

靜態網站，直接部署在 GitHub Pages，不需要 build。

```
CNAME / robots.txt / sitemap.xml / 404.html           搜尋引擎規則（全部允許）、找不到頁面
index.html / about.html / timeline.html / articles.html / contact.html / sponsor.html
data/articles.json                     文章清單（首頁與文章列表從這裡讀）
articles/                 每篇文章一個 html
images/articles/<slug>/    文章圖片
assets/css/style.css       全站樣式
assets/js/site.js          頁首頁尾、深色模式、文章清單、giscus（設定在檔案最上方的 SITE）
authoring/                  文章範本、設計規範、給 AI 的提示詞
```

## 本機預覽
```bash
python3 -m http.server 8000
```
開 http://localhost:8000 （不能直接雙擊 html，因為要讀 data/articles.json）。

## 部署
1. 推到 GitHub（`CNAME` 已設為 me.asdtw.org）。
2. Settings → Pages → Source 選 main 分支 / root。

## 之後要填的東西
- `assets/js/site.js`：`email`、`giscus`（到 https://giscus.app 取得）、各社群連結
- `about.html`：自行撰寫

## 發新文章
見 `authoring/AI-PROMPT.md`。

## 工作流程
分支、commit 格式、PR、CI、還原與緊急處理，見 [CONTRIBUTING.md](CONTRIBUTING.md)。
