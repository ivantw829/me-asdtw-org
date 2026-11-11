#!/usr/bin/env python3
"""網站品質檢查（只用標準函式庫）。本機 pre-commit hook 與 CI 都會執行。

用法：python3 authoring/check.py
有任何錯誤會以非 0 狀態結束。
"""
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def load_json(rel: str):
    try:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except FileNotFoundError:
        err(f"{rel}：檔案不存在")
    except json.JSONDecodeError as e:
        err(f"{rel}：JSON 格式錯誤（{e}）")
    return []


SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CATEGORIES = {"社會倡議", "政策參與", "社會服務", "研習", "研究", "組織參與"}

# ---------- 1. 資料檔 ----------
articles = load_json("data/articles.json")
timeline = load_json("data/timeline.json")

seen = set()
for i, a in enumerate(articles):
    where = f"data/articles.json[{i}]"
    for k in ("slug", "title", "date", "tags", "summary"):
        if not a.get(k):
            err(f"{where}：缺少欄位 {k}")
    slug = a.get("slug", "")
    if slug and not SLUG.match(slug):
        err(f"{where}：slug「{slug}」只能用小寫英數與連字號")
    if slug in seen:
        err(f"{where}：slug「{slug}」重複")
    seen.add(slug)
    if a.get("date") and not DATE.match(a["date"]):
        err(f"{where}：date 格式必須是 YYYY-MM-DD")
    if not isinstance(a.get("tags", []), list):
        err(f"{where}：tags 必須是陣列")
    if a.get("updated"):
        if not DATE.match(a["updated"]):
            err(f"{where}：updated 格式必須是 YYYY-MM-DD")
        elif a.get("date") and a["updated"] < a["date"]:
            err(f"{where}：updated 不能早於 date")
    if a.get("cover") and not (ROOT / a["cover"]).exists():
        err(f"{where}：cover 檔案不存在（{a['cover']}）")

for i, t in enumerate(timeline):
    where = f"data/timeline.json[{i}]"
    for k in ("date", "display", "category", "title"):
        if not t.get(k):
            err(f"{where}：缺少欄位 {k}")
    if t.get("date") and not DATE.match(t["date"]):
        err(f"{where}：date 格式必須是 YYYY-MM-DD")
    if t.get("category") and t["category"] not in CATEGORIES:
        err(f"{where}：category「{t['category']}」不在允許清單 {sorted(CATEGORIES)}")
    if t.get("url") and not t["url"].startswith("https://"):
        err(f"{where}：url 必須以 https:// 開頭")

# ---------- 2. 文章頁 ----------
published = [a for a in articles if not a.get("draft")]
adult_slugs = {a["slug"] for a in articles if a.get("adult")}
draft_slugs = {a["slug"] for a in articles if a.get("draft")}
for a in articles:
    slug = a.get("slug")
    page = ROOT / "articles" / f"{slug}.html"
    if not page.exists():
        err(f"articles/{slug}.html：articles.json 有登錄但檔案不存在")

for page in sorted((ROOT / "articles").glob("*.html")):
    rel = page.relative_to(ROOT).as_posix()
    text = page.read_text(encoding="utf-8")
    slug = page.stem
    if slug not in seen:
        err(f"{rel}：檔案存在但沒有登錄在 data/articles.json")
    gated = "data-age-gate" in text
    if slug in adult_slugs:
        if not gated:
            err(f"{rel}：articles.json 標為 adult，但缺少 <article data-age-gate>（請執行 python3 authoring/mark-adult.py {slug}）")
        if "age-noscript" not in text:
            err(f"{rel}：成人文章缺少 noscript 說明")
        if not re.search(r'<meta name="robots" content="[^"]*noindex', text):
            err(f"{rel}：成人文章必須 noindex")
        if 'name="rating" content="adult"' not in text or "RTA-5042-1996-1400-1577-RTA" not in text:
            err(f"{rel}：成人文章缺少分級標籤（rating: adult 與 RTA）")
    if slug in draft_slugs and not re.search(r'<meta name="robots" content="[^"]*noindex', text):
        err(f"{rel}：草稿（draft）頁面必須 noindex")
    if gated and slug not in adult_slugs:
        err(f"{rel}：有 data-age-gate 但 articles.json 沒標 adult（請在 data/articles.json 加 \"adult\": true，或用 mark-adult.py）")
    if f'data-slug="{slug}"' not in text:
        err(f'{rel}：缺少 data-slug="{slug}"（必須與檔名一致）')
    if re.search(r"\{\{.+?\}\}", text):
        err(f"{rel}：還有範本占位符 {{{{…}}}} 沒有替換")
    if re.search(r"\sstyle\s*=", text) or "<style" in text:
        err(f"{rel}：文章不得使用 style 屬性或 <style>（見 authoring/DESIGN-SPEC.md）")
    if len(re.findall(r"<script\b(?![^>]*application/ld\+json)", text)) != 2:
        err(f"{rel}：<script> 只能有範本中的 2 個（結構化資料 ld+json 不計）")
    if len(re.findall(r"<h1\b", text)) != 1:
        err(f"{rel}：必須恰好有一個 <h1>")
    for m in re.finditer(r"<img\b[^>]*>", text):
        tag = m.group(0)
        if not re.search(r'\salt="[^"]+"', tag):
            err(f"{rel}：<img> 缺少非空的 alt：{tag[:60]}")

# ---------- 3. 站內連結與資源 ----------
SKIP = ("http://", "https://", "mailto:", "tel:", "#", "data:", "javascript:")
pages = [p for p in ROOT.glob("*.html")] + list((ROOT / "articles").glob("*.html"))
for page in sorted(pages):
    rel = page.relative_to(ROOT).as_posix()
    text = page.read_text(encoding="utf-8")
    for ref in re.findall(r'(?:href|src)="([^"]*)"', text):
        if not ref or ref.startswith(SKIP) or "{{" in ref:
            continue
        path = re.split(r"[?#]", ref)[0]
        target = (ROOT / path.lstrip("/")) if path.startswith("/") else (page.parent / path)
        if path.endswith("/") or path == "":
            target = target / "index.html"
        if not target.resolve().exists():
            err(f"{rel}：找不到連結目標「{ref}」")

# ---------- 3.5 CSS／JS 版本碼（快取） ----------
import hashlib
for rel, pat in (("assets/css/style.css", r'href="[^"?#]*assets/css/style\.css(\?v=[0-9a-f]{8})?"'),
                 ("assets/js/site.js", r'src="[^"?#]*assets/js/site\.js(\?v=[0-9a-f]{8})?"')):
    ver = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:8]
    for page in sorted(ROOT.glob("*.html")) + sorted((ROOT / "articles").glob("*.html")):
        for m in re.finditer(pat, page.read_text(encoding="utf-8")):
            if m.group(1) != f"?v={ver}":
                err(f"{page.relative_to(ROOT).as_posix()}：{rel} 的版本碼不是最新（應為 ?v={ver}），請執行 python3 authoring/build-assets.py")

# ---------- 4. 網域、robots、sitemap ----------
PAGE_LIST = json.loads((ROOT / "authoring" / "pages.json").read_text(encoding="utf-8"))
listed = {pg["file"] for pg in PAGE_LIST}
for f in sorted(ROOT.glob("*.html")):
    if f.name != "404.html" and f.name not in listed:
        err(f"{f.name}：尚未登錄在 authoring/pages.json（sitemap 與分享圖會漏掉它）")
for pg in PAGE_LIST:
    if not (ROOT / pg["file"]).exists():
        err(f"authoring/pages.json：{pg['file']} 不存在")

cname_file = ROOT / "CNAME"
domain = cname_file.read_text(encoding="utf-8").strip() if cname_file.exists() else ""
if not domain:
    err("CNAME：缺少或是空的")
else:
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8") if (ROOT / "robots.txt").exists() else ""
    if f"Sitemap: https://{domain}/sitemap.xml" not in robots:
        err(f"robots.txt：Sitemap 網域與 CNAME（{domain}）不一致")
    sm_file = ROOT / "sitemap.xml"
    if not sm_file.exists():
        err("sitemap.xml：不存在，請執行 python3 authoring/build-sitemap.py")
    else:
        sitemap = sm_file.read_text(encoding="utf-8")
        need = [f"https://{domain}/{pg['path']}" for pg in PAGE_LIST]
        need += [f"https://{domain}/articles/{a['slug']}.html" for a in published if not a.get("adult")]
        for a in published:
            if a.get("adult") and f"/articles/{a['slug']}.html" in sitemap:
                err(f"sitemap.xml：成人文章 {a['slug']} 不應出現在 sitemap")
        for url in need:
            if f"<loc>{url}</loc>" not in sitemap:
                err(f"sitemap.xml：缺少 {url}（請執行 python3 authoring/build-sitemap.py）")

# ---------- 4.5 IndexNow 金鑰檔 ----------
keys = [f for f in ROOT.glob("*.txt") if re.fullmatch(r"[0-9a-f]{32}", f.stem)]
if len(keys) != 1:
    err(f"IndexNow 金鑰檔：根目錄應該恰好有 1 個 <32 位十六進位>.txt（目前 {len(keys)} 個）")
elif keys[0].read_text(encoding="utf-8").strip() != keys[0].stem:
    err(f"{keys[0].name}：內容必須等於檔名（金鑰本身）")

# ---------- 4.6 Atom 訂閱源 ----------
if domain:
    import xml.etree.ElementTree as ET
    ATOM = "{http://www.w3.org/2005/Atom}"
    feed_file = ROOT / "feed.xml"
    if not feed_file.exists():
        err("feed.xml：不存在，請執行 python3 authoring/build-feed.py")
    else:
        try:
            froot = ET.parse(feed_file).getroot()
        except ET.ParseError as e:
            err(f"feed.xml：不是合法 XML（{e}）")
            froot = None
        if froot is not None:
            entries = {e.findtext(f"{ATOM}id"): e for e in froot.findall(f"{ATOM}entry")}
            want = {f"https://{domain}/articles/{a['slug']}.html": a
                    for a in articles if not a.get("draft") and not a.get("adult")}
            for url, a in want.items():
                e = entries.get(url)
                if e is None:
                    err(f"feed.xml：缺少 {url}（請執行 python3 authoring/build-feed.py）")
                elif (e.findtext(f"{ATOM}title") != a["title"] or e.findtext(f"{ATOM}summary") != a["summary"]
                      or not (e.findtext(f"{ATOM}updated") or "").startswith(a.get("updated") or a["date"])):
                    err(f"feed.xml：{a['slug']} 的標題／摘要／更新日期與 articles.json 不一致（請重新執行 build-feed.py）")
            for url in entries.keys() - want.keys():
                err(f"feed.xml：不應出現 {url}（草稿或 18+ 文章必須排除）")
    FEED_TAG = f'<link rel="alternate" type="application/atom+xml" title="賴奕帆｜文章" href="https://{domain}/feed.xml">'
    for page in sorted(ROOT.glob("*.html")) + sorted((ROOT / "articles").glob("*.html")):
        if FEED_TAG not in page.read_text(encoding="utf-8"):
            err(f"{page.relative_to(ROOT).as_posix()}：缺少 Atom 訂閱源的 autodiscovery <link>（見 index.html 的 <head>）")

# ---------- 5. 社群分享（Open Graph / Twitter Card / 結構化資料） ----------
def jpeg_size(path: pathlib.Path):
    """讀取 JPEG 尺寸（不依賴外部套件）。"""
    data = path.read_bytes()
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        length = int.from_bytes(data[i + 2:i + 4], "big")
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + length
    return None


def meta(text: str, key: str, attr: str = "property"):
    m = re.search(rf'<meta {attr}="{re.escape(key)}" content="([^"]*)"', text)
    return html.unescape(m.group(1)) if m else None


if domain:
    base = f"https://{domain}"
    by_slug = {a.get("slug"): a for a in articles}
    for page in sorted(pages):
        rel = page.relative_to(ROOT).as_posix()
        if rel == "404.html":
            continue
        text = page.read_text(encoding="utf-8")
        path = "" if rel == "index.html" else rel
        want_url = f"{base}/{path}"
        canon = re.search(r'<link rel="canonical" href="([^"]*)"', text)
        if not canon or canon.group(1) != want_url:
            err(f"{rel}：canonical 應為 {want_url}")
        for key in ("og:title", "og:description", "og:url", "og:image", "og:image:alt", "og:type", "og:site_name", "og:locale"):
            if not meta(text, key):
                err(f"{rel}：缺少 {key}")
        for key in ("twitter:title", "twitter:description", "twitter:image", "twitter:image:alt"):
            if not meta(text, key, "name"):
                err(f"{rel}：缺少 {key}")
        if meta(text, "twitter:card", "name") != "summary_large_image":
            err(f"{rel}：twitter:card 必須是 summary_large_image")
        if meta(text, "og:url") != want_url:
            err(f"{rel}：og:url 應為 {want_url}")
        if meta(text, "og:image") != meta(text, "twitter:image", "name"):
            err(f"{rel}：og:image 與 twitter:image 不一致")
        if (meta(text, "og:image:width"), meta(text, "og:image:height")) != ("1200", "630"):
            err(f"{rel}：og:image:width/height 必須是 1200/630")
        desc = re.search(r'<meta name="description" content="([^"]*)"', text)
        if desc and meta(text, "og:description") != html.unescape(desc.group(1)):
            err(f"{rel}：og:description 與 description 不一致")
        img = meta(text, "og:image") or ""
        if not img.startswith(base + "/"):
            err(f"{rel}：og:image 必須是 {base}/ 開頭的完整網址")
        else:
            f = ROOT / img[len(base) + 1:]
            if not f.exists():
                err(f"{rel}：分享圖不存在（{img[len(base) + 1:]}），請執行 python3 authoring/build-og.py")
            elif jpeg_size(f) != (1200, 630):
                err(f"{rel}：分享圖尺寸必須是 1200×630（目前 {jpeg_size(f)}）")
        for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
            try:
                json.loads(blob)
            except json.JSONDecodeError as e:
                err(f"{rel}：結構化資料（ld+json）不是合法 JSON（{e}）")
        # 文章專屬：與 data/articles.json 一致
        if rel.startswith("articles/") and page.stem in by_slug:
            a = by_slug[page.stem]
            if meta(text, "og:type") != "article":
                err(f"{rel}：og:type 必須是 article")
            if meta(text, "og:title") != a.get("title"):
                err(f"{rel}：og:title 與 articles.json 的 title 不一致")
            if meta(text, "og:description") != a.get("summary"):
                err(f"{rel}：og:description 與 articles.json 的 summary 不一致")
            if meta(text, "article:published_time") != a.get("date"):
                err(f"{rel}：article:published_time 與 articles.json 的 date 不一致")
            want_img = f"{base}/images/og/adult.jpg" if a.get("adult") else f"{base}/images/og/{page.stem}.jpg"
            if meta(text, "og:image") != want_img:
                err(f"{rel}：og:image 應為 {want_img}")
            if a.get("updated") and f'<time datetime="{a["updated"]}">' not in text:
                err(f"{rel}：articles.json 有 updated，頁面缺少「更新於」日期")
            if not a.get("updated") and "更新於" in text:
                err(f"{rel}：頁面有「更新於」但 articles.json 沒有 updated")
            tags = re.findall(r'<meta property="article:tag" content="([^"]*)"', text)
            if [html.unescape(t) for t in tags] != a.get("tags", []):
                err(f"{rel}：article:tag 與 articles.json 的 tags 不一致")
            ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
            if not ld:
                err(f"{rel}：缺少文章結構化資料（ld+json）")
            else:
                try:
                    obj = json.loads(ld.group(1))
                    if obj.get("headline") != a.get("title") or obj.get("datePublished") != a.get("date"):
                        err(f"{rel}：ld+json 的 headline／datePublished 與 articles.json 不一致")
                    if obj.get("dateModified") != (a.get("updated") or a.get("date")):
                        err(f"{rel}：ld+json 的 dateModified 應為 updated（沒有就是 date）")
                except json.JSONDecodeError:
                    pass

# ---------- 6. 樣式數值同步（style.css ⇄ 兩份設計文件） ----------
css = (ROOT / "assets" / "css" / "style.css").read_text(encoding="utf-8")


def css_block(selector: str) -> dict:
    """取出某個選擇器第一個 {…} 內的 --變數（只含色碼與簡單值）。"""
    m = re.search(r"^[ \t]*" + re.escape(selector) + r"\s*\{(.*?)\n\s*\}", css, re.S | re.M)
    return dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b", m.group(1))) if m else {}


light = css_block(":root")
dark_a = css_block(':root[data-theme="dark"]')
dark_b = css_block(':root:not([data-theme="light"])')
if not (light and dark_a and dark_b):
    err("style.css：找不到 :root 或深色變數區塊，無法檢查樣式同步")
else:
    for k in sorted(set(dark_a) | set(dark_b)):
        if dark_a.get(k, "").lower() != dark_b.get(k, "").lower():
            err(f"style.css：深色變數 {k} 在兩個區塊不一致（{dark_a.get(k)} ≠ {dark_b.get(k)}）")
    DOC_TOKENS = ("--bg", "--surface", "--text", "--muted", "--accent", "--teal", "--ink", "--accent-ink")
    for doc in ("authoring/DESIGN-SPEC.md", "authoring/STYLE-PROMPT.md"):
        rows = {m.group(1): m.group(0).lower() for m in
                re.finditer(r"^\|\s*`(--[\w-]+)`.*$", (ROOT / doc).read_text(encoding="utf-8"), re.M)}
        for t in DOC_TOKENS:
            row = rows.get(t)
            if row is None:
                err(f"{doc}：色票表缺少 {t} 那一列")
                continue
            for name, vals in (("淺色", light), ("深色", dark_a)):
                v = vals.get(t)
                if v and v.lower() not in row:
                    err(f"{doc}：{t} 的{name}值應為 {v}（style.css 改了色票，這份文件要一併更新）")

# ---------- 結果 ----------
if errors:
    print(f"發現 {len(errors)} 個問題：")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
print(f"檢查通過：{len(published)} 篇文章、{len(timeline)} 筆經歷、{len(pages)} 個頁面。")
