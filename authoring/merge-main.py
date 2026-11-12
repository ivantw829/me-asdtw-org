#!/usr/bin/env python3
"""把 origin/main 合併進目前分支；只出在「產物檔案」的衝突自動解決。

可自動解決：
- HTML 內只差 ?v= 版本碼的衝突 → 取目前分支，之後 build-assets 重算
- sitemap.xml、feed.xml → 取目前分支，之後重新產生
- images/og/.manifest.json → 兩邊的雜湊表取聯集
其餘衝突（真正的內容衝突，例如 data/articles.json）不處理：中止合併並列出檔案，exit 1。
成功時 exit 0（已經是最新，或已合併並提交）。
"""
import json, re, subprocess, sys

def run(*a, check=True):
    return subprocess.run(a, capture_output=True, text=True, check=check)

V = re.compile(r"\?v=[0-9a-f]{8}")
GEN = {"sitemap.xml", "feed.xml"}
MANIFEST = "images/og/.manifest.json"

def resolve_html(path):
    text = open(path, encoding="utf-8").read()
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        if not lines[i].startswith("<<<<<<< "):
            out.append(lines[i]); i += 1; continue
        j = i + 1; ours = []
        while not lines[j].startswith("======="): ours.append(lines[j]); j += 1
        k = j + 1; theirs = []
        while not lines[k].startswith(">>>>>>> "): theirs.append(lines[k]); k += 1
        norm = lambda ls: [V.sub("?v=X", l) for l in ls]
        if norm(ours) != norm(theirs):
            return False
        out.extend(ours); i = k + 1
    open(path, "w", encoding="utf-8").write("\n".join(out))
    return True

def main():
    run("git", "fetch", "-q", "origin")
    if run("git", "merge-base", "--is-ancestor", "origin/main", "HEAD", check=False).returncode == 0:
        return 0
    if run("git", "merge", "--no-commit", "--no-ff", "origin/main", check=False).returncode == 0:
        pass
    else:
        conflicted = run("git", "diff", "--name-only", "--diff-filter=U").stdout.split()
        bad = []
        for f in conflicted:
            if f in GEN:
                run("git", "checkout", "--ours", "--", f)
            elif f == MANIFEST:
                ours = json.loads(run("git", "show", f":2:{f}").stdout)
                theirs = json.loads(run("git", "show", f":3:{f}").stdout)
                merged = {**theirs, **ours}
                open(f, "w", encoding="utf-8").write(json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            elif f.endswith(".html") and resolve_html(f):
                pass
            else:
                bad.append(f)
        if bad:
            run("git", "merge", "--abort", check=False)
            print("✗ 無法自動合併 origin/main，這些檔案有內容衝突，請手動處理：", *bad, sep="\n  ", file=sys.stderr)
            return 1
    for s in ("build-sitemap.py", "build-feed.py", "build-assets.py", "build-og.py"):
        r = run("python3", f"authoring/{s}", check=False)
        if r.returncode:
            print(f"✗ {s} 失敗：{r.stderr}", file=sys.stderr)
            run("git", "merge", "--abort", check=False)
            return 1
    run("git", "add", "-A")
    r = run("git", "commit", "-q", "--no-edit", check=False)
    if r.returncode:
        print(r.stdout, r.stderr, file=sys.stderr)
        return 1
    print("✓ 已合併最新 main（產物已重建）")
    return 0

sys.exit(main())
