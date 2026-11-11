/* ==========================================================
   賴奕帆 個人網站 — 共用腳本
   功能：統一的頁首/頁尾、深色模式、讀取 data/articles.json、giscus 留言
   要改導覽、社群連結、giscus 設定，只要改下面的 SITE 即可。
   ========================================================== */
const SITE = {
  name: "賴奕帆",
  tagline: "多元平權倡議者",
  nav: [
    { label: "首頁", path: "index.html" },
    { label: "關於", path: "about.html" },
    { label: "文章", path: "articles.html" },
    { label: "聯絡", path: "contact.html" },
    { label: "贊助", path: "sponsor.html" },
  ],
  // 社群連結（頁尾使用；聯絡頁的順序寫在 contact.html）
  links: [
    { label: "Discord", href: "https://discord.gg/b8BwFtv3C9" },
    { label: "Instagram", href: "https://www.instagram.com/ivantw829/" },
    { label: "Threads", href: "https://www.threads.com/@yian.earth" },
    { label: "Bluesky", href: "https://bsky.app/profile/ouoc.net" },
    { label: "YouTube", href: "https://www.youtube.com/channel/UCvTDRWA06FqA7SXe5jkCEWw" },
    { label: "GitHub", href: "https://github.com/ivantw829" },
  ],
  email: "ouob@duck.com",
  disclaimer: "個人發言僅代表個人立場，與所屬團體無關。",
  // giscus 留言：到 https://giscus.app 填入 repo 後取得下面四個值；repo 留空則不顯示留言區
  giscus: { repo: "", repoId: "", category: "", categoryId: "" },
};

(function () {
  const script = document.currentScript;
  // 以本腳本位置推算網站根目錄，讓首頁與 articles/ 內的頁面都能用同一份導覽
  const BASE = new URL("../../", script.src).href;
  const here = location.pathname;
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* ---------- 深色模式 ---------- */
  const root = document.documentElement;
  const getStored = () => { try { return localStorage.getItem("theme"); } catch (e) { return null; } };
  const setStored = (v) => { try { localStorage.setItem("theme", v); } catch (e) {} };
  const stored = getStored();
  if (stored) root.setAttribute("data-theme", stored);
  const isDark = () => root.getAttribute("data-theme") === "dark" ||
    (!root.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);

  /* ---------- 頁首 / 頁尾 ---------- */
  const header = document.querySelector("[data-site-header]");
  if (header) {
    header.className = "site-header";
    const file = here.split("/").pop() || "index.html";
    const inArticles = here.includes("/articles/");
    const nav = SITE.nav.map((n) => {
      const current = n.path === file || (inArticles && n.path === "articles.html");
      return `<a href="${BASE}${n.path}"${current ? ' aria-current="page"' : ""}>${n.label}</a>`;
    }).join("");
    header.innerHTML = `<div class="wrap">
      <a class="brand" href="${BASE}index.html">${esc(SITE.name)}</a>
      <nav class="nav" aria-label="主要導覽">${nav}</nav>
      <button class="theme-toggle" type="button" aria-label="切換深色模式"></button>
    </div>`;
    const btn = header.querySelector(".theme-toggle");
    const paint = () => { btn.textContent = isDark() ? "☀" : "☾"; btn.setAttribute("aria-pressed", isDark()); };
    paint();
    btn.addEventListener("click", () => {
      const next = isDark() ? "light" : "dark";
      root.setAttribute("data-theme", next); setStored(next); paint();
      const g = document.querySelector("iframe.giscus-frame");
      if (g) g.contentWindow.postMessage({ giscus: { setConfig: { theme: next === "dark" ? "dark" : "light" } } }, "https://giscus.app");
    });
  }

  const footer = document.querySelector("[data-site-footer]");
  if (footer) {
    footer.className = "site-footer";
    const links = SITE.links.map((l) => l.path ? `<a href="${BASE}${l.path}">${esc(l.label)}</a>` : `<a href="${l.href}" target="_blank" rel="noopener">${esc(l.label)}</a>`).join("");
    footer.innerHTML = `<div class="wrap">
      <div class="footer-links">${links}</div>
      <small>${esc(SITE.disclaimer)}</small>
      <small>© ${new Date().getFullYear()} ${esc(SITE.name)}</small>
    </div>`;
  }

  /* ---------- 文章資料 ---------- */
  const fmtDate = (iso) => { const [y, m, d] = iso.split("-"); return `${y} 年 ${+m} 月 ${+d} 日`; };
  let cache;
  const loadArticles = () => cache || (cache = fetch(BASE + "data/articles.json")
    .then((r) => r.json())
    .then((list) => list.filter((a) => !a.draft).sort((a, b) => (a.date < b.date ? 1 : -1))));

  const card = (a) => `<article class="card">
    ${a.cover ? `<img class="card-cover" src="${BASE}${esc(a.cover)}" alt="" loading="lazy">` : ""}
    <div class="meta">${fmtDate(a.date)}${a.readingTime ? ` · 約 ${a.readingTime} 分鐘` : ""}</div>
    <h3><a href="${BASE}articles/${esc(a.slug)}.html">${esc(a.title)}</a></h3>
    <p>${esc(a.summary || "")}</p>
    <div class="chips">${(a.tags || []).map((t) => `<a class="tag" href="${BASE}articles.html?tag=${encodeURIComponent(t)}">${esc(t)}</a>`).join("")}</div>
  </article>`;

  // 首頁：最新文章
  const latest = document.querySelector("[data-latest-articles]");
  if (latest) {
    loadArticles().then((list) => {
      latest.innerHTML = list.length ? list.slice(0, 3).map(card).join("") : '<p class="empty">還沒有文章，敬請期待。</p>';
    }).catch(() => { latest.innerHTML = '<p class="empty">文章清單載入失敗。若是在本機開啟，請用 <code>python3 -m http.server</code> 預覽。</p>'; });
  }

  // 文章列表頁：標籤篩選
  const listEl = document.querySelector("[data-article-list]");
  if (listEl) {
    const filterEl = document.querySelector("[data-tag-filter]");
    let active = new URLSearchParams(location.search).get("tag") || "";
    loadArticles().then((list) => {
      const render = () => {
        const shown = active ? list.filter((a) => (a.tags || []).includes(active)) : list;
        listEl.innerHTML = shown.length ? shown.map(card).join("") : '<p class="empty">沒有符合的文章。</p>';
        filterEl && filterEl.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String((b.dataset.tag || "") === active)));
      };
      if (filterEl) {
        const tags = [...new Set(list.flatMap((a) => a.tags || []))];
        filterEl.innerHTML = [""].concat(tags).map((t) => `<button type="button" class="tag" data-tag="${esc(t)}">${t ? esc(t) : "全部"}</button>`).join("");
        filterEl.addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; active = b.dataset.tag; render(); });
      }
      render();
    }).catch(() => { listEl.innerHTML = '<p class="empty">文章清單載入失敗。</p>'; });
  }

  // 文章頁：上一篇／下一篇
  const nav = document.querySelector("[data-article-nav]");
  const art = document.querySelector("article[data-slug]");
  if (nav && art) {
    nav.className = "article-nav";
    loadArticles().then((list) => {
      const i = list.findIndex((a) => a.slug === art.dataset.slug);
      if (i < 0) return;
      const newer = list[i - 1], older = list[i + 1];
      nav.innerHTML =
        (older ? `<a class="prev" href="${BASE}articles/${esc(older.slug)}.html"><small>← 上一篇</small>${esc(older.title)}</a>` : "") +
        (newer ? `<a class="next" href="${BASE}articles/${esc(newer.slug)}.html"><small>下一篇 →</small>${esc(newer.title)}</a>` : "");
    }).catch(() => {});
  }

  // 文章頁：giscus 留言
  const gc = document.querySelector("[data-giscus]");
  if (gc && SITE.giscus.repo) {
    gc.className = "comments";
    gc.innerHTML = "<h2>留言</h2>";
    const s = document.createElement("script");
    s.src = "https://giscus.app/client.js";
    s.async = true; s.crossOrigin = "anonymous";
    const set = { "repo": SITE.giscus.repo, "repo-id": SITE.giscus.repoId, "category": SITE.giscus.category, "category-id": SITE.giscus.categoryId,
      "mapping": "pathname", "strict": "0", "reactions-enabled": "1", "emit-metadata": "0", "input-position": "top",
      "theme": isDark() ? "dark" : "light", "lang": "zh-TW", "loading": "lazy" };
    Object.entries(set).forEach(([k, v]) => s.setAttribute("data-" + k, v));
    gc.appendChild(s);
  }

  // 經歷頁：依年份分組的時間軸，可依類別篩選（資料在 data/timeline.json）
  const tlEl = document.querySelector("[data-timeline]");
  if (tlEl) {
    const filterEl = document.querySelector("[data-timeline-filter]");
    let active = "";
    fetch(BASE + "data/timeline.json").then((r) => r.json()).then((list) => {
      list.sort((a, b) => (a.date < b.date ? 1 : -1));
      const render = () => {
        const shown = active ? list.filter((i) => i.category === active) : list;
        const years = [...new Set(shown.map((i) => i.date.slice(0, 4)))];
        tlEl.innerHTML = years.map((y) => `<h2 class="tl-year">${y}</h2><ol class="tl-list">` +
          shown.filter((i) => i.date.startsWith(y)).map((i) => `<li class="tl-item">
            <div class="tl-meta"><span>${esc(i.display)}</span><span class="tag">${esc(i.category)}</span></div>
            <div class="tl-title">${/^https:\/\//.test(i.url || "") ? `<a href="${esc(i.url)}" target="_blank" rel="noopener">${esc(i.title)}</a>` : esc(i.title)}</div>
            ${i.role ? `<div class="tl-role">${esc(i.role)}</div>` : ""}
          </li>`).join("") + "</ol>").join("") || '<p class="empty">沒有符合的項目。</p>';
        filterEl && filterEl.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.cat === active)));
      };
      if (filterEl) {
        const order = ["社會倡議", "政策參與", "社會服務", "研習", "研究", "組織參與"];
        const cats = [...new Set(list.map((i) => i.category))].sort((x, y) => (order.indexOf(x) + 99) % 99 - (order.indexOf(y) + 99) % 99);
        filterEl.innerHTML = [""].concat(cats).map((c) => `<button type="button" class="tag" data-cat="${esc(c)}">${c ? esc(c) : "全部"}</button>`).join("");
        filterEl.addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; active = b.dataset.cat; render(); });
      }
      render();
    }).catch(() => { tlEl.innerHTML = '<p class="empty">時間軸載入失敗。</p>'; });
  }

  // 聯絡頁：Email
  document.querySelectorAll("[data-email]").forEach((el) => {
    const t = el.querySelector("[data-email-text]");
    if (SITE.email) { el.href = "mailto:" + SITE.email; if (t) t.textContent = SITE.email; }
    else { el.removeAttribute("href"); if (t) t.textContent = "（尚未設定）"; }
  });
})();
