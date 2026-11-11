#!/usr/bin/env python3
"""把文章標成「成人內容（18+）」，或取消。只用標準函式庫。

用法：
  python3 authoring/mark-adult.py <slug>          標成成人文章
  python3 authoring/mark-adult.py <slug> --undo   取消

標成成人文章會一次完成（check.py 會驗證這些都存在）：
  1. data/articles.json 的該筆加上 "adult": true（列表卡片改顯示 18+ 標籤，不顯示封面與摘要）
  2. <article> 加上 data-age-gate（預設隱藏全文，需通過「是否已成年」彈窗）與 noscript 說明
  3. robots 改為 noindex, nofollow, noarchive；加上分級標籤（rating: adult 與 RTA）
  4. 分享圖（og:image / twitter:image）改用不含標題與摘要的通用 18+ 卡片 images/og/adult.jpg
  5. 結構化資料加上 audience.suggestedMinAge = 18
  6. 從 sitemap.xml 與 feed.xml 移除
注意：og:title、description、summary 仍是你寫的文字，請自行確保它們是中性描述，不含露骨內容。
"""
import html
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = f"https://{(ROOT / 'CNAME').read_text(encoding='utf-8').strip()}"
ADULT_IMG = f"{BASE}/images/og/adult.jpg"
ADULT_ALT = "成人內容（18+）：需年滿 18 歲才能閱讀"
RTA = "RTA-5042-1996-1400-1577-RTA"
NOSCRIPT = '<noscript><p class="age-noscript">此文章含成人內容，需要啟用 JavaScript，並確認已年滿 18 歲後才能閱讀。</p></noscript>'
e = lambda s: html.escape(s, quote=True)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    undo = "--undo" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    slug = args[0]

    jpath = ROOT / "data" / "articles.json"
    data = json.loads(jpath.read_text(encoding="utf-8"))
    art = next((a for a in data if a["slug"] == slug), None)
    if not art:
        sys.exit(f"data/articles.json 找不到 slug：{slug}")
    page = ROOT / "articles" / f"{slug}.html"
    s = page.read_text(encoding="utf-8")

    normal_img = f"{BASE}/images/og/{slug}.jpg"
    normal_alt = f"{art['title']}｜賴奕帆的文章分享卡（標籤：{'、'.join(art['tags'])}）"
    img, alt = (normal_img, normal_alt) if undo else (ADULT_IMG, ADULT_ALT)

    # 1) article 標記與 noscript
    s = re.sub(r"<noscript><p class=\"age-noscript\">.*?</p></noscript>\n?\s*", "", s)
    s = re.sub(r'(<article class="article" data-slug="[^"]*")( data-age-gate)?>', lambda m: m.group(1) + ("" if undo else " data-age-gate") + ">", s, count=1)
    if not undo:
        s = re.sub(r'(<article class="article"[^>]*>\n)', lambda m: m.group(1) + "      " + NOSCRIPT + "\n", s, count=1)

    # 2) robots 與分級標籤
    s = re.sub(r'[ \t]*<meta name="rating" content="[^"]*">\n', "", s)
    s = re.sub(r'<meta name="robots" content="[^"]*">',
               '<meta name="robots" content="index, follow, max-image-preview:large">' if undo
               else '<meta name="robots" content="noindex, nofollow, noarchive">', s, count=1)
    if not undo:
        s = re.sub(r'([ \t]*)(<meta name="robots"[^\n]*\n)', lambda m: m.group(1) + m.group(2) +
                   f'{m.group(1)}<meta name="rating" content="adult">\n{m.group(1)}<meta name="rating" content="{RTA}">\n', s, count=1)

    # 3) 分享圖
    for key, attr in (("og:image", "property"), ("twitter:image", "name")):
        s = re.sub(rf'(<meta {attr}="{key}" content=")[^"]*(")', rf"\g<1>{img}\2", s)
    for key, attr in (("og:image:alt", "property"), ("twitter:image:alt", "name")):
        s = re.sub(rf'(<meta {attr}="{key}" content=")[^"]*(")', lambda m: m.group(1) + e(alt) + m.group(2), s)

    # 4) 結構化資料
    def fix_ld(m):
        obj = json.loads(m.group(1))
        obj["image"] = [img]
        if undo:
            obj.pop("audience", None)
        else:
            obj["audience"] = {"@type": "PeopleAudience", "suggestedMinAge": 18}
        return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "</script>"
    s = re.sub(r'<script type="application/ld\+json">(.*?)</script>', fix_ld, s, count=1, flags=re.S)
    page.write_text(s, encoding="utf-8")

    # 5) JSON
    if undo:
        art.pop("adult", None)
    else:
        art["adult"] = True
    jpath.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 6) 產生通用分享圖並重建 sitemap
    subprocess.run([sys.executable, str(ROOT / "authoring" / "build-og.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "authoring" / "build-sitemap.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "authoring" / "build-feed.py")], check=True)
    print(f"{'已取消' if undo else '已標為成人內容（18+）'}：{slug}")
    if not undo:
        print("→ 請確認 title、summary、description 是中性描述（它們仍會出現在列表與分享預覽的文字裡）。")


if __name__ == "__main__":
    main()
