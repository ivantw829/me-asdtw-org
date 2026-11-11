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

```bash
git switch main && git pull           # 1. 同步
git switch -c content/<名稱>           # 2. 開分支
# …修改、預覽（python3 -m http.server 8000）…
python3 authoring/check.py            # 3. 自我檢查（commit 時也會自動跑）
git add -A && git commit              # 4. 提交（遵守 commit 格式）
git push                              # 5. 推分支（首次自動設定 upstream）
gh pr create --fill                   # 6. 開 PR（標題須符合約定式 commit）
# CI（check、pr-title）通過 → 審視 diff →
gh pr merge --squash                  # 7. squash merge，分支自動刪除
```

- **一個 PR 做一件事**。內容與程式碼變更盡量分開，方便回溯與還原。
- Squash merge 後 `main` 是線性歷史，**PR 標題就是 `main` 上的 commit 訊息**。
- 合併到 `main` 後 GitHub Pages 自動部署，約 1～2 分鐘。

## 4. 發新文章

1. `git switch -c content/<slug>`
2. 照 `authoring/AI-PROMPT.md` 產生 `articles/<slug>.html`，放圖片到 `images/articles/<slug>/`。
3. 在 `data/articles.json` 新增一筆，執行 `python3 authoring/build-sitemap.py`。
4. `python3 authoring/check.py` 通過 → commit：`content(article): 新增〈標題〉` → PR。
5. 要先寫不公開：在 `articles.json` 該筆加 `"draft": true`。

## 5. CI 檢查了什麼

`authoring/check.py` 會驗證：JSON 格式與必填欄位、slug／日期格式、文章檔與登錄一致、文章不得有範本占位符或 `style`、`<img>` 必須有 `alt`、站內連結與圖片都存在、sitemap 含所有已發布頁面、robots 與 CNAME 網域一致。另外 `pr-title` 檢查 PR 標題格式。

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
