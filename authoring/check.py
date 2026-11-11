#!/usr/bin/env python3
"""網站品質檢查（只用標準函式庫）。本機 pre-commit hook 與 CI 都會執行。

用法：python3 authoring/check.py
有任何錯誤會以非 0 狀態結束。
"""
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
    if f'data-slug="{slug}"' not in text:
        err(f'{rel}：缺少 data-slug="{slug}"（必須與檔名一致）')
    if "{{" in text or "}}" in text:
        err(f"{rel}：還有範本占位符 {{{{…}}}} 沒有替換")
    if re.search(r"\sstyle\s*=", text) or "<style" in text:
        err(f"{rel}：文章不得使用 style 屬性或 <style>（見 authoring/DESIGN-SPEC.md）")
    if len(re.findall(r"<script\b", text)) != 2:
        err(f"{rel}：<script> 只能有範本中的 2 個")
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

# ---------- 4. 網域、robots、sitemap ----------
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
        need = [f"https://{domain}/{p}" for p in ("", "about.html", "timeline.html", "articles.html", "contact.html", "sponsor.html")]
        need += [f"https://{domain}/articles/{a['slug']}.html" for a in published]
        for url in need:
            if f"<loc>{url}</loc>" not in sitemap:
                err(f"sitemap.xml：缺少 {url}（請執行 python3 authoring/build-sitemap.py）")

# ---------- 結果 ----------
if errors:
    print(f"發現 {len(errors)} 個問題：")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
print(f"檢查通過：{len(published)} 篇文章、{len(timeline)} 筆經歷、{len(pages)} 個頁面。")
