#!/usr/bin/env python3
"""為 CSS／JS 的引用加上內容雜湊版本碼（?v=xxxxxxxx），避免部署後回訪者拿到舊快取。只用標準函式庫。

GitHub Pages 的 CSS／JS 快取 10 分鐘；檔案內容一變，版本碼就跟著變，瀏覽器會當成新網址重新下載。
會改寫：根目錄 *.html、articles/*.html、authoring/article-template.html 裡指向
assets/css/style.css 與 assets/js/site.js 的 href／src。沒有變動就不寫檔（冪等）。
stdout 只印「被修改的檔案路徑」（每行一個，給 pre-commit 用來 git add），摘要印在 stderr。
用法：python3 authoring/build-assets.py
"""
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = {"assets/css/style.css": "css/style.css", "assets/js/site.js": "js/site.js"}
PATTERN = re.compile(r'((?:href|src)=")([^"?#]*assets/(?:css/style\.css|js/site\.js))(\?v=[0-9a-f]{8})?(")')


def version(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:8]


def html_files():
    return sorted(ROOT.glob("*.html")) + sorted((ROOT / "articles").glob("*.html")) + \
        [ROOT / "authoring" / "article-template.html"]


def main() -> None:
    vers = {rel: version(rel) for rel in ASSETS}
    changed = []
    for f in html_files():
        text = f.read_text(encoding="utf-8")

        def repl(m):
            rel = "assets/" + m.group(2).split("assets/", 1)[1]
            return f"{m.group(1)}{m.group(2)}?v={vers[rel]}{m.group(4)}"
        new = PATTERN.sub(repl, text)
        if new != text:
            f.write_text(new, encoding="utf-8")
            changed.append(f.relative_to(ROOT).as_posix())
    for c in changed:
        print(c)
    print(f"版本碼：style.css={vers['assets/css/style.css']} site.js={vers['assets/js/site.js']}；更新 {len(changed)} 個檔案",
          file=sys.stderr)


if __name__ == "__main__":
    main()
