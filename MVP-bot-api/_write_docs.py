import pathlib
base = pathlib.Path(__file__).parent

docs_html = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bot MVP - API Docs</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="style.css">
  <style>
    html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; }
    .docs-shell { display: flex; flex-direction: column; height: 100vh; }
    .docs-frame { flex: 1; border: none; width: 100%; }
  </style>
</head>
<body class="docs-shell">

  <!-- Shared Navbar -->
  <nav class="navbar app-navbar navbar-expand-lg">
    <a class="navbar-brand" href="index.html">&#x1F916; Bot MVP</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain" aria-controls="navMain" aria-expanded="false">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navMain">
      <ul class="navbar-nav mx-auto gap-1">
        <li class="nav-item"><a class="nav-link" href="index.html">&#x1F4AC; Chat</a></li>
        <li class="nav-item"><a class="nav-link" href="stats.html">&#x1F4CA; Thống kê</a></li>
        <li class="nav-item"><a class="nav-link active" href="docs.html">&#x1F4D6; API Docs</a></li>
      </ul>
      <div class="usage-pill">
        <div class="stat-item"><span class="stat-label">Requests:</span><span class="stat-value" id="statRequests">&mdash;</span></div>
        <span class="stat-sep">|</span>
        <div class="stat-item"><span class="stat-label">Tokens:</span><span class="stat-value" id="statTokens">&mdash;</span></div>
        <span class="stat-sep">|</span>
        <div class="stat-item"><span class="stat-label">Cost:</span><span class="stat-value" id="statCost">&mdash;</span></div>
      </div>
    </div>
  </nav>

  <!-- Swagger UI embedded in iframe -->
  <iframe class="docs-frame" id="docsFrame" src="about:blank"></iframe>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    const API_PORT = "{{API_PORT}}".includes('{{') ? "8100" : "{{API_PORT}}";
    const API_URL  = "{{API_URL}}".includes('{{') ? `http://${window.location.hostname}:${API_PORT}` : "{{API_URL}}";

    document.getElementById('docsFrame').src = `${API_URL}/docs`;

    async function updateUsageStats() {
      try {
        const res = await fetch(`${API_URL}/stats`);
        if (!res.ok) return;
        const data = await res.json();
        const totalTokens = (data.total_input_tokens || 0) + (data.total_output_tokens || 0);
        const cost = data.total_cost_usd || 0;
        document.getElementById('statRequests').textContent = (data.total_requests || 0).toLocaleString();
        document.getElementById('statTokens').textContent = totalTokens >= 1000 ? (totalTokens/1000).toFixed(1)+'K' : totalTokens.toLocaleString();
        document.getElementById('statCost').textContent = '$' + cost.toFixed(4);
      } catch(e) {}
    }

    window.addEventListener('load', updateUsageStats);
    setInterval(updateUsageStats, 15000);
  </script>
</body>
</html>"""

(base / 'docs.html').write_text(docs_html, encoding='utf-8')
print('docs.html written OK:', len(docs_html), 'bytes')
