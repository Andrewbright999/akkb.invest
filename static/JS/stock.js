function getTokenOrRedirect() {
  const token = localStorage.getItem("access_token");
  if (!token) {
    window.location.href = "/login";
    throw new Error("No token");
  }
  return token;
}

// fetch с Bearer-токеном
async function authFetch(url, options = {}) {
  const token = getTokenOrRedirect();
  const headers = Object.assign({}, options.headers || {}, {
    "Authorization": `Bearer ${token}`,
  });
  return fetch(url, { ...options, headers });
}

function qs(name) { return new URLSearchParams(window.location.search).get(name); }
function isoDate(d) { return d.toISOString().slice(0, 10); }

function periodToFromDate(period) {
  const to = new Date();
  const from = new Date(to);

  if (period === "7d") from.setDate(to.getDate() - 7);
  else if (period === "1m") from.setMonth(to.getMonth() - 1);
  else if (period === "3m") from.setMonth(to.getMonth() - 3);
  else if (period === "6m") from.setMonth(to.getMonth() - 6);
  else if (period === "1y") from.setFullYear(to.getFullYear() - 1);
  else if (period === "ytd") { from.setMonth(0, 1); from.setHours(0, 0, 0, 0); }
  else if (period === "max") from.setFullYear(to.getFullYear() - 10);

  return { from, to };
}

function toNum(x) {
  const n = Number(String(x ?? "").replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

function safeCandles(raw) {
  return (raw || [])
    .filter(c => {
      const o = toNum(c.open), h = toNum(c.high), l = toNum(c.low), cl = toNum(c.close);
      const t = c.t || c.begin || c.date || c.datetime;
      if (!t) return false;
      if (o === null || h === null || l === null || cl === null) return false;
      return true;
    })
    .map(c => ({
      t: c.t || c.begin || c.date || c.datetime,
      open: toNum(c.open),
      high: toNum(c.high),
      low: toNum(c.low),
      close: toNum(c.close),
    }));
}

function drawCandles(candles) {
  const el = document.getElementById("chart_wrap");
  if (!candles || candles.length === 0) {
    el.innerHTML = "<div class='muted'>Нет данных для графика</div>";
    return;
  }

  const options = {
    legend: 'none',
    explorer: { actions: ['dragToZoom', 'rightClickToReset'], axis: 'horizontal', keepInBounds: true }
  };

  // Формат Google CandlestickChart: [X, low, open, close, high]
  const arr = candles.map(c => [new Date(c.t), c.low, c.open, c.close, c.high]);
  const data = google.visualization.arrayToDataTable(arr, true);

  new google.visualization.CandlestickChart(el).draw(data, options);
}

function drawLine(candles) {
  const el = document.getElementById("chart_wrap");
  if (!candles || candles.length === 0) {
    el.innerHTML = "<div class='muted'>Нет данных для графика</div>";
    return;
  }

  const options = {
    legend: { position: 'none' },
    explorer: { actions: ['dragToZoom', 'rightClickToReset'], axis: 'horizontal', keepInBounds: true }
  };

  const arr = candles.map(c => [new Date(c.t), c.close]);
  arr.unshift(["Date", "Close"]);
  const data = google.visualization.arrayToDataTable(arr);

  new google.visualization.LineChart(el).draw(data, options);
}

async function loadMe() {
  const token = localStorage.getItem("access_token");
  if (!token) { window.location.href = "/login"; return; }

  const res = await authFetch("/api/me");
  if (!res.ok) {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
    return;
  }

  const data = await res.json();
  const u = data.user;
  const a = data.account;

  const fullName = [u.first_name, u.last_name].filter(Boolean).join(" ") || "Без имени";
  const uname = u.username ? `@${u.username}` : "";

  const el = document.getElementById("profile");
  el.innerHTML = `
    <img class="avatar" src="${u.photo_url || ""}" alt="" onerror="this.style.display='none'">
    <div style="flex:1;">
      <div class="pname">${fullName} <span class="pmuted">${uname}</span></div>
      <div class="pmuted">Cash: ${a.cash} • user_id: ${u.id}</div>
    </div>
    <button id="logoutBtn" class="danger" style="margin-left:auto;">Выйти</button>
  `;

  document.getElementById("logoutBtn").addEventListener("click", () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("account_id");
    window.location.href = "/login";
  });
}


async function loadLast(secid) {
  const r = await fetch(`/api/market/last/${encodeURIComponent(secid)}`);
  if (!r.ok) return null;
  const j = await r.json();
  return toNum(j.last);
}

async function loadMyPosition(secid) {
  const r = await authFetch(`/api/positions/${encodeURIComponent(secid)}`);
  if (!r.ok) return { qty: 0, avg_price: 0 };

  const p = await r.json().catch(() => null);
  return {
    qty: Number(p?.qty ?? 0) || 0,
    avg_price: Number(p?.avg_price ?? 0) || 0,
  };
}


async function trade(side) {
  const secid = (document.getElementById("secid").textContent || "").trim();
  const qtyRaw = document.getElementById("tradeQty").value;
  const qty = toNum(qtyRaw);

  if (!secid) { document.getElementById("tradeMsg").textContent = "Нет secid"; return; }
  if (qty === null || qty <= 0) { document.getElementById("tradeMsg").textContent = "qty должен быть > 0"; return; }

  document.getElementById("tradeMsg").textContent = "Отправка…";

  const url = side === "BUY" ? "/api/trade/buy" : "/api/trade/sell";
  const body = { secid, qty }; // без price

  const r = await authFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await r.json().catch(() => null);
  if (!r.ok) {
    document.getElementById("tradeMsg").textContent =
      (data && (data.detail || JSON.stringify(data))) || `Ошибка: ${r.status}`;
    return;
  }

  document.getElementById("tradeMsg").textContent = "OK";

  await loadMe(); // обновить cash после сделки
  const pos = await loadMyPosition(secid);
  document.getElementById("myQty").textContent = pos.qty > 0 ? String(pos.qty) : "0";
  document.getElementById("myAvg").textContent = pos.qty > 0 ? `Avg buy: ${pos.avg_price}` : "";

  const last = await loadLast(secid);
  if (last !== null) document.getElementById("last").textContent = String(last);
}

async function loadStockAndChart() {
  getTokenOrRedirect(); // защищаем страницу

  const secid = (qs("secid") || "").toUpperCase();
  if (!secid) { document.getElementById("title").textContent = "Нет secid"; return; }

  document.getElementById("secid").textContent = secid;
  document.getElementById("title").textContent = `(${secid})`;

  const last = await loadLast(secid);
  const pos = await loadMyPosition(secid);
  document.getElementById("myQty").textContent = pos.qty > 0 ? String(pos.qty) : "0";

const avgEl = document.getElementById("myAvg");
avgEl.textContent = pos.qty > 0 ? `Avg buy: ${pos.avg_price}` : "";

  document.getElementById("last").textContent = last === null ? "-" : String(last);

  document.getElementById("status").textContent = "Загрузка…";
  const period = document.getElementById("period").value;
  const { from, to } = periodToFromDate(period);

  const candlesRes = await fetch(
    `/api/market/candles/${encodeURIComponent(secid)}?from=${isoDate(from)}&to=${isoDate(to)}&interval=24`
  );
  const payload = await candlesRes.json().catch(() => ({}));
  const candles = safeCandles(payload.candles || []);

  const chartType = document.getElementById("chartType").value;
  google.charts.setOnLoadCallback(() => {
    if (chartType === "line") drawLine(candles);
    else drawCandles(candles);
  });

  document.getElementById("status").textContent = `Период: ${period}, свечей: ${candles.length}`;
}

document.getElementById("reloadBtn").addEventListener("click", loadStockAndChart);
document.getElementById("period").addEventListener("change", loadStockAndChart);
document.getElementById("chartType").addEventListener("change", loadStockAndChart);

document.getElementById("buyBtn").addEventListener("click", () => trade("BUY"));
document.getElementById("sellBtn").addEventListener("click", () => trade("SELL"));

// старт
loadMe();
loadStockAndChart();
