#!/usr/bin/env python3
"""Markdown → 文章頁。把一份帶 frontmatter 的 Markdown 套進 article-template.html。

做的事（輸出仍是提交進 repo 的靜態 HTML，部署與 SEO 不變）：
  1. 產生 articles/<slug>.html（版型、meta、ld+json 全部來自範本，不會被改壞）
  2. 新增／更新 data/articles.json 的該筆資料
  3. 處理圖片（給 --images 時）：png／jpg 自動用 cwebp 轉成 webp 放到 images/articles/<slug>/，
     內文圖最寬 1600、封面（cover）裁成 16:9 1600×900，品質自動調整到 ≤300KB；webp 原檔直接複製
  4. 產生分享圖、sitemap、feed.xml，最後執行 check.py

用法：
  python3 authoring/md2article.py 原稿.md [--images 圖片資料夾]

原稿格式：
  ---
  title: 文章標題
  slug: my-article            # 小寫英文、數字、連字號
  date: 2026-11-11
  category: 心得分享          # 分類，只能是 心得分享／技術教學（定義在 check.py 的 ARTICLE_CATEGORIES）；articles 頁依此篩選
  tags: 標籤1, 標籤2          # 1～3 個，只顯示在文章頁與 meta，不當篩選
  summary: 80～120 字摘要，會同時用在 description／og:description／articles.json
  lead: 一句話摘要（30～60 字），顯示在標題下
  readingTime: 6              # 選填，沒填就以每分鐘 400 字估算
  updated: 2026-12-01         # 選填：發布後修改過才填。寫入「更新於」、dateModified 與 sitemap lastmod
  draft: true                 # 選填：草稿。不進列表／sitemap／feed，頁面 noindex；拿掉後重跑就是正式發布
  adult: true                 # 選填：18+ 文章，自動套用 mark-adult.py
  ---
  內文 Markdown。支援：
    ## 大標、### 小標、段落、- 清單、1. 清單、| 表格 |、> 引言、--- 分隔線、```程式碼區塊```
    ![圖說](檔名.png)         # 圖說同時當 alt；png／jpg／webp 都可，輸出一律 .webp；cover 開頭的檔名（cover.png 等）當作封面
    [[提示框：標題]] 下一段文字（到空行為止）
    [[金句：一句話]]
    [[目錄]]                  # 在第一個大標前產生目錄
    `code`、**粗體**、[文字](網址)、裸網址（自動變連結）
    最後可放 `## 參考資料` + 編號清單，會變成文末參考資料區塊
"""
import difflib
import html
import json
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import urllib.parse

ARTICLE_CATEGORIES = {"心得分享", "技術教學"}  # 與 check.py 同步

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "authoring" / "article-template.html"
ARTICLES = ROOT / "data" / "articles.json"


def die(msg: str) -> None:
    sys.exit(f"✗ {msg}")


MAX_IMG_KB = 300
MAX_W = 1600
IMG_EXT = (".png", ".jpg", ".jpeg")


def webp_size(path: pathlib.Path):
    d = path.read_bytes()[:40]
    if d[:4] != b"RIFF" or d[8:12] != b"WEBP":
        return None
    kind = d[12:16]
    if kind == b"VP8 ":
        w, h = struct.unpack("<HH", d[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if kind == b"VP8L":
        b = struct.unpack("<I", d[21:25])[0]
        return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    if kind == b"VP8X":
        return int.from_bytes(d[24:27], "little") + 1, int.from_bytes(d[27:30], "little") + 1
    return None


def src_size(path: pathlib.Path):
    """來源圖片尺寸（用 macOS sips；專案本來就需要 sips 來產生分享圖）。"""
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
                         capture_output=True, text=True).stdout
    w = re.search(r"pixelWidth: (\d+)", out)
    h = re.search(r"pixelHeight: (\d+)", out)
    if not (w and h):
        die(f"讀不到圖片尺寸：{path}")
    return int(w.group(1)), int(h.group(1))


def to_webp(src: pathlib.Path, dst: pathlib.Path, cover: bool) -> None:
    cwebp = shutil.which("cwebp")
    if not cwebp:
        die("找不到 cwebp，請先安裝：brew install webp（或自行先把圖片轉成 webp 再放進 --images 資料夾）")
    w, h = src_size(src)
    args = []
    if cover:
        if w * 9 > h * 16:  # 太寬：左右置中裁切
            cw = round(h * 16 / 9)
            args += ["-crop", str((w - cw) // 2), "0", str(cw), str(h)]
        else:  # 太高：上下置中裁切
            ch = round(w * 9 / 16)
            args += ["-crop", "0", str((h - ch) // 2), str(w), str(ch)]
        args += ["-resize", str(MAX_W), "900"]
        if w < MAX_W:
            print(f"! {src.name}：寬度只有 {w}px，封面放大到 {MAX_W}px 會變糊")
    elif w > MAX_W:
        args += ["-resize", str(MAX_W), "0"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    for q in (88, 80, 72, 64, 56, 48, 40):
        subprocess.run([cwebp, "-quiet", "-q", str(q), *args, str(src), "-o", str(dst)], check=True)
        if dst.stat().st_size <= MAX_IMG_KB * 1024:
            return
    print(f"! {dst.name}：壓到最低品質仍有 {dst.stat().st_size // 1024}KB（建議 ≤{MAX_IMG_KB}KB），請換較小的原圖")


def normalize_refs(body: str) -> str:
    """![](x.png) → ![](x.webp)；封面（cover.*）一律變 cover.webp。"""
    def fix(m):
        name = m.group(2)
        if re.match(r"https?://", name):
            return m.group(0)
        stem, ext = (name.rsplit(".", 1) + [""])[:2]
        if ext.lower() in ("png", "jpg", "jpeg", "webp"):
            name = f"{stem}.webp"
        return f"![{m.group(1)}]({name})"
    return re.sub(r"!\[(.*?)\]\(([^)]*)\)", fix, body)


def prepare_images(body: str, slug: str, images_dir):
    """依原稿引用的圖片處理檔案，回傳 {檔名: (寬, 高)}。"""
    refs = sorted(set(re.findall(r"!\[.*?\]\(([^)/]+\.webp)\)", body)))
    out_dir = ROOT / "images" / "articles" / slug
    dims = {}
    for f in refs:
        dst = out_dir / f
        stem = f[:-5]
        if images_dir:
            src = next((c for c in [images_dir / f, *[images_dir / (stem + e) for e in IMG_EXT],
                                    *[images_dir / (stem + e.upper()) for e in IMG_EXT]] if c.exists()), None)
            if src is None:
                print(f"! 在 {images_dir} 找不到 {stem}.(webp|png|jpg)")
            elif src.suffix.lower() == ".webp":
                out_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            else:
                to_webp(src, dst, cover=(f == "cover.webp"))
                print(f"  ✓ {src.name} → {dst.relative_to(ROOT)}（{dst.stat().st_size // 1024}KB）")
        if not dst.exists():
            print(f"! 缺少圖片 images/articles/{slug}/{f}")
            dims[f] = (1600, 900)
            continue
        size = webp_size(dst) or (1600, 900)
        dims[f] = size
        kb = dst.stat().st_size // 1024
        if kb > MAX_IMG_KB:
            print(f"! {f}：{kb}KB 超過建議的 {MAX_IMG_KB}KB")
        if size[0] > MAX_W:
            print(f"! {f}：寬 {size[0]}px 超過 {MAX_W}px")
        if f == "cover.webp" and size != (1600, 900):
            print(f"! cover.webp 應為 1600×900（目前 {size[0]}×{size[1]}）")
    return dims


def tag_warnings(tags, others):
    known = sorted({t for a in others for t in a.get("tags", [])})
    for t in tags:
        if t in known:
            continue
        near = difflib.get_close_matches(t, known, n=1, cutoff=0.6)
        if near:
            print(f"! 標籤「{t}」是新的，但跟既有標籤「{near[0]}」很像，要統一用詞嗎？")


def parse_frontmatter(text: str):
    m = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", text, re.S)
    if not m:
        die("原稿開頭必須有 --- frontmatter ---")
    fm = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()
    return fm, m.group(2)


def inline(t: str) -> str:
    t = re.sub(r"<(https?://[^>\s]+)>", r"\1", t)
    t = html.escape(t, quote=False)
    codes = []

    def stash(m):
        codes.append(f"<code>{m.group(1)}</code>")
        return f"\x00{len(codes) - 1}\x00"

    t = re.sub(r"`([^`]+)`", stash, t)

    def link(m):
        href = m.group(2)
        ext = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
        return f'<a href="{href}"{ext}>{m.group(1)}</a>'

    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r'(?<![">=])(https?://[^\s<）」，。、；：]+)',
               lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>', t)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], t)


def convert(body: str, slug: str, dims=None):
    """回傳 (內文 HTML, 封面圖說, 參考資料清單, 圖片檔名集合)"""
    lines = body.strip("\n").split("\n")
    out, h2s, images = [], [], set()
    cover = None
    sources = None
    want_toc = False
    i = 0

    def figure(alt, fname):
        images.add(fname)
        a = html.escape(alt)
        w, h = (dims or {}).get(fname, (1600, 900))
        return (f'<figure>\n  <img src="../images/articles/{slug}/{fname}" alt="{a}" loading="lazy" '
                f'width="{w}" height="{h}">\n  <figcaption>{a}</figcaption>\n</figure>')

    while i < len(lines):
        l = lines[i]
        s = l.strip()
        if not s:
            i += 1
            continue
        if s.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(code), quote=False) + "</code></pre>")
            continue
        if s == "[[目錄]]":
            want_toc = True
            i += 1
            continue
        if s == "---":
            out.append("<hr>")
            i += 1
            continue
        m = re.match(r"!\[(.*?)\]\((.*?)\)$", s)
        if m:
            if m.group(2) == "cover.webp":
                cover = m.group(1)
                images.add("cover.webp")
            else:
                out.append(figure(m.group(1), m.group(2)))
            i += 1
            continue
        m = re.match(r"\[\[提示框：(.*?)\]\]$", s)
        if m:
            i += 1
            ps = []
            while i < len(lines) and lines[i].strip():
                ps.append(lines[i].strip())
                i += 1
            out.append(f'<div class="callout">\n  <p class="callout-title">{inline(m.group(1))}</p>\n'
                       + "\n".join(f"  <p>{inline(p)}</p>" for p in ps) + "\n</div>")
            continue
        m = re.match(r"\[\[金句：(.*?)\]\]$", s)
        if m:
            out.append(f'<p class="pullquote">{inline(m.group(1))}</p>')
            i += 1
            continue
        if s.startswith("## "):
            title = s[3:].strip()
            if title == "參考資料":
                i += 1
                items = []
                while i < len(lines) and not lines[i].startswith("## "):
                    mm = re.match(r"\d+\. (.*)", lines[i].strip())
                    if mm:
                        items.append(mm.group(1))
                    i += 1
                sources = items
                continue
            h2s.append(title)
            if len(h2s) == 1 and want_toc:
                out.append("@@TOC@@")
            out.append(f'<h2 id="s{len(h2s)}">{inline(title)}</h2>')
            i += 1
            continue
        if s.startswith("### "):
            out.append(f"<h3>{inline(s[4:])}</h3>")
            i += 1
            continue
        if s.startswith("**") and s.endswith("**") and s.count("**") == 2:
            out.append(f"<h3>{inline(s[2:-2])}</h3>")  # 整行粗體視為小標
            i += 1
            continue
        if s.startswith(">"):
            qs = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                qs.append(lines[i].strip().lstrip(">").strip())
                i += 1
            cite = None
            if len(qs) > 1 and re.match(r"[—－-]\s*", qs[-1]) and qs[-1].startswith(("—", "－")):
                cite = qs.pop()
            out.append("<blockquote>\n" + "\n".join(f"  <p>{inline(q)}</p>" for q in qs if q)
                       + (f"\n  <cite>{inline(cite)}</cite>" if cite else "") + "\n</blockquote>")
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            cells = lambda r: [c.strip() for c in r.strip("|").split("|")]
            head, rest = cells(rows[0]), [cells(r) for r in rows[2:]]
            out.append("<table>\n  <thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head)
                       + "</tr></thead>\n  <tbody>\n"
                       + "\n".join("    <tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rest)
                       + "\n  </tbody>\n</table>")
            continue
        if re.match(r"(- |\d+\. )", s):
            tag = "ul" if s.startswith("- ") else "ol"
            items = []
            while i < len(lines) and re.match(r"(- |\d+\. )", lines[i].strip()):
                items.append(re.sub(r"^(- |\d+\. )", "", lines[i].strip()))
                i += 1
            out.append(f"<{tag}>\n" + "\n".join(f"  <li>{inline(x)}</li>" for x in items) + f"\n</{tag}>")
            continue
        out.append(f"<p>{inline(s)}</p>")
        i += 1

    toc = ""
    if want_toc and h2s:
        toc = ('<div class="callout">\n  <p class="callout-title">本文目錄</p>\n  <ol>\n'
               + "\n".join(f'    <li><a href="#s{n + 1}">{html.escape(t, quote=False)}</a></li>'
                           for n, t in enumerate(h2s))
               + "\n  </ol>\n</div>")
    main = "\n\n".join(out).replace("@@TOC@@", toc)
    return main, cover, sources, images


def build(fm, body, slug, dims=None):
    main, cover, sources, images = convert(body, slug, dims)
    indent = lambda s, n: "\n".join((" " * n + x if x else x) for x in s.split("\n"))
    tags = [x.strip() for x in re.sub(r"^\[|\]$", "", fm["tags"]).split(",") if x.strip()]
    text_len = len(re.sub(r"\s|<[^>]+>", "", main))
    rt = int(fm["readingTime"]) if fm.get("readingTime") else max(1, round(text_len / 400))
    y, mth, d = fm["date"].split("-")
    updated = fm.get("updated", "")
    t = TEMPLATE.read_text(encoding="utf-8")
    t = re.sub(r"[ \t]*<!--(?!\s*社群分享).*?-->\n?", "", t, flags=re.S)
    a = t.index('<div class="prose">')
    b = t.rindex("      </div>\n", a, t.index("    </article>")) + len("      </div>\n")
    pres = []
    main = re.sub(r"<pre>.*?</pre>", lambda m: pres.append(m.group(0)) or f"@@PRE{len(pres) - 1}@@", main, flags=re.S)
    main = indent(main, 8)
    main = re.sub(r"@@PRE(\d+)@@", lambda m: pres[int(m.group(1))], main)
    t = t[:a] + '<div class="prose">\n\n' + main + "\n\n      </div>\n" + t[b:]
    if sources:
        lis = "\n".join(f"          <li>{inline(x)}</li>" for x in sources)
        t = re.sub(r'(<aside class="article-sources"[^>]*>\s*<h2 id="sources-title">參考資料</h2>\s*<ol>).*?(</ol>)',
                   lambda m: m.group(1) + "\n" + lis + "\n        " + m.group(2), t, flags=re.S)
    else:
        t = re.sub(r'\s*<aside class="article-sources".*?</aside>\n', "\n", t, flags=re.S)
    if cover:
        c = html.escape(cover)
        t = re.sub(r'<figure class="article-cover">.*?</figure>',
                   f'<figure class="article-cover">\n        <img src="../images/articles/{slug}/cover.webp" '
                   f'alt="{c}" width="1600" height="900">\n        <figcaption>{c}</figcaption>\n      </figure>',
                   t, flags=re.S)
    else:
        t = re.sub(r'\s*<figure class="article-cover">.*?</figure>\n', "\n", t, flags=re.S)
    if updated:
        uy, um, ud = updated.split("-")
        t = (t.replace("{{更新日期}}", updated)
              .replace("{{YYYY 年 M 月 D 日（更新）}}", f"{uy} 年 {int(um)} 月 {int(ud)} 日"))
    else:  # 沒改過：整段移除「更新於」，dateModified 回到發布日期
        t = re.sub(r'\s*<span aria-hidden="true">·</span>\s*<span>更新於[^\n]*</span>', "", t)
        t = t.replace("{{更新日期}}", fm["date"])
    if fm.get("draft", "").lower() == "true":
        t = t.replace('content="index, follow, max-image-preview:large"', 'content="noindex, nofollow"', 1)
    t = (t.replace("{{一句話摘要}}", html.escape(fm["lead"], quote=False))
          .replace("{{摘要}}", html.escape(fm["summary"]))
          .replace("{{文章標題}}", html.escape(fm["title"]))
          .replace("{{slug}}", slug)
          .replace("{{YYYY 年 M 月 D 日}}", f"{y} 年 {int(mth)} 月 {int(d)} 日")
          .replace("{{YYYY-MM-DD}}", fm["date"])
          .replace("{{N}}", str(rt)))
    joined = "、".join(tags)
    t = t.replace("{{標籤1}}、{{標籤2}}", joined)
    t = t.replace("  <meta property=\"article:tag\" content=\"{{標籤1}}\">\n  <meta property=\"article:tag\" content=\"{{標籤2}}\">",
                  "\n".join(f'  <meta property="article:tag" content="{html.escape(x)}">' for x in tags))
    cat = fm["category"]
    t = t.replace('<a class="tag" href="../articles.html?category={{分類}}">{{分類}}</a>',
                  f'<a class="tag" href="../articles.html?category={urllib.parse.quote(cat)}">{html.escape(cat)}</a>')
    t = t.replace('<span class="tag">{{標籤1}}</span>\n          <span class="tag">{{標籤2}}</span>',
                  "\n          ".join(f'<span class="tag">{html.escape(x)}</span>' for x in tags))
    t = re.sub(r"\n[ \t]+\n", "\n\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    if re.search(r"\{\{.+?\}\}", t):
        die("輸出仍有未替換的 {{…}}，請檢查原稿與範本")
    return t, tags, rt, images


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    images_dir = None
    if "--images" in args:
        k = args.index("--images")
        images_dir = pathlib.Path(args[k + 1]).expanduser()
        del args[k:k + 2]
    src = pathlib.Path(args[0]).expanduser()
    fm, body = parse_frontmatter(src.read_text(encoding="utf-8"))
    for k in ("title", "slug", "date", "category", "tags", "summary", "lead"):
        if not fm.get(k):
            die(f"frontmatter 缺少 {k}")
    if fm["category"] not in ARTICLE_CATEGORIES:
        die(f"category「{fm['category']}」不在允許清單 {sorted(ARTICLE_CATEGORIES)}")
    slug = fm["slug"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        die("slug 只能是小寫英文、數字與連字號")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fm["date"]):
        die("date 格式必須是 YYYY-MM-DD")
    if fm.get("updated"):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fm["updated"]):
            die("updated 格式必須是 YYYY-MM-DD")
        if fm["updated"] < fm["date"]:
            die("updated 不能早於 date")
    truthy = lambda k: fm.get(k, "").lower() == "true"

    body = normalize_refs(body)
    dims = prepare_images(body, slug, images_dir)
    text, tags, rt, images = build(fm, body, slug, dims)
    if not 1 <= len(tags) <= 3:
        die("標籤必須是 1～3 個")
    if not 60 <= len(fm["summary"]) <= 160:
        print(f"! summary 長度 {len(fm['summary'])} 字（建議 80～120 字）")

    data = json.loads(ARTICLES.read_text(encoding="utf-8"))
    tag_warnings(tags, [a for a in data if a["slug"] != slug])
    old = next((a for a in data if a["slug"] == slug), {})

    out = ROOT / "articles" / f"{slug}.html"
    existed = out.exists()
    out.write_text(text, encoding="utf-8")
    print(f"{'更新' if existed else '建立'} {out.relative_to(ROOT)}（閱讀約 {rt} 分鐘）")

    entry = {"slug": slug, "title": fm["title"], "date": fm["date"], "category": fm["category"], "tags": tags,
             "summary": fm["summary"], "readingTime": rt}
    if fm.get("updated"):
        entry["updated"] = fm["updated"]
    if truthy("draft"):
        entry["draft"] = True
        print("! 草稿：不會出現在列表、sitemap 與 feed，但知道網址的人仍看得到頁面，不要放敏感內容。")
    adult = truthy("adult") or bool(old.get("adult"))  # 重跑時保留既有的 18+ 設定
    if adult:
        entry["adult"] = True
    for k, a in enumerate(data):
        if a["slug"] == slug:
            data[k] = entry
            break
    else:
        data.append(entry)
    ARTICLES.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    py = sys.executable
    if adult:
        subprocess.run([py, str(ROOT / "authoring" / "mark-adult.py"), slug], check=True)
    subprocess.run([py, str(ROOT / "authoring" / "build-og.py"), slug], check=True)
    subprocess.run([py, str(ROOT / "authoring" / "build-sitemap.py")], check=True)
    subprocess.run([py, str(ROOT / "authoring" / "build-feed.py")], check=True)
    subprocess.run([py, str(ROOT / "authoring" / "build-assets.py")], check=True, stdout=subprocess.DEVNULL)
    sys.exit(subprocess.run([py, str(ROOT / "authoring" / "check.py")]).returncode)


if __name__ == "__main__":
    main()
