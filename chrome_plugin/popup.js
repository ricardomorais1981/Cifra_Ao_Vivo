// Cifra ao Vivo — popup do plugin
const $ = (id) => document.getElementById(id);
const send = (msg) => chrome.runtime.sendMessage({ target: "background", ...msg });
let tick = null;

function showStatus(text, isError = false) {
  const el = $("status");
  el.textContent = text;
  el.className = "status" + (isError ? " err" : "");
  el.classList.toggle("hidden", !text);
}

// Separa "Artista - Música - EP Tal | Canal - YouTube" em artista e música,
// tirando o que atrapalha a busca da letra.
function parseTitle(pageTitle) {
  let clean = pageTitle.replace(/^\(\d+\)\s*/, "")
    .replace(/\s*[-|]\s*(YouTube Music|YouTube|Spotify|Deezer|SoundCloud)\s*$/i, "")
    .replace(/[\(\[][^\)\]]*[\)\]]/g, " ")        // (Ao Vivo), [Clipe Oficial]...
    .replace(/#\S+/g, " ")                              // hashtags
    .replace(/\s+/g, " ").trim();
  const parts = clean.split(/\s+[-–—|]\s+|\s*\|\s*/).map(p => p.trim()).filter(Boolean);
  const tidy = (t) => t.replace(/\b(feat|ft)\.?\s.*$/i, "")
    .replace(/\b(ao vivo|clipe oficial|official( music)? video|lyric video|videoclipe)\b/gi, "")
    .replace(/\s+/g, " ").trim();
  if (parts.length >= 2) return { artist: tidy(parts[0]), title: tidy(parts[1]) };
  return { artist: "", title: tidy(parts[0] || "") };
}

function fmt(s) { return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`; }

function render(state) {
  const recording = state.status === "recording";
  $("idleView").classList.toggle("hidden", recording || state.status === "sending");
  $("recView").classList.toggle("hidden", !recording);
  clearInterval(tick);
  if (recording) {
    $("recInfo").textContent = [state.title, state.artist].filter(Boolean).join(" — ");
    const upd = () => $("timer").textContent = fmt((Date.now() - state.startedAt) / 1000);
    upd(); tick = setInterval(upd, 500);
  }
  if (state.status === "sending") showStatus("Enviando o áudio para o Cifra ao Vivo...");
  if (state.status === "error") { showStatus(state.error, true); send({ type: "reset" }); }
}

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const res = await send({ type: "state" });
  render(res.state);
  if (res.state.status === "idle" || res.state.status === "error") {
    const p = parseTitle(tab?.title || "");
    $("title").value = p.title; $("artist").value = p.artist;
    if (!res.online) {
      showStatus("O Cifra ao Vivo não está aberto. Rode o run.bat no computador antes de gravar.", true);
    }
  }

  $("btnStart").onclick = async () => {
    $("btnStart").disabled = true;
    showStatus("");
    const r = await send({ type: "start", tabId: tab.id, title: $("title").value.trim(), artist: $("artist").value.trim() });
    $("btnStart").disabled = false;
    if (!r.ok) return showStatus(r.error, true);
    render((await send({ type: "state" })).state);
  };
  $("btnStop").onclick = async () => {
    $("btnStop").disabled = $("btnCancel").disabled = true;
    clearInterval(tick);
    showStatus("Enviando o áudio para o Cifra ao Vivo...");
    const r = await send({ type: "stop" });
    if (!r.ok) { showStatus(r.error, true); render({ status: "idle" }); }
    else window.close();   // o resultado abre numa nova aba
    $("btnStop").disabled = $("btnCancel").disabled = false;
  };
  $("btnCancel").onclick = async () => {
    await send({ type: "cancel" });
    render({ status: "idle" }); showStatus("Gravação cancelada.");
  };
}
init();
