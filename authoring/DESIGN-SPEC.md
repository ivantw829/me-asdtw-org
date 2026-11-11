# 文章設計規範 v1

所有文章頁都由 `article-template.html` 產生，樣式全部來自 `assets/css/style.css`。
**文章裡不寫任何 CSS，也不寫 JavaScript。**

## 1. 字體（Google Fonts，已在範本 head 引入，不得更換）

| 用途 | 字體 | 字重 |
|---|---|---|
| 文章標題 `h1`、大標 `h2`、小標 `h3`、引言、金句、摘要 | Noto Serif TC（襯線） | 500 / 700 |
| 內文、清單、圖說、標籤、導覽 | Noto Sans TC（黑體） | 400 / 500 / 700 |
| 程式碼 | 系統等寬字體 | — |

## 2. 色彩（CSS 變數，自動支援深色模式）

| 變數 | 淺色 | 深色 | 用途 |
|---|---|---|---|
| `--bg` | #faf6ee | #1a1612 | 頁面底色（米白紙張感） |
| `--surface` | #fffdf8 | #231e18 | 卡片、參考資料底色 |
| `--text` | #2b2620 | #efe7d8 | 主要文字 |
| `--muted` | #6b6254 | #b3a894 | 次要文字、圖說 |
| `--accent` | #f2c230 | #f2b84b | 識別黃：色塊、線條 |
| `--teal` | #4a7b7f | #7fb0b4 | 識別青綠：圓形、鏤空字、次要裝飾 |
| `--ink` | #26281f | #f8f6ec | 識別墨黑：名字標籤 |
| `--accent-ink` | #8f5500 | #f2b84b | 琥珀褐：連結文字 |

不得直接寫色碼，也不得使用 `style=""`。

### 角色識別（來自角色設定圖，不得更動）
- 奶白底、芥末黃、青綠、墨黑，搭配角色「IVAN」插畫。
- 裝飾語彙：條碼、鏤空大字、× 與 + 符號、黑底名字標籤、圓形色塊。**文章內文不使用這些裝飾**，只在首頁等版面頁使用。
- 圖片位置：`assets/img/`（hero.webp、avatar.webp、favicon.png、og.jpg），文章不得更換。

## 3. 版面

- 內文欄寬約 40rem（約 36 個中文字），置中。
- 內文字級 1.06rem，行距 1.95；第一段 1.12rem。
- 每段 2～5 句，避免超過 8 行的長段落。
- 手機寬度（≥320px）自動單欄，不需另外處理。

## 4. 允許使用的元件

### 標題階層
- `h1`：全文只有一個，放在 `.article-head` 內（範本已有）。
- `h2`：大標，左側琥珀色粗線。**內文最上層一律用 h2**。
- `h3`：小標。`h4`：極少使用。
- 不得跳級（h2 後直接 h4）。

### 文字
- `<strong>`：重點（琥珀螢光筆）。一段最多一處。
- `<a href>`：連結。外部連結加 `target="_blank" rel="noopener"`。
- `<code>`、`<pre><code>`：程式碼。

### 清單
- `<ul>`、`<ol>`：項目 3～7 個為宜。

### 引言
```html
<blockquote>
  <p>引用的話</p>
  <cite>— 出處</cite>
</blockquote>
```

### 圖片
```html
<figure>
  <img src="../images/articles/<slug>/01.webp" alt="描述" loading="lazy" width="1200" height="800">
  <figcaption>圖說（含來源）</figcaption>
</figure>
```
- 寬版圖片：`<figure class="wide">`（比內文欄寬，一篇最多 1～2 張）。
- 必須有 `alt` 與 `figcaption`；`width`／`height` 填實際像素以避免版面跳動。

### 提示框
```html
<div class="callout">
  <p class="callout-title">標題</p>
  <p>內容</p>
</div>
```

### 金句
```html
<p class="pullquote">一句話</p>
```
一篇最多 2 個。

### 分隔線
`<hr>`：會顯示成三個琥珀色圓點，用於場景轉換。

### 表格
標準 `<table><thead>…`，需含 `<th>`。

### 參考資料
範本底部的 `<aside class="article-sources">`，使用 `<ol>`。

## 5. 圖片規範

- 位置：`images/articles/<slug>/`
- 封面：`cover.webp`，**16:9，1600×900**。
- 內文圖：`01.webp`、`02.webp`…，最寬 1600px，單張 ≤ 300KB。
- 格式：webp（照片）或 svg（圖示、圖表）。
- 一律要有 `alt` 文字，描述圖片內容，不是「圖片」二字。
- 使用他人圖片需在 `figcaption` 註明來源與授權。

## 6. 檔案與命名

- 檔名＝ slug：全小寫英文、數字與連字號，例如 `my-first-rally.html`。
- 日期格式：`YYYY-MM-DD`（`datetime` 屬性與 data/articles.json）；顯示用「2026 年 11 月 11 日」。
- 標籤：1～3 個，用繁體中文，同一概念用同一個詞（例如固定用「身心障礙」，不要時而「身障」時而「障礙」）。

## 7. 繁體中文排版

- 全形標點：，。、；：？！「」『』（）。
- 中英文、中文與數字之間加一個半形空格（例如「2026 年」「LGBTQIAA+ 權益」）。
- 引號用「」，書名用〈〉或《》。
- 英文專有名詞保留原大小寫。
