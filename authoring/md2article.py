#!/usr/bin/env python3
"""Markdown → 文章頁。把一份帶 frontmatter 的 Markdown 套進 article-template.html。

做的事（輸出仍是提交進 repo 的靜態 HTML，部署與 SEO 不變）：
  1. 產生 articles/<slug>.html（版型、meta、ld+json 全部來自範本，不會被改壞）
  2. 新增／更新 data/articles.json 的該筆資料
  3. 複製圖片到 images/articles/<slug>/（給 --images 時）
  4. 產生分享圖與 sitemap，最後執行 check.py

用法：
  python3 authoring/md2article.py 原稿.md [--images 圖片資料夾]

原稿格式：
  ---
  title: 文章標題
  slug: my-article            # 小寫英文、數字、連字號
  date: 2026-11-11
  tags: 標籤1, 標籤2          # 1～3 個
  summary: 80～120 字摘要，會同時用在 description／og:description／articles.json
  lead: 一句話摘要（30～60 字），顯示在標題下
  readingTime: 6              # 選填，沒填就以每分鐘 400 字估算
  ---
  內文 Markdown。支援：
    ## 大標、### 小標、段落、- 清單、1. 清單、| 表格 |、> 引言、--- 分隔線
    ![圖說](檔名.webp)        # 圖說同時當 alt；檔名為 cover.webp 的當作封面
    [[提示框：標題]] 下一段文字（到空行為止）
    [[金句：一句話]]
    [[目錄]]                  # 在第一個大標前產生目錄
    `code`、**粗體**、[文字](網址)、裸網址（自動變連結）
    最後可放 `## 參考資料` + 編號清單，會變成文末參考資料區塊
"""
import html
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "authoring" / "article-template.html"
ARTICLES = ROOT / "data" / "articles.json"


def die(msg: str) -> None:
    sys.exit(f"✗ {msg}")


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
    t = re.sub(r'(?<![">=])(https?://[^\s<）」]+)',
               lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>', t)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], t)


def convert(body: str, slug: str):
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
        return (f'<figure>\n  <img src="../images/articles/{slug}/{fname}" alt="{a}" loading="lazy" '
                f'width="1600" height="900">\n  <figcaption>{a}</figcaption>\n</figure>')

    while i < len(lines):
        l = lines[i]
        s = l.strip()
        if not s:
            i += 1
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


def build(fm, body, slug):
    main, cover, sources, images = convert(body, slug)
    indent = lambda s, n: "\n".join((" " * n + x if x else x) for x in s.split("\n"))
    tags = [x.strip() for x in re.sub(r"^\[|\]$", "", fm["tags"]).split(",") if x.strip()]
    text_len = len(re.sub(r"\s|<[^>]+>", "", main))
    rt = int(fm["readingTime"]) if fm.get("readingTime") else max(1, round(text_len / 400))
    y, mth, d = fm["date"].split("-")
    t = TEMPLATE.read_text(encoding="utf-8")
    t = re.sub(r"[ \t]*<!--(?!\s*社群分享).*?-->\n?", "", t, flags=re.S)
    a = t.index('<div class="prose">')
    b = t.rindex("      </div>\n", a, t.index("    </article>")) + len("      </div>\n")
    t = t[:a] + '<div class="prose">\n\n' + indent(main, 8) + "\n\n      </div>\n" + t[b:]
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
    t = t.replace('<a class="tag" href="../articles.html?tag={{標籤1}}">{{標籤1}}</a>\n          '
                  '<a class="tag" href="../articles.html?tag={{標籤2}}">{{標籤2}}</a>',
                  "\n          ".join(f'<a class="tag" href="../articles.html?tag={x.replace(" ", "%20")}">{html.escape(x)}</a>'
                                      for x in tags))
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
    for k in ("title", "slug", "date", "tags", "summary", "lead"):
        if not fm.get(k):
            die(f"frontmatter 缺少 {k}")
    slug = fm["slug"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        die("slug 只能是小寫英文、數字與連字號")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fm["date"]):
        die("date 格式必須是 YYYY-MM-DD")
    text, tags, rt, images = build(fm, body, slug)
    if not 1 <= len(tags) <= 3:
        die("標籤必須是 1～3 個")
    if not 60 <= len(fm["summary"]) <= 160:
        print(f"! summary 長度 {len(fm['summary'])} 字（建議 80～120 字）")

    out = ROOT / "articles" / f"{slug}.html"
    existed = out.exists()
    out.write_text(text, encoding="utf-8")
    print(f"{'更新' if existed else '建立'} {out.relative_to(ROOT)}（閱讀約 {rt} 分鐘）")

    img_out = ROOT / "images" / "articles" / slug
    if images_dir:
        img_out.mkdir(parents=True, exist_ok=True)
        for f in sorted(images):
            if (images_dir / f).exists():
                shutil.copy2(images_dir / f, img_out / f)
            else:
                print(f"! 找不到圖片 {images_dir / f}")
    for f in sorted(images):
        if not (img_out / f).exists():
            print(f"! 缺少圖片 images/articles/{slug}/{f}")

    data = json.loads(ARTICLES.read_text(encoding="utf-8"))
    entry = {"slug": slug, "title": fm["title"], "date": fm["date"], "tags": tags,
             "summary": fm["summary"], "readingTime": rt}
    for k, a in enumerate(data):
        if a["slug"] == slug:
            for extra in ("draft", "adult"):  # 保留既有旗標
                if extra in a:
                    entry[extra] = a[extra]
            data[k] = entry
            break
    else:
        data.append(entry)
    ARTICLES.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    py = sys.executable
    subprocess.run([py, str(ROOT / "authoring" / "build-og.py"), slug], check=True)
    subprocess.run([py, str(ROOT / "authoring" / "build-sitemap.py")], check=True)
    sys.exit(subprocess.run([py, str(ROOT / "authoring" / "check.py")]).returncode)


if __name__ == "__main__":
    main()
