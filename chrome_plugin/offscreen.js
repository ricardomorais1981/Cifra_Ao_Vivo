// Cifra ao Vivo — gravador (documento offscreen)
// Recebe o stream da aba, continua tocando o som para o usuário,
// grava em mono 22050 Hz e, ao parar, envia um WAV para o app local.

const SAMPLE_RATE = 22050;   // mesma taxa usada pelo motor (TARGET_SR)
const MAX_SECONDS = 15 * 60;  // para e envia sozinho após 15 minutos

let stream = null, ctx = null, node = null, player = null;
let chunks = [], nSamples = 0;

async function startRecording(streamId) {
  stream = await navigator.mediaDevices.getUserMedia({
    audio: { mandatory: { chromeMediaSource: "tab", chromeMediaSourceId: streamId } },
    video: false,
  });

  // Ao capturar, o Chrome silencia a aba: devolve o som ao usuário em qualidade total
  player = new Audio();
  player.srcObject = stream;
  player.play().catch(() => {});

  // Gravação em 22050 Hz (o Chrome reamostra a entrada)
  ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
  await ctx.audioWorklet.addModule("recorder-worklet.js");
  const src = ctx.createMediaStreamSource(stream);
  node = new AudioWorkletNode(ctx, "recorder-processor");
  chunks = []; nSamples = 0;
  let limitHit = false;
  node.port.onmessage = (e) => {
    chunks.push(e.data); nSamples += e.data.length;
    if (!limitHit && nSamples >= SAMPLE_RATE * MAX_SECONDS) {
      limitHit = true;
      chrome.runtime.sendMessage({ target: "background", type: "ended" });
    }
  };
  const mute = ctx.createGain(); mute.gain.value = 0;   // mantém o grafo ativo sem tocar em dobro
  src.connect(node).connect(mute).connect(ctx.destination);

  stream.getAudioTracks().forEach(t => t.onended = () =>
    chrome.runtime.sendMessage({ target: "background", type: "ended" }));
}

async function stopRecording() {
  try { node && node.disconnect(); } catch {}
  try { ctx && await ctx.close(); } catch {}
  try { player && (player.pause(), player.srcObject = null); } catch {}
  try { stream && stream.getTracks().forEach(t => { t.onended = null; t.stop(); }); } catch {}
  const data = new Float32Array(nSamples);
  let off = 0;
  for (const c of chunks) { data.set(c, off); off += c.length; }
  chunks = []; nSamples = 0; stream = ctx = node = player = null;
  return data;
}

function encodeWav(samples, sr) {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVE");
  w(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sr, true); v.setUint32(28, sr * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  w(36, "data"); v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: "audio/wav" });
}

async function upload(server, title, artist, samples) {
  if (samples.length < SAMPLE_RATE * 10)
    throw new Error("Gravação muito curta (menos de 10 s).");
  const params = new URLSearchParams({ title: title || "", artist: artist || "" });
  const r1 = await fetch(`${server}/tasks?${params}`, { method: "POST" });
  if (!r1.ok) throw new Error("O app recusou a tarefa: " + await r1.text());
  const { task_id } = await r1.json();
  const fd = new FormData();
  fd.append("file", encodeWav(samples, SAMPLE_RATE), "captura_aba.wav");
  const r2 = await fetch(`${server}/tasks/${task_id}/audio`, { method: "POST", body: fd });
  if (!r2.ok) throw new Error("O app recusou o áudio: " + await r2.text());
  return task_id;
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.target !== "offscreen") return;
  (async () => {
    if (msg.type === "start") {
      try { await startRecording(msg.streamId); return { ok: true }; }
      catch (e) { return { ok: false, error: "Não foi possível gravar a aba: " + e.message }; }
    }
    if (msg.type === "stop") {
      const samples = await stopRecording();
      if (!msg.send) return { ok: true };
      try { return { ok: true, taskId: await upload(msg.server, msg.title, msg.artist, samples) }; }
      catch (e) { return { ok: false, error: e.message }; }
    }
    return { ok: false, error: "Mensagem desconhecida." };
  })().then(sendResponse);
  return true;
});
