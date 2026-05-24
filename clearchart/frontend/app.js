"use strict";

const state = {
  imageFile: null,
  questions: [],
};

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

/* ---------- Carga de preguntas ---------- */
async function loadQuestions() {
  try {
    const res = await fetch("/api/questions");
    const data = await res.json();
    state.questions = data.questions || [];
    renderQuestions();
  } catch (err) {
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

/* ---------- Manejo de imagen ---------- */
function setImage(file) {
  if (!file || !file.type.startsWith("image/")) return;
  state.imageFile = file;
  const url = URL.createObjectURL(file);
  els.previewImg.src = url;
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

els.dropzone.addEventListener("click", (e) => {
  if (e.target === els.removeImg) return;
  els.fileInput.click();
});
els.dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); els.fileInput.click(); }
});
els.fileInput.addEventListener("change", (e) => setImage(e.target.files[0]));
els.removeImg.addEventListener("click", (e) => { e.stopPropagation(); clearImage(); });

["dragenter", "dragover"].forEach((evt) =>
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.remove("dragover");
  })
);
els.dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) setImage(file);
});

// Pegar captura con Ctrl/Cmd + V
window.addEventListener("paste", (e) => {
  const items = e.clipboardData?.items || [];
  for (const item of items) {
    if (item.type.startsWith("image/")) {
      setImage(item.getAsFile());
      break;
    }
  }
});

/* ---------- Estado del botón ---------- */
function requiredAnswered() {
  const answers = collectAnswers();
  return state.questions
    .filter((q) => q.required)
    .every((q) => (answers[q.id] || "").length > 0);
}

function refreshAnalyzeState() {
  const ready = state.imageFile && requiredAnswered();
  els.analyzeBtn.disabled = !ready;
  if (!state.imageFile) {
    els.actionMsg.textContent = "Subí un gráfico para empezar.";
    els.actionMsg.classList.remove("error");
  } else if (!requiredAnswered()) {
    els.actionMsg.textContent = "Completá las preguntas marcadas con *.";
    els.actionMsg.classList.remove("error");
  } else {
    els.actionMsg.textContent = "Todo listo.";
    els.actionMsg.classList.remove("error");
  }
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

function setLoading(loading) {
  els.analyzeBtn.classList.toggle("loading", loading);
  els.analyzeBtn.disabled = loading;
  if (loading) {
    els.actionMsg.textContent = "Leyendo tu gráfico y armando el mapa...";
    els.actionMsg.classList.remove("error");
  }
}

function showResult(markdown) {
  els.resultContent.innerHTML = renderMarkdown(markdown);
  els.resultCard.classList.remove("hidden");
  els.resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
}

els.newAnalysis.addEventListener("click", () => {
  els.resultCard.classList.add("hidden");
  els.resultContent.innerHTML = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
});

/* ---------- Render de markdown mínimo ---------- */
function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function inline(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function renderMarkdown(md) {
  const lines = (md || "").split("\n");
  let html = "";
  let listType = null;

  const closeList = () => {
    if (listType) { html += `</${listType}>`; listType = null; }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (/^---+$/.test(line.trim())) { closeList(); html += "<hr />"; continue; }
    if (/^#{1,6}\s+/.test(line)) {
      closeList();
      const text = line.replace(/^#{1,6}\s+/, "");
      html += `<h2>${inline(text)}</h2>`;
      continue;
    }
    const ol = line.match(/^\s*\d+\.\s+(.*)/);
    const ul = line.match(/^\s*[-*]\s+(.*)/);
    if (ol) {
      if (listType !== "ol") { closeList(); html += "<ol>"; listType = "ol"; }
      html += `<li>${inline(ol[1])}</li>`;
      continue;
    }
    if (ul) {
      if (listType !== "ul") { closeList(); html += "<ul>"; listType = "ul"; }
      html += `<li>${inline(ul[1])}</li>`;
      continue;
    }
    closeList();
    if (line.trim() === "") continue;
    html += `<p>${inline(line)}</p>`;
  }
  closeList();
  return html;
}

/* ---------- Init ---------- */
loadQuestions();
refreshAnalyzeState();
