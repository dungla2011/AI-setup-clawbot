/**
 * nav.js — Shared navigation bar for all pages.
 *
 * Usage in each HTML page:
 *   1. Place a bare <nav> tag:
 *        <nav id="app-nav" class="navbar app-navbar navbar-expand-lg" data-active="chat|stats|docs"></nav>
 *   2. After building API_URL, call:
 *        initNav(API_URL);
 *
 * Provides:
 *   - Rendered navbar HTML (brand, links, usage-pill)
 *   - window.updateUsageStats() — pages can call this after events (e.g. post-send)
 *   - Auto-refresh of the pill every 15 s
 */
(function () {
  const PAGES = [
    { key: 'chat',  href: 'index.html', icon: '&#x1F4AC;', label: 'Chat' },
    { key: 'stats', href: 'stats.html', icon: '&#x1F4CA;', label: 'Thống kê' },
    { key: 'docs',  href: 'docs.html',  icon: '&#x1F4D6;', label: 'API Docs' },
  ];

  window.initNav = function (apiUrl) {
    const nav = document.getElementById('app-nav');
    if (!nav) return;

    const active = nav.dataset.active || '';
    const links = PAGES.map(p =>
      `<li class="nav-item"><a class="nav-link${p.key === active ? ' active' : ''}" href="${p.href}">${p.icon} ${p.label}</a></li>`
    ).join('');

    nav.innerHTML = `
      <a class="navbar-brand" href="index.html">&#x1F916; Bot MVP</a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain"
              aria-controls="navMain" aria-expanded="false">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navMain">
        <ul class="navbar-nav mx-auto gap-1">${links}</ul>
        <div class="usage-pill">
          <div class="stat-item"><span class="stat-label">Requests:</span><span class="stat-value" id="statRequests">&mdash;</span></div>
          <span class="stat-sep">|</span>
          <div class="stat-item"><span class="stat-label">Tokens:</span><span class="stat-value" id="statTokens">&mdash;</span></div>
          <span class="stat-sep">|</span>
          <div class="stat-item"><span class="stat-label">Cost:</span><span class="stat-value" id="statCost">&mdash;</span></div>
        </div>
      </div>`;

    async function refreshStats() {
      try {
        const res = await fetch(`${apiUrl}/stats`);
        if (!res.ok) return;
        const d = await res.json();
        const totalTokens = (d.total_input_tokens || 0) + (d.total_output_tokens || 0);
        document.getElementById('statRequests').textContent = (d.total_requests || 0).toLocaleString();
        document.getElementById('statTokens').textContent =
          totalTokens >= 1000 ? (totalTokens / 1000).toFixed(1) + 'K' : totalTokens.toLocaleString();
        document.getElementById('statCost').textContent = '$' + (d.total_cost_usd || 0).toFixed(4);
      } catch (e) { /* silently ignore network errors */ }
    }

    // Expose globally so pages can trigger an immediate refresh (e.g. after sending a message)
    window.updateUsageStats = refreshStats;

    refreshStats();
    setInterval(refreshStats, 15000);
  };
}());
