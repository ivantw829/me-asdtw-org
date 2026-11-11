#!/usr/bin/env bash
# 一條龍發文：Markdown → 文章頁 → 本機預覽（等你確認）→ PR 合併上線 → 驗證線上 meta。
# 用法：bash authoring/publish.sh 原稿.md [圖片資料夾]
# 環境變數：CO_AUTHOR（提交共同作者）、PREVIEW_PORT（預設 8765）
# 草稿：原稿 frontmatter 寫 draft: true，一樣會上線但 noindex 且不進列表；拿掉後重跑即正式發布。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

src="${1:?用法：bash authoring/publish.sh 原稿.md [圖片資料夾]}"
imgs="${2:-}"
port="${PREVIEW_PORT:-8765}"

fm() { python3 - "$src" "$1" <<'PY'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
m = re.match(r"\A---\n(.*?)\n---\n", t, re.S)
for line in (m.group(1) if m else "").splitlines():
    k, _, v = line.partition(":")
    if k.strip() == sys.argv[2]:
        print(v.strip()); break
PY
}
slug=$(fm slug); title=$(fm title); draft=$(fm draft | tr 'A-Z' 'a-z')
[ -n "$slug" ] && [ -n "$title" ] || { echo "✗ 原稿 frontmatter 缺少 slug 或 title" >&2; exit 1; }

existed=0
git ls-files --error-unmatch "articles/$slug.html" >/dev/null 2>&1 && existed=1

if [ -n "$imgs" ]; then python3 authoring/md2article.py "$src" --images "$imgs"; else python3 authoring/md2article.py "$src"; fi

python3 -m http.server "$port" >/dev/null 2>&1 &
server=$!
trap 'kill $server 2>/dev/null || true' EXIT
sleep 1
url="http://localhost:$port/articles/$slug.html"
echo "預覽：$url"
command -v open >/dev/null && open "$url" || true
read -r -p "確認沒問題請按 Enter 發布（Ctrl+C 取消，檔案會留在工作區）… " _
kill $server 2>/dev/null || true

if [ "$draft" = "true" ]; then verb="新增草稿"; elif [ "$existed" = 1 ]; then verb="更新"; else verb="新增"; fi
bash authoring/ship.sh "content(article): ${verb}〈${title}〉"
python3 authoring/verify-live.py "$slug"
