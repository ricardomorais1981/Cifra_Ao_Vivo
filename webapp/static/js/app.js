/* ===================================================================
   Cifra ao Vivo v2.0 — Frontend
   =================================================================== */

"use strict";

// ---------------------------------------------------------------------------
// Estado
// ---------------------------------------------------------------------------
let currentTaskId   = null;
let pollTimer       = null;
let selectedFile    = null;
let lastTxtContent  = "";

// ---------------------------------------------------------------------------
// Elementos
// ---------------------------------------------------------------------------
const $ = id => document.getElementById(id);

const uploadPanel    = $("uploadPanel");
const progressPanel  = $("progressPanel");
const resultPanel    = $("resultPanel");
const errorPanel     = $("errorPanel");

const dropZone       = $("dropZone");
const fileInput      = $("fileInput");
const btnSelectFile  = $("btnSelectFile");
const selectedFileEl = $("selectedFile");
const btnProcess     = $("btnProcess");
const inputTitle     = $("inputTitle");
const inputArtist    = $("inputArtist");

const progressBar    = $("progressBar");
const progressMsg    = $("progressMsg");
const progressTitle  = $("progressTitle");
const btnCancelProg  = $("btnCancelProgress");

const statusBadge    = $("statusBadge");
const resultTitle    = $("resultTitle");
const resultArtist   = $("resultArtist");
const resultKey      = $("resultKey");
const resultTempo    = $("resultTempo");
const resultDuration = $("resultDuration");
const transposeInput = $("transposeInput");
const capoInput      = $("capoInput");
const lyricsOffsetInput = $("lyricsOffsetInput");
const flatsCheck     = $("flatsCheck");
const simplifyCheck  = $("simplifyCheck");
const btnExportTxt   = $("btnExportTxt");
const btnCopyTxt     = $("btnCopyTxt");
const btnNewFile     = $("btnNewFile");
const sheetContent   = $("sheetContent");
const qualityContent = $("qualityContent");

// ---------------------------------------------------------------------------
// Helpers de UI
// ---------------------------------------------------------------------------
function showPanel(name) {
  for (const p of [uploadPanel, progressPanel, resultPanel, errorPanel])
    p.classList.add("hidden");
  $(`${name}Panel`).classList.remove("hidden");
}

function setProgress(pct, msg) {
  progressBar.style.width = pct + "%";
  progressMsg.textContent = msg;
}

function formatDuration(s) {
  const m = Math.floor(s / 60);
  const ss = Math.round(s % 60);
  return `${m}:${String(ss).padStart(2, "0")}`;
}

function statusClass(status) {
  if (status === "aprovado")            return "badge-green";
  if (status === "aprovado_apos_correcao") return "badge-yellow";
  return "badge-red";
}
function statusLabel(status) {
  if (status === "aprovado")            return "✓ Aprovado";
  if (status === "aprovado_apos_correcao") return "✦ Corrigido";
  if (status === "qualidade_nao_confirmada") return "⚠ Incompleto";
  return status;
}

// ---------------------------------------------------------------------------
// Drop Zone
// ---------------------------------------------------------------------------
dropZone.addEventListener("click", () => fileInput.click());
btnSelectFile.addEventListener("click", e => { e.stopPropagation(); fileInput.click(); });

dropZone.addEventListener("dragover", e => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  if (e.dataTransfer.files.length) onFileSelected(e.dataTransfer.files[0]);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) onFileSelected(fileInput.files[0]);
});

function onFileSelected(file) {
  selectedFile = file;
  selectedFileEl.textContent = `📄 ${file.name}  (${(file.size / 1048576).toFixed(1)} MB)`;
  selectedFileEl.classList.remove("hidden");
  btnProcess.disabled = false;

  // Preenche título automaticamente se vazio
  if (!inputTitle.value) {
    const name = file.name.replace(/\.[^.]+$/, "").replace(/_/g, " ");
    inputTitle.value = name;
  }
}

// ---------------------------------------------------------------------------
// Processar
// ---------------------------------------------------------------------------
btnProcess.addEventListener("click", startProcessing);

async function startProcessing() {
  if (!selectedFile) return;

  showPanel("progress");
  setProgress(2, "Criando tarefa...");
  progressTitle.textContent = inputTitle.value || "Processando...";

  try {
    // 1. Cria tarefa
    const params = new URLSearchParams({
      title:  inputTitle.value,
      artist: inputArtist.value,
    });
    const r1 = await fetch(`/tasks?${params}`, { method: "POST" });
    if (!r1.ok) throw new Error(await r1.text());
    const { task_id } = await r1.json();
    currentTaskId = task_id;

    // 2. Envia áudio
    setProgress(5, "Enviando arquivo...");
    const fd = new FormData();
    fd.append("file", selectedFile);
    const r2 = await fetch(`/tasks/${task_id}/audio`, { method: "POST", body: fd });
    if (!r2.ok) throw new Error(await r2.text());

    // 3. Polling
    pollStatus(task_id);
  } catch (err) {
    showError(err.message);
  }
}

// ---------------------------------------------------------------------------
// Polling
// ---------------------------------------------------------------------------
function pollStatus(task_id) {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const r = await fetch(`/tasks/${task_id}`);
      if (!r.ok) return;
      const data = await r.json();

      setProgress(data.progress || 0, data.message || "...");

      if (data.status === "done") {
        clearInterval(pollTimer);
        await loadResult(task_id);
      } else if (data.status === "error") {
        clearInterval(pollTimer);
        showError(data.error || "Erro desconhecido.");
      }
    } catch (e) {
      // ignora erros de rede temporários
    }
  }, 800);
}

// ---------------------------------------------------------------------------
// Exibir resultado
// ---------------------------------------------------------------------------
async function loadResult(task_id) {
  try {
    const r = await fetch(`/tasks/${task_id}/result`);
    if (!r.ok) throw new Error(await r.text());
    const data = await r.json();

    // Preenche cabeçalho
    resultTitle.textContent  = data.title || "—";
    lyricsTitleInput.value  = data.title && data.title !== "Desconhecido" ? data.title : "";
    lyricsArtistInput.value = data.artist || "";
    lyricsStatus.textContent = "";
    const noLyrics = !data.lyrics || data.lyrics.length === 0;
    lyricsHint.textContent = noLyrics
      ? "A letra não foi encontrada automaticamente. Escreva o nome da música e do artista e clique em Buscar."
      : "Letra errada ou de outra versão? Escreva o nome da música e do artista e busque de novo.";
    lyricsCard.classList.toggle("hidden", !noLyrics);
    resultArtist.textContent = data.artist || "";
    resultKey.textContent    = data.key ? `🎼 Tom: ${data.key}` : "";
    resultTempo.textContent  = data.tempo ? `♩ ${Math.round(data.tempo)} BPM` : "";
    resultDuration.textContent = (data.duration ? `⏱ ${formatDuration(data.duration)}` : "")
      + (data.music_start >= 0.5 ? `  ·  ▶ começa em ${data.music_start.toFixed(1).replace(".", ",")} s` : "");
    resultDuration.title = data.music_start >= 0.5
      ? "O trecho antes disso (silêncio, fala ou abertura) foi ignorado." : "";

    statusBadge.textContent = statusLabel(data.pipeline_status);
    statusBadge.className   = "badge " + statusClass(data.pipeline_status);

    // Carrega TXT
    await refreshSheet(task_id);
    showPanel("result");
  } catch (err) {
    showError(err.message);
  }
}

async function refreshSheet(task_id) {
  const tid = task_id || currentTaskId;
  if (!tid) return;
  const params = new URLSearchParams({
    transpose: transposeInput.value || "0",
    capo:      capoInput.value || "0",
    lyrics_offset: lyricsOffsetInput.value || "0",
    flats:     flatsCheck.checked ? "true" : "false",
    simplify:  simplifyCheck.checked ? "true" : "false",
  });
  try {
    const r = await fetch(`/tasks/${tid}/export/txt?${params}`);
    lastTxtContent = await r.text();
    renderSheet(lastTxtContent);
  } catch (e) {
    sheetContent.textContent = "Erro ao carregar cifra.";
  }
}

function renderSheet(txt) {
  // Destaca linhas de acorde: linhas que contêm apenas letras de acorde (A-G, #, b, m, 7, /, espaços)
  const lines = txt.split("\n");
  const html  = lines.map(ln => {
    const isChord = (/^[\sA-Gb#mMdisujan/\d\(\)°+?]+$/.test(ln) && /[A-G]/.test(ln))
                 || /^\[(Intro|Instrumental|Final)\]/.test(ln);
    const escaped = ln.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    return isChord
      ? `<span class="chord-line">${escaped}</span>`
      : escaped;
  }).join("\n");
  sheetContent.innerHTML = html;

  // Preenche relatório de qualidade (seção entre separadores)
  const qualStart = txt.indexOf("RELATORIO DE QUALIDADE");
  const qualEnd   = txt.indexOf("LETRA E CIFRAS", qualStart);
  if (qualStart >= 0) {
    const q = qualEnd > 0
      ? txt.slice(qualStart, qualEnd)
      : txt.slice(qualStart);
    qualityContent.textContent = q.trim();
  }
}

// Recarrega quando muda transpose / bemóis / simplificar
transposeInput.addEventListener("change", () => refreshSheet());
capoInput.addEventListener("change",      () => refreshSheet());
lyricsOffsetInput.addEventListener("change", () => refreshSheet());
flatsCheck.addEventListener("change",     () => refreshSheet());
simplifyCheck.addEventListener("change",  () => refreshSheet());

// ---------------------------------------------------------------------------
// Exportar / Copiar
// ---------------------------------------------------------------------------
btnExportTxt.addEventListener("click", async () => {
  if (!currentTaskId) return;
  const params = new URLSearchParams({
    transpose: transposeInput.value || "0",
    capo:      capoInput.value || "0",
    lyrics_offset: lyricsOffsetInput.value || "0",
    flats:     flatsCheck.checked ? "true" : "false",
    simplify:  simplifyCheck.checked ? "true" : "false",
  });
  window.location.href = `/tasks/${currentTaskId}/export/txt?${params}`;
});

btnCopyTxt.addEventListener("click", async () => {
  if (!lastTxtContent) return;
  await navigator.clipboard.writeText(lastTxtContent);
  btnCopyTxt.textContent = "✓ Copiado!";
  setTimeout(() => { btnCopyTxt.textContent = "📋 Copiar"; }, 2000);
});

// ---------------------------------------------------------------------------
// Nova música / Cancelar
// ---------------------------------------------------------------------------
btnNewFile.addEventListener("click", resetApp);
btnCancelProg.addEventListener("click", resetApp);
$("btnRetry").addEventListener("click", resetApp);

function resetApp() {
  clearInterval(pollTimer);
  if (currentTaskId) {
    fetch(`/tasks/${currentTaskId}`, { method: "DELETE" }).catch(() => {});
    currentTaskId = null;
  }
  selectedFile = null;
  fileInput.value = "";
  selectedFileEl.textContent = "";
  selectedFileEl.classList.add("hidden");
  btnProcess.disabled = true;
  lastTxtContent = "";
  showPanel("upload");
}

// ---------------------------------------------------------------------------
// Erro
// ---------------------------------------------------------------------------
function showError(msg) {
  $("errorMsg").textContent = msg;
  showPanel("error");
}

// ---------------------------------------------------------------------------
// Aberto pelo plugin do Chrome: /?task=ID mostra o progresso e o resultado
// ---------------------------------------------------------------------------
(function openTaskFromUrl() {
  const tid = new URLSearchParams(location.search).get("task");
  if (!tid) return;
  history.replaceState(null, "", "/");
  currentTaskId = tid;
  progressTitle.textContent = "Captura do Chrome";
  setProgress(5, "Processando o áudio gravado...");
  showPanel("progress");
  pollStatus(tid);
})();

// ---------------------------------------------------------------------------
// Busca manual da letra
// ---------------------------------------------------------------------------
const lyricsCard        = $("lyricsCard");
const lyricsHint        = $("lyricsHint");
const lyricsStatus      = $("lyricsStatus");
const lyricsTitleInput  = $("lyricsTitleInput");
const lyricsArtistInput = $("lyricsArtistInput");
const btnSearchLyrics   = $("btnSearchLyrics");

$("btnToggleLyrics").addEventListener("click", () => {
  lyricsCard.classList.toggle("hidden");
  if (!lyricsCard.classList.contains("hidden")) lyricsTitleInput.focus();
});

async function searchLyrics() {
  if (!currentTaskId) return;
  const title = lyricsTitleInput.value.trim();
  if (!title) { lyricsStatus.textContent = "Escreva o nome da música."; return; }
  btnSearchLyrics.disabled = true;
  lyricsStatus.textContent = "Buscando a letra...";
  try {
    const params = new URLSearchParams({ title, artist: lyricsArtistInput.value.trim() });
    const r = await fetch(`/tasks/${currentTaskId}/lyrics?${params}`, { method: "POST" });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || "Não foi possível buscar a letra.");
    resultTitle.textContent  = data.title || title;
    resultArtist.textContent = data.artist || "";
    lyricsStatus.textContent = `✓ Letra encontrada (${data.n_lines} linhas).`;
    await refreshSheet();
    setTimeout(() => lyricsCard.classList.add("hidden"), 1500);
  } catch (err) {
    lyricsStatus.textContent = "⚠ " + err.message;
  } finally {
    btnSearchLyrics.disabled = false;
  }
}
btnSearchLyrics.addEventListener("click", searchLyrics);
for (const el of [lyricsTitleInput, lyricsArtistInput])
  el.addEventListener("keydown", e => { if (e.key === "Enter") searchLyrics(); });
