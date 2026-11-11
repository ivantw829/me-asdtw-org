#!/usr/bin/env python3
"""通知 Bing 等搜尋引擎（IndexNow）有新頁面或更新。只用標準函式庫。

GitHub Actions（.github/workflows/indexnow.yml）在 main 有新 commit 時執行：
  - 比對上一個 commit，找出新增／修改的 articles/*.html（排除草稿與 18+ 文章）
  - 有變動就連同首頁與文章列表一起送出；等頁面真的上線（HTTP 200）後才送
用法：
  python3 authoring/indexnow.py --dry-run     只列出會送出的網址
  python3 authoring/indexnow.py --all         送出所有已發布文章（手動補送）
金鑰檔：網站根目錄的 <金鑰>.txt（內容就是金鑰本身），check.py 會驗證存在且一致。
Google 不支援 IndexNow，仍靠 sitemap。
"""
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOST = (ROOT / "CNAME").read_text(encoding="utf-8").strip()
BASE = f"https://{HOST}"


def find_key() -> str:
    for f in ROOT.glob("*.txt"):
        if re.fullmatch(r"[0-9a-f]{32}", f.stem) and f.read_text(encoding="utf-8").strip() == f.stem:
            return f.stem
    sys.exit("找不到 IndexNow 金鑰檔（根目錄的 <32 位十六進位>.txt，內容等於檔名）")


def changed_files() -> set:
    out = subprocess.run(["git", "diff", "--name-only", "HEAD~1", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return set(out.stdout.split()) if out.returncode == 0 else set()


def main() -> None:
    dry, every = "--dry-run" in sys.argv, "--all" in sys.argv
    articles = json.loads((ROOT / "data" / "articles.json").read_text(encoding="utf-8"))
    public = {a["slug"] for a in articles if not a.get("draft") and not a.get("adult")}
    if every:
        slugs = public
    else:
        changed = changed_files()
        slugs = {pathlib.Path(f).stem for f in changed if re.fullmatch(r"articles/[^/]+\.html", f)} & public
    if not slugs:
        print("沒有需要通知的文章。")
        return
    urls = [f"{BASE}/", f"{BASE}/articles.html"] + [f"{BASE}/articles/{s}.html" for s in sorted(slugs)]
    print("要送出：\n  " + "\n  ".join(urls))
    if dry:
        return

    deadline = time.time() + 300  # 等 GitHub Pages 部署完成
    pending = list(urls)
    while pending and time.time() < deadline:
        pending = [u for u in pending if not _live(u)]
        if pending:
            time.sleep(10)
    if pending:
        sys.exit("部署逾時，下列網址還抓不到：\n  " + "\n  ".join(pending))

    key = find_key()
    body = json.dumps({"host": HOST, "key": key, "keyLocation": f"{BASE}/{key}.txt", "urlList": urls}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow 回應：HTTP {r.status}")
    except urllib.error.HTTPError as e:  # 200/202 成功；其他代表金鑰或網址有問題
        sys.exit(f"IndexNow 失敗：HTTP {e.code} {e.read().decode('utf-8', 'replace')[:200]}")


def _live(url: str) -> bool:
    try:
        req = urllib.request.Request(f"{url}?_={int(time.time())}", method="HEAD", headers={"User-Agent": "indexnow-ci"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


if __name__ == "__main__":
    main()
