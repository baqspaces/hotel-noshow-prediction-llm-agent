const state = {
  token: localStorage.getItem("noshow_token") || "",
  dimensions: [],
  socket: null,
};

const $ = (id) => document.getElementById(id);
const fmtPct = (value) => `${((Number(value) || 0) * 100).toFixed(1)}%`;
const fmtMoney = (value) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
const fmtCurrency = (value) => `USD ${fmtMoney(value)}`;

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderInlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").split(/\r?\n/);
  const html = [];
  let inList = false;

  function closeList() {
    if (inList) {
      html.push("</ul>");
      inList = false;
    }
  }

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      closeList();
      return;
    }

    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = heading[1].length + 2;
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      return;
    }

    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${renderInlineMarkdown(bullet[1])}</li>`);
      return;
    }

    closeList();
    html.push(`<p>${renderInlineMarkdown(trimmed)}</p>`);
  });

  closeList();
  return html.join("");
}

function dimensionLabel(dimension) {
  return dimension === "customer_status" ? "Customer status" : dimension;
}

function customerStatus(row) {
  if (row.customer_status) return row.customer_status;
  if (Number(row.first_time_flag) === 1) return "First-time";
  if (Number(row.first_time_flag) === 0) return "Returning";
  return "";
}

function renderAssistantResponse(data) {
  const provider = data.provider === "deterministic_fallback" ? "fallback" : data.provider || "unknown";
  const trace = (data.agent_trace || [])
    .map((step) => `<li><strong>${escapeHtml(step.agent)}:</strong> ${escapeHtml(step.action)}</li>`)
    .join("");

  $("assistantAnswer").innerHTML = `
    <div class="assistant-meta">
      <span class="provider provider-${escapeHtml(provider)}">Provider: ${escapeHtml(provider)}</span>
    </div>
    <div class="assistant-markdown">${renderMarkdown(data.answer)}</div>
    <details class="agent-trace">
      <summary>Agent trace</summary>
      <ul>${trace || "<li>No trace returned</li>"}</ul>
    </details>
  `;
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`${path}: ${detail.detail || response.statusText}`);
  }
  return response.json();
}

function setStatus(message) {
  $("status").textContent = message;
}

async function login() {
  const payload = {
    username: $("username").value,
    password: $("password").value,
  };
  const data = await api("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.token = data.access_token;
  localStorage.setItem("noshow_token", state.token);
  setStatus("Logged in. Loading dashboard...");
  await loadDashboard();
}

function renderMetrics(summary) {
  const cards = [
    ["Total bookings", Number(summary.total_bookings || 0).toLocaleString()],
    ["No-show rate", fmtPct(summary.no_show_rate)],
    ["Observed revenue at risk", fmtCurrency(summary.observed_revenue_at_risk)],
    ["Average booking price", fmtCurrency(summary.avg_price)],
  ];
  $("metrics").innerHTML = cards
    .map(([label, value]) => `<article class="metric"><p class="eyebrow">${label}</p><strong>${value}</strong></article>`)
    .join("");
}

function fillDimensionControls(dimensions) {
  const options = dimensions.map((dimension) => `<option value="${dimension}">${dimensionLabel(dimension)}</option>`).join("");
  $("dimensionSelect").innerHTML = options;
}

async function loadDashboard() {
  const [summary, dimensions] = await Promise.all([api("/api/summary"), api("/api/dimensions")]);
  state.dimensions = dimensions.dimensions;
  renderMetrics(summary);
  fillDimensionControls(state.dimensions);
  await loadSegments();
  connectSummaryStream();
  setStatus("Dashboard ready.");
}

function connectSummaryStream() {
  if (state.socket) state.socket.close();
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(`${protocol}://${location.host}/ws/summary?token=${encodeURIComponent(state.token)}`);
  state.socket.onmessage = (event) => renderMetrics(JSON.parse(event.data));
  state.socket.onopen = () => setStatus("Dashboard ready. Live summary stream connected.");
  state.socket.onerror = () => setStatus("Dashboard ready. Live summary stream unavailable; REST API still works.");
}

async function loadSegments() {
  const dimension = $("dimensionSelect").value || "branch";
  const minBookings = Number($("minBookings").value || 20);
  const data = await api(`/api/segments?dimension=${encodeURIComponent(dimension)}&min_bookings=${minBookings}&limit=12`);
  $("segmentTitle").textContent = `${dimensionLabel(dimension)} no-show rates`;
  const maxRate = Math.max(...data.rows.map((row) => Number(row.no_show_rate || 0)), 0.01);
  $("segmentBars").innerHTML = data.rows
    .map((row) => {
      const width = Math.max(4, (Number(row.no_show_rate || 0) / maxRate) * 100);
      const label = `${row.segment} (${Number(row.bookings).toLocaleString()})`;
      return `
        <div class="bar-row" title="${label}">
          <div class="bar-label">${row.segment}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
          <div class="bar-value">${fmtPct(row.no_show_rate)}</div>
        </div>
      `;
    })
    .join("");
}

async function loadRisk() {
  const riskBand = $("riskBandFilter").value || "All";
  const limit = Number($("riskLimit").value || 25);
  const data = await api(`/api/bookings/high-risk?risk_band=${encodeURIComponent(riskBand)}&limit=${limit}`);
  $("riskRows").innerHTML = data.rows.length
    ? data.rows
    .map((row) => {
      const band = String(row.risk_band || "Low").toLowerCase();
      return `
        <tr>
          <td>${row.booking_id ?? ""}</td>
          <td>${row.branch ?? ""}</td>
          <td>${row.room ?? ""}</td>
          <td>${customerStatus(row)}</td>
          <td>${row.country ?? ""}</td>
          <td><span class="risk-pill risk-${band}">${row.risk_band}<br>${fmtPct(row.predicted_no_show_probability)}</span></td>
          <td>${fmtPct(row.risk_score)}</td>
          <td>${fmtCurrency(row.expected_revenue_at_risk)}</td>
          <td>${row.intervention?.recommended_action || ""}</td>
        </tr>
      `;
    })
    .join("")
    : `<tr><td colspan="9">No bookings found for ${riskBand} risk.</td></tr>`;
}

async function askAssistant() {
  const answerBox = $("assistantAnswer");
  answerBox.innerHTML = `<div class="assistant-loading">Thinking...</div>`;
  answerBox.scrollIntoView({ behavior: "smooth", block: "center" });

  const data = await api("/api/assistant/query", {
    method: "POST",
    body: JSON.stringify({ question: $("assistantQuestion").value }),
  });
  renderAssistantResponse(data);
}

async function safe(action) {
  try {
    await action();
  } catch (error) {
    setStatus(error.message);
    if (action === askAssistant) {
      $("assistantAnswer").innerHTML = `<div class="assistant-error"><strong>Assistant error</strong><p>${escapeHtml(error.message)}</p></div>`;
    }
  }
}

$("loginBtn").addEventListener("click", () => safe(login));
$("refreshSegments").addEventListener("click", () => safe(loadSegments));
$("loadRisk").addEventListener("click", () => safe(loadRisk));
$("riskBandFilter").addEventListener("change", () => safe(loadRisk));
$("askAssistant").addEventListener("click", () => safe(askAssistant));

if (state.token) {
  safe(loadDashboard);
}
