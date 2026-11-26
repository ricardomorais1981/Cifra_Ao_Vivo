// Cifra ao Vivo — plugin de captura da aba (service worker)
// Coordena popup <-> documento offscreen (que grava e envia o áudio).

const SERVER = "http://127.0.0.1:8000";

// Ícone desenhado pelo próprio plugin (não depende dos arquivos da pasta icons)
function drawIcon(size) {
  const c = new OffscreenCanvas(size, size), g = c.getContext("2d");
  const r = size / 5;
  g.fillStyle = "#1f6feb";
  g.beginPath(); g.roundRect(0, 0, size, size, r); g.fill();
  g.strokeStyle = "rgba(255,255,255,.92)"; g.lineWidth = Math.max(1, size / 14);
  for (let i = 0; i < 4; i++) {
    const x = size * (0.26 + 0.16 * i);
    g.beginPath(); g.moveTo(x, size * 0.18); g.lineTo(x, size * 0.82); g.stroke();
  }
  g.fillStyle = "#d32f2f"; g.strokeStyle = "#fff"; g.lineWidth = Math.max(1, size / 16);
  g.beginPath(); g.arc(size * 0.72, size * 0.72, size * 0.17, 0, 2 * Math.PI); g.fill(); g.stroke();
  return g.getImageData(0, 0, size, size);
}
function setIcon() {
  try { chrome.action.setIcon({ imageData: { 16: drawIcon(16), 32: drawIcon(32) } }); } catch (e) {}
}
chrome.runtime.onInstalled.addListener(setIcon);
chrome.runtime.onStartup.addListener(setIcon);
setIcon();

async function getState() {
  const { state } = await chrome.storage.session.get("state");
  return state || { status: "idle" };
}
async function setState(state) {
  await chrome.storage.session.set({ state });
}

async function ensureOffscreen() {
  const existing = await chrome.runtime.getContexts({ contextTypes: ["OFFSCREEN_DOCUMENT"] });
  if (existing.length) return;
  await chrome.offscreen.createDocument({
    url: "offscreen.html",
    reasons: ["USER_MEDIA"],
    justification: "Gravar o áudio da aba para gerar a cifra",
  });
}
async function closeOffscreen() {
  const existing = await chrome.runtime.getContexts({ contextTypes: ["OFFSCREEN_DOCUMENT"] });
  if (existing.length) await chrome.offscreen.closeDocument();
}

async function serverOnline() {
  try {
    const r = await fetch(`${SERVER}/health`, { cache: "no-store" });
    return r.ok;
  } catch { return false; }
}

async function start({ tabId, title, artist }) {
  const st = await getState();
  if (st.status === "recording" || st.status === "sending")
    return { ok: false, error: "Já existe uma gravação em andamento." };
  if (!(await serverOnline()))
    return { ok: false, error: "O Cifra ao Vivo não está aberto. Rode o run.bat e tente de novo." };

  let streamId;
  try {
    streamId = await chrome.tabCapture.getMediaStreamId({ targetTabId: tabId });
  } catch (e) {
    return { ok: false, error: "Não foi possível capturar esta aba (páginas internas do Chrome não podem ser gravadas). " + e.message };
  }

  await ensureOffscreen();
  const res = await chrome.runtime.sendMessage({ target: "offscreen", type: "start", streamId });
  if (!res || !res.ok) {
    await closeOffscreen();
    return { ok: false, error: (res && res.error) || "Falha ao iniciar a gravação." };
  }
  await setState({ status: "recording", tabId, title, artist, startedAt: Date.now() });
  chrome.action.setBadgeBackgroundColor({ color: "#d32f2f" });
  chrome.action.setBadgeText({ text: "REC" });
  return { ok: true };
}

async function stop(send) {
  const st = await getState();
  if (st.status !== "recording") return { ok: false, error: "Nenhuma gravação em andamento." };
  chrome.action.setBadgeText({ text: send ? "..." : "" });
  await setState({ ...st, status: send ? "sending" : "idle" });
  const res = await chrome.runtime.sendMessage({
    target: "offscreen", type: "stop", send,
    server: SERVER, title: st.title, artist: st.artist,
  });
  await closeOffscreen();
  chrome.action.setBadgeText({ text: "" });

  if (!send) { await setState({ status: "idle" }); return { ok: true }; }
  if (!res || !res.ok) {
    await setState({ status: "error", error: (res && res.error) || "Falha ao enviar o áudio." });
    return { ok: false, error: (res && res.error) || "Falha ao enviar o áudio." };
  }
  await setState({ status: "idle", lastTask: res.taskId });
  chrome.tabs.create({ url: `${SERVER}/?task=${encodeURIComponent(res.taskId)}` });
  return { ok: true, taskId: res.taskId };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.target !== "background") return;
  (async () => {
    switch (msg.type) {
      case "start":   return start(msg);
      case "stop":    return stop(true);
      case "cancel":  return stop(false);
      case "state":   return { ok: true, state: await getState(), online: await serverOnline() };
      case "ended":   // a aba fechou ou a captura terminou sozinha
        return (await getState()).status === "recording" ? stop(true) : { ok: true };
      case "reset":   await setState({ status: "idle" }); return { ok: true };
    }
    return { ok: false, error: "Mensagem desconhecida." };
  })().then(sendResponse);
  return true;  // resposta assíncrona
});

// Fecha a gravação se a aba gravada for fechada
chrome.tabs.onRemoved.addListener(async (tabId) => {
  const st = await getState();
  if (st.status === "recording" && st.tabId === tabId) stop(true);
});
