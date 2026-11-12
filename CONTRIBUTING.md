# 工作流程

這是單人維護的個人網站，採 **trunk-based development**：`main` 永遠可部署（推到 `main` 就會自動上線到 me.asdtw.org），所有變更都在短命分支完成，經 PR 與 CI 檢查後 squash merge。

```
main ──●────────●────────●──   （受保護，每個點都可部署）
        \      /  \      /
         feat/…     content/…   （短命分支，合併後自動刪除）
```

## 1. 分支

| 前綴 | 用途 | 範例 |
|---|---|---|
| `content/` | 新文章、經歷、文字修改 | `content/climate-march-essay` |
| `feat/` | 新功能或新頁面 | `feat/timeline-filter` |
| `fix/` | 錯誤修正 | `fix/mobile-nav-wrap` |
| `style/` `refactor/` | 外觀、重構（不改行為） | `style/hero-spacing` |
| `docs/` `chore/` `ci/` | 文件、雜項、自動化 | `chore/update-sitemap` |

- 從最新的 `main` 開分支，**存活不超過幾天**。
- 不直接在 `main` 上提交或推送（本機 hook 會擋）。
- 分支名只用小寫英數與連字號。

## 2. Commit 訊息（約定式 commit）

```
type(scope): 描述
```

- **type**：`feat` `fix` `content` `docs` `style` `refactor` `perf` `chore` `ci` `revert`
- **scope**（選填）：`article` `timeline` `home` `sponsor` `design` `seo` `data` `authoring`
- 描述 72 字內、不加句號，說明「為什麼」比「改了什麼」重要。
- 破壞性變更（例如改 `data/*.json` 結構）在 type 後加 `!`：`feat(data)!: …`。

```
content(article): 新增〈為氣候而走〉心得
fix(timeline): 修正 2025 同志遊行日期
style(home): 調整科技樹手機版間距
```

本機已設 `commit-msg` hook 檢查格式；`.gitmessage` 是提示範本。

## 3. 日常流程

### 一鍵發布（建議）

改好檔案後，一行完成「開分支 → 檢查 → commit → push → 開 PR → 等 CI → 自動 squash merge → 同步本機」：

```bash
bash authoring/ship.sh "content(article): 新增〈標題〉"
```

- 在 `main` 上執行會自動開分支；在功能分支上執行則沿用該分支。
- CI 通過後由 GitHub 自動合併（repo 已啟用 auto-merge），合併後自動刪遠端分支、同步本機並清掉本機舊分支。
- 提交時 pre-commit 會**自動更新 `sitemap.xml`** 並跑 `check.py`，不需要手動跑 `build-sitemap.py`。

### 手動流程

```bash
git switch main && git pull           # 1. 同步（或 bash authoring/sync.sh）
git switch -c content/<名稱>           # 2. 開分支
# …修改、預覽（python3 -m http.server 8000）…
git add -A && git commit              # 3. 提交（hook 會更新 sitemap、檢查、驗證 commit 格式）
git push                              # 4. 推分支（首次自動設定 upstream）
gh pr create --fill                   # 5. 開 PR（標題須符合約定式 commit）
gh pr merge --auto --squash           # 6. CI 通過後自動合併
bash authoring/sync.sh                # 7. 同步本機與 GitHub
```

- **一個 PR 做一件事**。內容與程式碼變更盡量分開，方便回溯與還原。
- Squash merge 後 `main` 是線性歷史，**PR 標題就是 `main` 上的 commit 訊息**。
- 合併到 `main` 後 GitHub Pages 自動部署，約 1～2 分鐘。
- 隨時可跑 `bash authoring/sync.sh`：抓取、`main` 快轉到最新、刪除已合併的本機分支，並確認本機 `main` 與 GitHub 一致。
- Dependabot 每月會自動開 GitHub Actions 版本更新的 PR（標題 `ci(deps): …`），CI 通過後直接合併即可。

## 4. 發新文章

**一條龍（建議）**：照 `authoring/AI-PROMPT.md`「方式 A」讓 AI 產出 Markdown（含 frontmatter）存成原稿，然後：

```bash
bash authoring/publish.sh 原稿.md 圖片資料夾
```

它會依序：產生文章頁（png/jpg 自動轉 webp）→ 登錄 `articles.json` → 開本機預覽等你按 Enter → 開 PR、等 CI、合併 → 驗證線上頁面的 canonical、og 與分享圖。

- **草稿**：frontmatter 寫 `draft: true`，頁面 noindex、不進列表／sitemap；知道網址的人仍看得到，不要放敏感內容。拿掉 `draft` 重跑即正式發布。
- **修改已發布的文章**：改原稿、加 `updated: YYYY-MM-DD`，重跑 `publish.sh`（會顯示「更新於」並更新 sitemap `lastmod`）。
- **18+ 文章**：frontmatter 寫 `adult: true`。
- 只想產生不上線：`python3 authoring/md2article.py 原稿.md --images 圖片資料夾`，之後自己 `bash authoring/ship.sh "content(article): 新增〈標題〉"`。
- **靜態文章列表**：`index.html`、`articles.html` 的文章卡片由 `build-lists.py` 寫進 `<!--lists:start-->…<!--lists:end-->` 之間（給不執行 JS 的爬蟲），commit 時自動更新；不要手改這段。
- **訂閱源**：`feed.xml`（Atom，只放標題、摘要與連結）由 `build-feed.py` 產生，commit 時自動更新；草稿與 18+ 不會出現。
- **CSS／JS 版本碼**：頁面引用 `style.css`／`site.js` 的 `?v=` 由 `build-assets.py` 依檔案內容自動更新，commit 時自動處理，部署後回訪者不會再看到舊樣式。
- 上線驗證可單獨跑：`python3 authoring/verify-live.py <slug>`。
- **IndexNow**：合併到 `main` 且有 `articles/*.html` 變動時，GitHub Action 會等頁面上線後通知 Bing 等搜尋引擎（排除草稿與 18+）。手動補送所有文章：Actions → IndexNow → Run workflow。Google 不支援 IndexNow，靠 sitemap。

## 5. CI 檢查了什麼

`authoring/check.py` 會驗證：JSON 格式與必填欄位、slug／日期格式、文章檔與登錄一致、文章不得有範本占位符或 `style`、`<img>` 必須有 `alt`、站內連結與圖片都存在、sitemap 含所有已發布頁面、robots 與 CNAME 網域一致、草稿頁 noindex、`updated` 與頁面／ld+json 一致、IndexNow 金鑰檔存在。另外 `pr-title` 檢查 PR 標題格式。

## 6. 版本與還原

- **還原**：不改歷史，用 `git revert <commit>` 開 PR（type 用 `revert`）。部署出問題時這是最快的做法。
- **標記版本**：大改版（例如換整體設計）在 `main` 打 tag：`git tag -a v2026.11 -m "…" && git push origin v2026.11`，以日期為版本號。
- 絕對不要在 `main` 上 force push 或 rebase。

## 7. 緊急情況

站長有繞過保護的權限，只在網站壞掉需要立刻處理時使用：
`ALLOW_MAIN_COMMIT=1` / `ALLOW_MAIN_PUSH=1` 可略過本機 hook。事後請補一個 PR 或 issue 說明。

## 8. 初次設定（只需做一次）

```bash
git config core.hooksPath .githooks   # 啟用本機 hooks
git config commit.template .gitmessage
git config pull.ff only && git config push.autoSetupRemote true && git config fetch.prune true
```

GitHub 端（CI 已在 main 跑過一次後）：

```bash
bash authoring/setup-github.sh        # squash merge、自動刪分支、保護 main
```

## 9. 檔案與隱私守則

- 不提交：`.DS_Store`、金鑰、私人信件、未經同意的個資（全名、學校、聯絡方式、可辨識的未成年人照片）。已提交的敏感內容即使刪除，仍留在歷史裡，請在提交前確認。
- 提交信箱使用 GitHub noreply 位址，不用私人信箱。
- 圖片壓縮到單張 300KB 內（webp）再提交。
