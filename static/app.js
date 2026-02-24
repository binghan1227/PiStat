'use strict';

const charts = {};

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtBytes(bytes) {
  if (bytes === null || bytes === undefined) return '—';
  const gb = bytes / 1073741824;
  if (gb >= 1) return gb.toFixed(2) + ' GB';
  const mb = bytes / 1048576;
  if (mb >= 1) return mb.toFixed(1) + ' MB';
  return (bytes / 1024).toFixed(0) + ' KB';
}

function fmtUptime(seconds) {
  if (!seconds) return '—';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function colorClass(value, warn = 70, danger = 85) {
  if (value === null || value === undefined) return '';
  if (value >= danger) return 'red';
  if (value >= warn) return 'yellow';
  return 'green';
}

function applyColor(cardId, value, warn, danger) {
  const el = document.getElementById(cardId);
  if (!el) return;
  el.classList.remove('green', 'yellow', 'red');
  const cls = colorClass(value, warn, danger);
  if (cls) el.classList.add(cls);
}

// ── Current stats ─────────────────────────────────────────────────────────────

async function fetchCurrent() {
  try {
    const res = await fetch('/api/current');
    if (!res.ok) return;
    const d = await res.json();

    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    set('val-cpu', d.cpu_percent != null ? d.cpu_percent.toFixed(1) : '—');
    set('val-mem', d.mem_percent != null ? d.mem_percent.toFixed(1) : '—');
    set('val-temp', d.cpu_temp != null ? d.cpu_temp.toFixed(1) : '—');
    set('val-disk', d.disk_percent != null ? d.disk_percent.toFixed(1) : '—');

    const load = (d.load_1 != null)
      ? `${d.load_1.toFixed(2)} / ${d.load_5.toFixed(2)} / ${d.load_15.toFixed(2)}`
      : '—';
    set('val-load', load);

    const net = (d.net_bytes_sent != null)
      ? `${fmtBytes(d.net_bytes_sent)} / ${fmtBytes(d.net_bytes_recv)}`
      : '—';
    set('val-net', net);

    set('val-uptime', fmtUptime(d.uptime_seconds));

    applyColor('card-cpu', d.cpu_percent);
    applyColor('card-mem', d.mem_percent);
    applyColor('card-temp', d.cpu_temp, 65, 80);
    applyColor('card-disk', d.disk_percent);

    const ts = d.timestamp ? new Date(d.timestamp * 1000).toLocaleTimeString() : '—';
    const lu = document.getElementById('last-updated');
    if (lu) lu.textContent = `Updated ${ts}`;
  } catch (e) {
    console.warn('fetchCurrent failed:', e);
  }
}

// ── History / Charts ──────────────────────────────────────────────────────────

async function fetchHistory(metric, hours = 1) {
  const res = await fetch(`/api/history?metric=${metric}&hours=${hours}`);
  if (!res.ok) return [];
  return res.json();
}

function makeChart(canvasId, label, color) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  return new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [{
        label,
        data: [],
        borderColor: color,
        backgroundColor: color + '22',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.3,
        fill: true,
      }],
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: 'time',
          time: { tooltipFormat: 'HH:mm:ss' },
          ticks: { maxTicksLimit: 8 },
        },
        y: { beginAtZero: true },
      },
      plugins: { legend: { display: false } },
    },
  });
}

function initCharts() {
  charts.cpu  = makeChart('chart-cpu',  'CPU %',  '#4f8ef7');
  charts.mem  = makeChart('chart-mem',  'Mem %',  '#34c98a');
  charts.temp = makeChart('chart-temp', 'Temp °C','#f76b4f');
}

async function refreshCharts() {
  const configs = [
    { key: 'cpu',  metric: 'cpu_percent' },
    { key: 'mem',  metric: 'mem_percent'  },
    { key: 'temp', metric: 'cpu_temp'     },
  ];

  for (const { key, metric } of configs) {
    const chart = charts[key];
    if (!chart) continue;
    try {
      const rows = await fetchHistory(metric, 1);
      chart.data.datasets[0].data = rows.map(r => ({
        x: r.ts * 1000,
        y: r.value,
      }));
      chart.update('none');
    } catch (e) {
      console.warn(`refreshCharts(${metric}) failed:`, e);
    }
  }
}

// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  fetchCurrent();
  initCharts();
  refreshCharts();

  setInterval(fetchCurrent, 5000);
  setInterval(refreshCharts, 60000);
});
