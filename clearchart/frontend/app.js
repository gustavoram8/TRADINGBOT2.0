"use strict";

const state = { imageFile: null, questions: [] };

const els = {
  dropzone: document.getElementById("dropzone"),
  fileInput: document.getElementById("file-input"),
  dzEmpty: document.getElementById("dropzone-empty"),
  dzPreview: document.getElementById("dropzone-preview"),
  previewImg: document.getElementById("preview-img"),
  removeImg: document.getElementById("remove-img"),
  form: document.getElementById("questions-form"),
  analyzeBtn: document.getElementById("analyze-btn"),
  actionMsg: document.getElementById("action-msg"),
  resultCard: document.getElementById("step-result"),
  resultContent: document.getElementById("result-content"),
  newAnalysis: document.getElementById("new-analysis"),
};

/* ---------- Preguntas ---------- */
async function loadQuestions() {
  try {
    const res = await fetch("/api/questions");
    const data = await res.json();
    state.questions = data.questions || [];
    renderQuestions();
  } catch {
    els.form.innerHTML = '<p class="action-msg error">No se pudieron cargar las preguntas. ¿El servidor está corriendo?</p>';
  }
}

function renderQuestions() {
  els.form.innerHTML = "";
  state.questions.forEach((q) => {
    const field = document.createElement("div");
    field.className = "q-field";
    const label = document.createElement("label");
    label.setAttribute("for", `q-${q.id}`);
    label.innerHTML = q.label + (q.required ? '<span class="req">*</span>' : "");
    const input = document.createElement("textarea");
    input.id = `q-${q.id}`;
    input.name = q.id;
    input.rows = 2;
    input.placeholder = q.placeholder || "";
    input.addEventListener("input", refreshAnalyzeState);
    field.appendChild(label);
    field.appendChild(input);
    els.form.appendChild(field);
  });
}

function collectAnswers() {
  const answers = {};
  state.questions.forEach((q) => {
    const el = document.getElementById(`q-${q.id}`);
    answers[q.id] = el ? el.value.trim() : "";
  });
  return answers;
}

/* ---------- Imagen ---------- */
function setImage(file) {
  if (!file || !file.type.startsWith("image/")) return;
  state.imageFile = file;
  els.previewImg.src = URL.createObjectURL(file);
  els.dzEmpty.classList.add("hidden");
  els.dzPreview.classList.remove("hidden");
  refreshAnalyzeState();
}
function clearImage() {
  state.imageFile = null;
  els.fileInput.value = "";
  els.previewImg.src = "";
  els.dzEmpty.classList.remove("hidden");
  els.dzPreview.classList.add("hidden");
  refreshAnalyzeState();
}

els.dropzone.addEventListener("click", (e) => { if (e.target !== els.removeImg) els.fileInput.click(); });
els.dropzone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); els.fileInput.click(); } });
els.fileInput.addEventListener("change", (e) => setImage(e.target.files[0]));
els.removeImg.addEventListener("click", (e) => { e.stopPropagation(); clearImage(); });
["dragenter","dragover"].forEach(ev => els.dropzone.addEventListener(ev, (e) => { e.preventDefault(); els.dropzone.classList.add("dragover"); }));
["dragleave","drop"].forEach(ev => els.dropzone.addEventListener(ev, (e) => { e.preventDefault(); els.dropzone.classList.remove("dragover"); }));
els.dropzone.addEventListener("drop", (e) => { const f = e.dataTransfer.files[0]; if (f) setImage(f); });
window.addEventListener("paste", (e) => {
  for (const item of (e.clipboardData?.items || []))
    if (item.type.startsWith("image/")) { setImage(item.getAsFile()); break; }
});

/* ---------- Botón ---------- */
function requiredAnswered() {
  const a = collectAnswers();
  return state.questions.filter(q => q.required).every(q => (a[q.id] || "").length > 0);
}
function refreshAnalyzeState() {
  const ready = state.imageFile && requiredAnswered();
  els.analyzeBtn.disabled = !ready;
  els.actionMsg.classList.remove("error");
  els.actionMsg.textContent = !state.imageFile
    ? "Subí un gráfico para empezar."
    : !requiredAnswered() ? "Completá las preguntas marcadas con *." : "Todo listo.";
}

/* ---------- Análisis ---------- */
els.analyzeBtn.addEventListener("click", async () => {
  if (els.analyzeBtn.disabled) return;
  setLoading(true);
  const fd = new FormData();
  fd.append("image", state.imageFile);
  fd.append("answers", JSON.stringify(collectAnswers()));
  try {
    const res = await fetch("/api/analyze", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error desconocido.");
    showResult(data.analysis);
  } catch (err) {
    els.actionMsg.textContent = err.message;
    els.actionMsg.classList.add("error");
  } finally {
    setLoading(false);
  }
});

function setLoading(on) {
  els.analyzeBtn.classList.toggle("loading", on);
  els.analyzeBtn.disabled = on;
  if (on) { els.actionMsg.textContent = "Leyendo tu gráfico y redibujando el mapa..."; els.actionMsg.classList.remove("error"); }
}

function showResult(data) {
  els.resultContent.innerHTML = buildMapHTML(data);
  els.resultCard.classList.remove("hidden");
  els.resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
  setTimeout(() => drawChart(data), 50);
}

els.newAnalysis.addEventListener("click", () => {
  els.resultCard.classList.add("hidden");
  els.resultContent.innerHTML = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
});

/* ---------- Construcción del HTML del mapa ---------- */
function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function buildMapHTML(data) {
  if (!data || typeof data !== "object")
    return `<div class="map-card"><p class="action-msg error">Respuesta inesperada.</p></div>`;

  if (data.parse_error)
    return `<div class="map-card"><h3>Aviso</h3><p>${esc(data.raw)}</p></div>`;

  const dir = (data.direction || "").toLowerCase();
  const dirClass = dir.includes("bajist") ? "bajista" : dir.includes("alcist") ? "alcista" : "lateral";
  const arrow = dirClass === "bajista" ? "↓" : dirClass === "alcista" ? "↑" : "↔";
  const focusItems = (data.focus_list || []).map(f => `<li>${esc(f)}</li>`).join("");

  return `
<div class="map-wrapper">
  <div class="map-header ${dirClass}">
    <div class="direction-row">
      <span class="direction-arrow">${arrow}</span>
      <div>
        <div class="instrument-label">${esc(data.instrument)}</div>
        <span class="confidence">Confianza: ${esc(data.confidence)}</span>
      </div>
    </div>
    <div class="headline">${esc(data.headline)}</div>
  </div>

  <div class="chart-container">
    <canvas id="cc-chart"></canvas>
    <div class="chart-legend" id="cc-legend"></div>
  </div>

  <div class="map-grid">
    <div class="map-card invalidation">
      <h3>⚠️ Invalidación</h3>
      <p class="trigger"><strong>Si:</strong> ${esc(data.invalidation_trigger)}</p>
    </div>
    <div class="map-card focus">
      <h3>👁 En Qué Enfocarte</h3>
      <ul class="focus-list-items">${focusItems || "<li>Ver escenario principal</li>"}</ul>
    </div>
  </div>
</div>`;
}

/* ---------- Canvas chart ---------- */
const ZONE_COLORS = {
  resistance: { fill: "rgba(255,68,68,0.18)",   border: "#ff4444", label: "#ff6b6b" },
  support:    { fill: "rgba(68,255,107,0.18)",   border: "#44ff6b", label: "#6dff8a" },
  target:     { fill: "rgba(79,157,255,0.18)",   border: "#4f9dff", label: "#7ab8ff" },
  liquidity:  { fill: "rgba(255,215,0,0.14)",    border: "#ffd700", label: "#ffd700" },
  fvg:        { fill: "rgba(255,149,0,0.18)",    border: "#ff9500", label: "#ffaa40" },
  ob:         { fill: "rgba(255,149,0,0.18)",    border: "#ff9500", label: "#ffaa40" },
  imbalance:  { fill: "rgba(200,100,255,0.14)",  border: "#c864ff", label: "#d980ff" },
};

function drawChart(data) {
  const canvas = document.getElementById("cc-chart");
  if (!canvas) return;

  const W = 820;
  const H = 440;
  canvas.width = W;
  canvas.height = H;
  canvas.style.width = "100%";
  canvas.style.height = "auto";

  const ctx = canvas.getContext("2d");
  const PAD = { left: 85, right: 12, top: 24, bottom: 36 };
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top - PAD.bottom;

  const rangeHigh = Number(data.price_range?.high) || 0;
  const rangeLow  = Number(data.price_range?.low)  || 0;
  const priceSpan = rangeHigh - rangeLow || 1;
  const current   = Number(data.current_price) || null;
  const path      = (data.trend_path || []).map(Number).filter(n => !isNaN(n));
  const zones     = data.zones || [];

  const py = (p) => PAD.top + cH * (1 - (p - rangeLow) / priceSpan);
  const tx = (i, total) => PAD.left + cW * (i / Math.max(total - 1, 1));

  /* Background */
  ctx.fillStyle = "#0a0d12";
  ctx.fillRect(0, 0, W, H);

  /* Grid */
  const GRID = 6;
  for (let i = 0; i <= GRID; i++) {
    const y = PAD.top + cH * (i / GRID);
    const price = rangeHigh - (priceSpan * i / GRID);
    ctx.strokeStyle = "#1a2235";
    ctx.lineWidth = 1;
    ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(W - PAD.right, y); ctx.stroke();
    ctx.fillStyle = "#6b7a94";
    ctx.font = "11px -apple-system,sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(formatPrice(price), PAD.left - 6, y + 4);
  }

  /* Vertical grid (time) */
  const VGRID = 5;
  for (let i = 1; i < VGRID; i++) {
    const x = PAD.left + cW * (i / VGRID);
    ctx.strokeStyle = "#151e2e";
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x, PAD.top); ctx.lineTo(x, PAD.top + cH); ctx.stroke();
  }

  /* Zones (drawn back to front: watch → primary → critical) */
  const sorted = [...zones].sort((a, b) => {
    const rank = { watch: 0, primary: 1, critical: 2 };
    return (rank[a.importance] || 0) - (rank[b.importance] || 0);
  });

  for (const z of sorted) {
    const colors = ZONE_COLORS[z.type] || ZONE_COLORS.resistance;
    const ph = Number(z.price_high);
    const pl = Number(z.price_low ?? z.price_high);
    if (isNaN(ph)) continue;

    const yTop = py(Math.max(ph, pl));
    const yBot = py(Math.min(ph, pl));
    const zH   = Math.max(yBot - yTop, z.importance === "critical" ? 5 : 3);

    /* Fill */
    const alpha = z.importance === "critical" ? 1 : z.importance === "primary" ? 0.75 : 0.5;
    ctx.globalAlpha = alpha;
    ctx.fillStyle = colors.fill;
    ctx.fillRect(PAD.left, yTop, cW, zH);
    ctx.globalAlpha = 1;

    /* Border line at top */
    ctx.strokeStyle = colors.border;
    ctx.lineWidth = z.importance === "critical" ? 2.5 : 1.5;
    ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(PAD.left, yTop); ctx.lineTo(W - PAD.right, yTop); ctx.stroke();

    if (zH > 3) {
      ctx.strokeStyle = colors.border;
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(PAD.left, yBot); ctx.lineTo(W - PAD.right, yBot); ctx.stroke();
      ctx.setLineDash([]);
    }

    /* Label */
    const labelY = yTop - 5;
    ctx.font = z.importance === "critical"
      ? "bold 11.5px -apple-system,sans-serif"
      : "11px -apple-system,sans-serif";
    ctx.fillStyle = colors.label;
    ctx.textAlign = "left";
    ctx.fillText(`${z.label}  ${formatPrice(ph)}`, PAD.left + 5, labelY < PAD.top + 12 ? yBot + 14 : labelY);
  }

  /* Invalidation level */
  const invP = Number(data.invalidation_price);
  if (!isNaN(invP) && invP > 0) {
    const y = py(invP);
    ctx.strokeStyle = "#ffd700";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([8, 5]);
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(W - PAD.right, y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#ffd700";
    ctx.font = "10px -apple-system,sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(`Invalidación ${formatPrice(invP)}`, W - PAD.right - 4, y - 4);
  }

  /* Trend path — main price line */
  if (path.length >= 2) {
    /* Shadow / glow */
    ctx.shadowColor = "#4f9dff44";
    ctx.shadowBlur = 8;
    ctx.strokeStyle = "#c8d8f0";
    ctx.lineWidth = 2.5;
    ctx.lineJoin = "round";
    ctx.setLineDash([]);
    ctx.beginPath();
    path.forEach((p, i) => {
      const x = tx(i, path.length);
      const y = py(p);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.shadowBlur = 0;

    /* Dots at each path point */
    path.forEach((p, i) => {
      const x = tx(i, path.length);
      const y = py(p);
      ctx.beginPath();
      ctx.arc(x, y, i === path.length - 1 ? 5 : 3, 0, Math.PI * 2);
      ctx.fillStyle = i === path.length - 1 ? "#ffffff" : "#9ab8d8";
      ctx.fill();
    });

    /* Price labels along path (first and last) */
    ctx.fillStyle = "#c8d8f0";
    ctx.font = "10px -apple-system,sans-serif";
    ctx.textAlign = "left";
    if (path[0]) ctx.fillText(formatPrice(path[0]), tx(0, path.length) + 6, py(path[0]) - 5);
  }

  /* Current price line */
  if (current) {
    const y = py(current);
    const dirClass = (data.direction || "").toLowerCase();
    const lineColor = dirClass.includes("bajist") ? "#ff4444" : dirClass.includes("alcist") ? "#44ff6b" : "#ffd700";
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 4]);
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(W - PAD.right, y); ctx.stroke();
    ctx.setLineDash([]);

    /* Price tag */
    ctx.fillStyle = lineColor;
    ctx.font = "bold 11px -apple-system,sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(`▶ ${formatPrice(current)}`, PAD.left - 3, y + 4);
  }

  /* Frame border */
  ctx.strokeStyle = "#283044";
  ctx.lineWidth = 1;
  ctx.setLineDash([]);
  ctx.strokeRect(PAD.left, PAD.top, cW, cH);

  /* Time labels */
  ctx.fillStyle = "#4a5568";
  ctx.font = "10px -apple-system,sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("← Pasado", PAD.left + cW * 0.15, PAD.top + cH + 22);
  ctx.fillText("Ahora →", PAD.left + cW * 0.85, PAD.top + cH + 22);

  /* Legend */
  buildLegend(zones, data.direction);
}

function buildLegend(zones, direction) {
  const el = document.getElementById("cc-legend");
  if (!el) return;
  const dir = (direction || "").toLowerCase();
  el.innerHTML = zones.map(z => {
    const c = ZONE_COLORS[z.type] || ZONE_COLORS.resistance;
    const dot = `<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${c.border};margin-right:5px;vertical-align:middle"></span>`;
    return `<span class="legend-item">${dot}${z.label}</span>`;
  }).join("") + `<span class="legend-item"><span style="display:inline-block;width:24px;height:2px;background:#c8d8f0;margin-right:5px;vertical-align:middle"></span>Precio</span>`;
}

function formatPrice(p) {
  const n = Number(p);
  if (isNaN(n)) return "";
  return n >= 1000
    ? n.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 2 })
    : n.toFixed(4);
}

/* ---------- Init ---------- */
loadQuestions();
refreshAnalyzeState();
