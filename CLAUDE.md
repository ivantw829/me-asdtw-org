# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

賴奕帆的個人網站（https://me.asdtw.org），純靜態 HTML/CSS/JS，部署在 GitHub Pages（repo：`ivantw829/me-asdtw-org`，`main` 推上去即上線）。沒有 build 步驟、沒有套件管理，也沒有測試框架。內容與介面文字一律使用繁體中文（zh-Hant-TW）。

## Commands

```bash
python3 -m http.server 8000        # 本機預覽；不能直接開 file://，因為頁面用 fetch 讀 data/*.json
python3 authoring/check.py         # 唯一的「測試」：資料、文章規範、站內連結、sitemap。CI 與 pre-commit 都會跑
python3 authoring/build-sitemap.py # 重新產生 sitemap.xml（pre-commit 會自動跑並 stage，通常不用手動）
bash authoring/ship.sh "type(scope): 描述"  # 一鍵：分支→commit→push→PR→等 CI→auto squash merge→同步本機
bash authoring/sync.sh             # 本機與 GitHub 對齊：prune、main 快轉、刪已合併的本機分支
bash authoring/setup-github.sh     # 一次性：squash only、auto-merge、保護 main（已套用）
```

`check.py` 沒有「只跑單一檢查」的選項；它是單一腳本，錯誤會列出所有問題後以非 0 結束。

## 架構（需要跨檔案才看得懂的部分）

**共用外框由 JS 注入。** 每個 HTML 只放空的 `<header data-site-header>`、`<footer data-site-footer>`，由 `assets/js/site.js` 填入導覽與頁尾。導覽項目、頁尾社群連結、email、giscus 設定都在 `site.js` 最上方的 `SITE` 物件。`site.js` 用自己的 `<script src>` 位置推算站台根目錄 `BASE`，所以同一份導覽在根目錄與 `articles/` 內都能用；新增站內連結時請沿用 `BASE`，不要寫死絕對路徑（`404.html` 例外，它用 `/` 開頭的路徑且不載入 `site.js`）。

**列表由 JSON 驅動。** `data/articles.json`（文章清單，首頁最新 3 篇與 `articles.html` 的標籤篩選都讀它；`draft: true` 會隱藏）與 `data/timeline.json`（`timeline.html`，依年份分組；選填 `url` 會把標題變成連結）都在 `site.js` 內用 `data-*` 屬性當掛載點渲染。文章頁本身是手寫的 HTML，上一篇／下一篇依 `<article data-slug>` 比對 JSON 產生。

**文章頁是範本產物，不是自由排版。** 從 `authoring/article-template.html` 複製，規範在 `authoring/DESIGN-SPEC.md`，給 AI 的提示詞在 `authoring/AI-PROMPT.md`。`check.py` 會強制：不得有 `style=`／`<style>`、`<script>` 恰好 2 個、恰好一個 `<h1>`、`<img>` 必須有 `alt`、不得殘留 `{{…}}`、`data-slug` 與檔名及 JSON 一致、每個 `articles/*.html` 都要登錄在 JSON。時間軸的 `category` 只能是固定六類（社會倡議／政策參與／社會服務／研習／研究／組織參與，定義在 `check.py` 的 `CATEGORIES`，改分類要同步改 `check.py` 與 `site.js` 篩選排序）。

**網域在多處硬寫，必須一致。** 以 `CNAME`（`me.asdtw.org`）為準；`robots.txt` 的 Sitemap 行、`authoring/build-sitemap.py` 的 `DOMAIN`、`index.html` 與文章範本的 `og:image` 都要同步，`check.py` 會驗 CNAME 與 robots/sitemap 一致。

**樣式只有一個 `assets/css/style.css`。** 淺色/深色用 CSS 變數；深色變數有兩份（`[data-theme="dark"]` 與 `prefers-color-scheme: dark` 且非 `data-theme="light"`），改色票要兩處一起改。識別色（奶白、黃 `--accent`、青綠 `--teal`、墨黑 `--ink`）來自角色設定圖，條碼／鏤空字／× 等裝飾只用在首頁，文章內文不用。

**切頁動畫（跨頁面 View Transitions）有隱性依賴。** 每個頁面（`404.html` 除外）的 `<head>` 需要 `<link rel="expect" href="#page-end" blocking="render">`，並在 `site.js` 之後放 `<span id="page-end" hidden></span>`，否則頁首會在切換瞬間閃空白。新增頁面或改範本時別漏掉。

**快取陷阱。** GitHub Pages 的 CSS/JS 快取 10 分鐘，剛部署後回訪者可能出現「新 HTML 配舊 CSS」的短暫錯位，這不是 bug；目前沒有檔名雜湊或版本碼。

## 工作流程（完整版見 CONTRIBUTING.md）

- `main` 受保護（已套用）：只能經 PR、CI（`check`、`pr-title`）通過後 squash merge；repo 只允許 squash、啟用 auto-merge、合併後自動刪分支。日常直接用 `authoring/ship.sh`。PR 標題即 `main` 上的 commit 訊息，必須是約定式 commit：`type(scope): 描述`，type 為 `feat fix content docs style refactor perf chore ci revert`。分支前綴對應 type（如 `content/…`）。
- 本機 hooks 在 `.githooks/`，**每個 clone 要自己啟用**：`git config core.hooksPath .githooks`。pre-commit 會拒絕在 `main` 上提交、自動重建並 stage `sitemap.xml`、再執行 `check.py`；pre-push 拒絕推 `main`（緊急用 `ALLOW_MAIN_COMMIT=1` / `ALLOW_MAIN_PUSH=1`）。
- 提交信箱使用 GitHub noreply 位址（repo local config）。推送會動到 `.github/workflows/` 時，`gh` 的 token 需要 `workflow` scope。
- 兩個 PR 都改到 `data/articles.json` 與 `sitemap.xml` 時容易衝突；先合併其中一個，另一個從最新 `main` 重新套用變更（`strict` 保護要求 PR 分支包含最新 `main`）。

## 內容守則（來自站長的明確決定）

- 不要編造經歷細節（角色、日期、標題、成員數等）；沒有提供就留空或詢問。
- 公開網站不放：感情與性傾向等私人資料、未經同意的第三人全名（例如小論文共同作者）、特殊選才申請的細節（除非站長主動要求）。
- 站長發言的聲明「個人發言僅代表個人立場，與所屬團體無關」固定顯示在頁尾，不要移除。
- 排版：全形標點，中文與英數之間加半形空格，引號用「」。
