import { authFetch } from "./api.js";

// ---------- utils ----------
function fmt2(x) {
  const n = Number(x);
  if (!Number.isFinite(n)) return "-";
  return n.toFixed(2);
}

function fmtSigned(x) {
  const n = Number(x);
  if (!Number.isFinite(n)) return "-";
  const s = n > 0 ? "+" : "";
  return s + n.toFixed(2);
}

function clsPnL(x) {
  const n = Number(x);
  if (!Number.isFinite(n) || n === 0) return "pnl0";
  return n > 0 ? "pnlPlus" : "pnlMinus";
}

// ---------- profile ----------
async function loadMe() {
  const token = localStorage.getItem("access_token");
  if (!token) {
    window.location.href = "/login";
    return;
  }

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
  if (!el) return;

  el.innerHTML = `
    <img class="avatar" src="${u.photo_url || ""}" alt="" onerror="this.style.display='none'">
    <div style="flex:1;">
      <div class="pname">${fullName} <span class="pmuted">${uname}</span></div>
      <div class="pmuted">Cash: ${fmt2(a.cash)} • user_id: ${u.id}</div>
    </div>
    <button id="logoutBtn" class="danger" style="margin-left:auto;">Выйти</button>
  `;

  const btn = document.getElementById("logoutBtn");
  if (btn) {
    btn.addEventListener("click", () => {
      localStorage.removeItem("access_token");
      localStorage.removeItem("account_id");
      window.location.href = "/login";
    });
  }
}

// ---------- leaderboard ----------
async function loadLeaderboard() {
  const el = document.getElementById("leaderboard");
  if (!el) return;

  el.innerHTML = `<div class="muted">Рейтинг: загрузка…</div>`;

  const res = await fetch("/api/leaderboard?top=10");
  if (!res.ok) {
    el.innerHTML = `<div class="muted">Рейтинг: ошибка ${res.status}</div>`;
    return;
  }

  const data = await res.json();
  const items = data.items || [];

  if (!items.length) {
    el.innerHTML = `
      <div style="font-weight:600;margin-bottom:6px;">Рейтинг пользователей</div>
      <div class="muted">Пока нет пользователей</div>
    `;
    return;
  }

  const rows = items.map(it => {
    const u = it.user || {};
    const uname = u.username ? `@${u.username}` : "—";
    const img = u.photo_url
      ? `<img class="avatar" src="${u.photo_url}" alt="" onerror="this.style.display='none'">`
      : `<div class="avatar" style="width:36px;height:36px;border-radius:50%;background:#2b2f3a;"></div>`;

    return `
      <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid rgba(255,255,255,.06);">
        <div style="width:28px;" class="muted">#${it.rank}</div>
        ${img}
        <div style="flex:1;">
          <div class="pname">${uname}</div>
          <div class="muted">Equity: ${fmt2(it.equity)} • Cash: ${fmt2(it.cash)}</div>
        </div>
      </div>
    `;
  }).join("");

  el.innerHTML = `
    <div style="font-weight:600;margin-bottom:6px;">Рейтинг пользователей</div>
    ${rows}
  `;
}

// ---------- portfolio (with PnL) ----------
async function loadPortfolio() {
  const el = document.getElementById("portfolio");
  if (!el) return;

  el.innerHTML = `<div class="muted">Портфель: загрузка…</div>`;

  const res = await authFetch("/api/portfolio");
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    el.innerHTML = `<div class="muted">Ошибка портфеля: ${(data && (data.detail || JSON.stringify(data))) || res.status}</div>`;
    return;
  }

  const data = await res.json();
  const cash = data.account?.cash ?? 0;

  const summary = data.summary || {};
  const positionsValue = summary.positions_value ?? 0;
  const positionsPnLRub = summary.positions_pnl_rub ?? 0;
  const positionsPnLPct = summary.positions_pnl_pct ?? 0;
  const equity = summary.equity ?? (Number(cash) + Number(positionsValue));

  const positions = data.positions || [];

  el.innerHTML = `
    <div style="display:flex; gap:18px; flex-wrap:wrap; align-items:baseline; margin-bottom:10px;">
      <div><b>Equity:</b> ${fmt2(equity)}</div>
      <div class="muted">Cash: ${fmt2(cash)}</div>
      <div class="muted">Positions: ${fmt2(positionsValue)}</div>
      <div class="${clsPnL(positionsPnLRub)}">PnL: ${fmtSigned(positionsPnLRub)} (${fmtSigned(positionsPnLPct)}%)</div>
    </div>

    <table id="ptbl">
      <thead>
        <tr>
          <th>Тикер</th>
          <th>Компания</th>
          <th>Кол-во</th>
          <th>Avg buy</th>
          <th>Last</th>
          <th>Стоимость</th>
          <th>PnL, ₽</th>
          <th>PnL, %</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  `;

  const tbody = el.querySelector("#ptbl tbody");
  if (!tbody) return;

  if (!positions.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="muted">Позиции пустые</td></tr>`;
    return;
  }

  for (const p of positions) {
    const tr = document.createElement("tr");
    tr.dataset.secid = p.secid;
    tr.style.cursor = "pointer";

    tr.innerHTML = `
      <td>${p.secid}</td>
      <td>${p.name ?? p.secid}</td>
      <td>${p.qty}</td>
      <td>${fmt2(p.avg_price)}</td>
      <td>${fmt2(p.last)}</td>
      <td>${fmt2(p.value)}</td>
      <td class="${clsPnL(p.pnl_rub)}">${fmtSigned(p.pnl_rub)}</td>
      <td class="${clsPnL(p.pnl_rub)}">${fmtSigned(p.pnl_pct)}%</td>
    `;

    tr.addEventListener("click", () => {
      window.location.href = `/stock?secid=${encodeURIComponent(p.secid)}`;
    });

    tbody.appendChild(tr);
  }
}

// ---------- popular ----------
async function loadPopular() {
  const tbl = document.getElementById("tbl");
  if (!tbl) return;

  const res = await fetch("/api/market/popular-today?top=15");
  const data = await res.json().catch(() => ({ items: [] }));

  const tbody = document.querySelector("#tbl tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  for (const it of (data.items || [])) {
    const tr = document.createElement("tr");
    tr.dataset.secid = it.secid;
    tr.style.cursor = "pointer";
    tr.innerHTML = `
      <td>${it.secid}</td>
      <td>${it.name ?? it.secid}</td>
      <td>${it.last ?? "-"}</td>
      <td>${it.valtoday ?? "-"}</td>
    `;
    tr.addEventListener("click", () => {
      window.location.href = `/stock?secid=${encodeURIComponent(it.secid)}`;
    });
    tbody.appendChild(tr);
  }
}

// ---------- init ----------
window.addEventListener("DOMContentLoaded", async () => {
  await loadMe();
  await loadLeaderboard();
  await loadPortfolio();
  await loadPopular();
});
