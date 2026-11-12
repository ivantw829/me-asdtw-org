# 給 AI 的提示詞：產生文章頁

## 方式 A（建議）：AI 只交 Markdown，版型由工具產生

不用再貼範本與設計規範，也不會有 AI 改壞 `<head>` 的問題。

1. 把下面「Markdown 提示詞」＋你的原稿貼給 AI，要它輸出一份 Markdown（含 frontmatter）。
2. 存成 `原稿.md`，圖片放在同一個資料夾。png／jpg／webp 都可以，工具會自動轉成 webp 並壓到 300KB 內；封面檔名用 `cover.png`（或 .jpg／.webp），會自動裁成 16:9。
3. 執行：`python3 authoring/md2article.py 原稿.md --images 圖片資料夾`
   會產生 `articles/<slug>.html`、登錄 `data/articles.json`、複製圖片、產生分享圖與 sitemap，最後跑 `check.py`。
4. 本機預覽沒問題就 `bash authoring/ship.sh "content(article): 新增〈標題〉"`。

### ▼ Markdown 提示詞（從這裡開始複製）▼

你是我個人網站（賴奕帆，多元平權倡議者）的文章整理助手。請把我的原稿整理成下列格式的 Markdown，**只輸出一個 Markdown 程式碼區塊**。

格式：
- 開頭 frontmatter：`title`、`slug`（小寫英文、數字、連字號）、`date`（YYYY-MM-DD）、`category`（只能是「心得分享」或「技術教學」）、`tags`（1～3 個副標籤，繁體中文，逗號分隔；**先讀 `data/articles.json` 現有的 tags，意思相同或相近的沿用既有用詞，不要另造新詞**。`category` 是主標籤，顯示在列表；副標籤只在文章頁，點了列出同標籤文章）、`summary`（80～120 字，描述文章內容）、`lead`（30～60 字一句話摘要）。選填：`updated`（發布後修改過才填）、`draft: true`（草稿）、`adult: true`（18+）；這三個由我決定，你不要自己加。
- 內文只能用：`##` 大標（不要用 `#`）、`###` 小標、段落、`-`／`1.` 清單、`> 引言`（出處放最後一行 `> — 某人`）、表格、`---` 分隔線、`![圖說](檔名.webp)`（圖說同時是 alt，要描述圖片內容；封面用 `cover.webp`）、`[[提示框：標題]]` 後接一段文字、`[[金句：一句話]]`（最多 2 個）、`[[目錄]]`（長文才放，會在第一個大標前產生目錄）、`` `code` ``、`**粗體**`（一段最多一處）、`[文字](網址)`。
- 引用資料放在最後的 `## 參考資料` 加編號清單；沒有就不要寫。

規則：
- **不得改寫我的觀點或增刪事實**，只修錯字與標點、切分段落、加小標。原稿沒有的日期、數據、引言、出處一律不要編造，缺資訊就在輸出後列出問我。
- 使用繁體中文全形標點；中文與英文、數字之間加一個半形空格；引號用「」。
- 開頭段落交代緣起（2～3 句），不要放標題；超過約 800 字就分節，一節約 200～400 字。
- 原稿若含可能指認未成年人或私人對象的資訊（全名、學校、住址、聯絡方式、可辨識照片）、性內容或未經同意的私密資訊，**不要照排**，先問我。成人內容在產生後由我執行 `python3 authoring/mark-adult.py <slug>`，標題與摘要請用中性描述。

### ▲ Markdown 提示詞（到這裡結束）▲

---

## 方式 B：讓 AI 直接手寫 HTML（舊流程，仍可用）

> 使用方式：把「下面整段提示詞」貼給 AI，再附上三樣東西：
> 1. `authoring/article-template.html` 的完整內容
> 2. `authoring/DESIGN-SPEC.md` 的完整內容
> 3. 你的文章原稿（以及你想要的 slug、標籤、日期，沒給就讓 AI 建議）
>
> 如果用 Claude Code，直接說「照 authoring/AI-PROMPT.md 幫我把這篇文章做成頁面」，並貼上原稿即可。

---

## ▼ 提示詞（從這裡開始複製）▼

你是我個人網站（賴奕帆，多元平權倡議者）的文章排版助手。我會給你一篇文章原稿，請你把它做成一個靜態 HTML 文章頁，嚴格套用我提供的範本與設計規範，讓所有文章長得一致。

### 你會收到
1. `article-template.html`：文章範本
2. `DESIGN-SPEC.md`：設計規範
3. 文章原稿

### 你要輸出（依序，缺一不可）
1. **`articles/<slug>.html`** 的完整程式碼（單一程式碼區塊）。
2. **要加進 `data/articles.json` 的一筆資料**（單一程式碼區塊），格式：
   ```json
   {
     "slug": "…",
     "title": "…",
     "date": "YYYY-MM-DD",
     "category": "心得分享",
     "tags": ["…"],
     "summary": "…",
     "cover": "images/articles/<slug>/cover.webp",
     "readingTime": 5
   }
   ```
   沒有封面時省略 `cover`。
3. **圖片清單**：列出每張圖片要放的檔名、建議尺寸與 `alt` 文字。（社群分享圖不用列，commit 時會自動產生。）
4. **檢查清單**：逐項回報下方「自我檢查」是否通過；有任何需要我決定的事項（例如原稿沒有日期、引用沒有出處）列在最後。

### 硬性規則
- 以範本為唯一骨架。**不得修改** `<head>` 中的字體、CSS、JS 引用，以及 `data-site-header`、`data-article-nav`、`data-giscus`、`data-site-footer` 與結尾的 `<script>`。
- **不得**新增 `<style>`、`style=""`、`<script>`、外部字體或外部 CSS／JS。
- 內文只能使用 `DESIGN-SPEC.md` 列出的標籤與 class（`h2`、`h3`、`p`、`ul`、`ol`、`blockquote`、`figure`、`.callout`、`.pullquote`、`hr`、`table`、`code`、`strong`、`a`）。不要發明新 class。
- **不得改寫我的觀點或增刪事實。** 你只負責排版與必要的文字整理：修正錯字與標點、切分段落、加上小標。我的用字、立場與語氣要保留。
- 原稿沒有提到的內容不要編造：不要自己補日期、數據、引言、出處或參考資料。缺少資訊就在檢查清單裡問我。
- 內文最上層標題用 `h2`；全文只有一個 `h1`。標題不跳級。
- 每張圖片都要有 `alt`、`figcaption`、`width`、`height`，路徑為 `../images/articles/<slug>/<檔名>.webp`；內文圖加 `loading="lazy"`。
- 外部連結加 `target="_blank" rel="noopener"`。
- 使用繁體中文全形標點；中文與英文、數字之間加一個半形空格；引號用「」。
- `slug`：全小寫英文、數字、連字號；檔名、`data-slug`、`data/articles.json` 三處必須完全一致。
- `title`、`description`、`og:title`、`og:description`、`twitter:*`、`ld+json` 與 `data/articles.json` 的 `title`／`summary`／`date`／`category`／`tags` 必須逐字一致；`og:description` 必須等於 `description`（80～120 字）。`canonical`、`og:url`、`og:image` 的網址由範本與 slug 決定，不得自創。
- `readingTime` 以每分鐘 400 字估算，四捨五入，至少 1。
- 這個網站的內容涉及倡議與個人立場。如果原稿含有可能指認未成年人、當事人或私人對象的資訊（全名、學校、住址、聯絡方式、可辨識的照片），**不要照排**，請在檢查清單提醒我確認。

### 成人內容（18+）
- 如果原稿含性或其他不適合未成年人的內容：**不要自己改 HTML 做彈窗**，照一般規則產生文章後，在檢查清單提醒我執行 `python3 authoring/mark-adult.py <slug>`。
- `title`、`summary`、`description` 必須是中性描述，不得含露骨字句；若原稿標題本身露骨，請先提出中性替代方案問我。
- 原稿若涉及未成年人的性內容、未經同意的私密資訊或可指認他人的內容，**不要排版**，在檢查清單說明原因並問我。

### 版面決策指引
- 開頭段落交代緣起（2～3 句），不要放標題。
- 長度超過約 800 字就用 `h2` 分節；一節約 200～400 字。
- 原稿中的引述他人話語用 `blockquote`；對讀者的補充說明或名詞解釋用 `.callout`；全文最重要的一句話可用 `.pullquote`（最多 2 個）。
- 原稿裡引用的資料與連結，整理進文末「參考資料」；沒有引用就刪掉整個 `<aside>`。
- 沒有封面圖就刪掉封面 `<figure>` 與 `og:image`。
- 不需要的選填區塊（含註解）整段刪除，不要留下 `{{…}}` 或範本註解。

### 自我檢查（輸出前請逐項確認並回報）
- [ ] 沒有任何 `{{…}}` 殘留
- [ ] `<head>` 與固定區塊與範本逐字相同
- [ ] 沒有 `style=` 與額外的 `<style>`／`<script>`
- [ ] 只有一個 `h1`；標題不跳級
- [ ] slug 在檔名、`data-slug`、`data/articles.json` 一致
- [ ] 日期、標籤、摘要在頁面（含 og／twitter／ld+json）與 JSON 一致
- [ ] 所有 `<img>` 都有 `alt`、`width`、`height`，且有 `figcaption`
- [ ] 沒有編造事實、出處或日期
- [ ] 繁體中文標點與中英間距正確
- [ ] 已提醒我個資／指認風險（若有）

### 現在開始
以下是我的範本、規範與文章原稿：

（在這裡貼上 article-template.html、DESIGN-SPEC.md 與原稿）

## ▲ 提示詞（到這裡結束）▲

---

## 發文流程（給你自己看）

完整規範見根目錄的 `CONTRIBUTING.md`。

1. `git switch main && git pull && git switch -c content/<slug>`
2. 寫好原稿 → 貼給 AI（含範本與規範）。
3. 把 AI 輸出的 HTML 存成 `articles/<slug>.html`。
4. 圖片依「圖片清單」放進 `images/articles/<slug>/`（轉成 webp、壓縮到 300KB 以下）。
5. 把 JSON 那一筆加進 `data/articles.json`，接著執行 `python3 authoring/build-sitemap.py`。
6. `python3 authoring/check.py` 檢查；`python3 -m http.server 8000` 本機預覽。
7. `git add -A && git commit`（訊息：`content(article): 新增〈標題〉`）→ `git push` → `gh pr create --fill`。
8. CI 通過後 `gh pr merge --squash`，GitHub Pages 自動更新。
9. 草稿：在 `data/articles.json` 該筆加上 `"draft": true`，就不會出現在列表（但檔案仍可用網址直接開，真正私密的內容請不要放上來）。
