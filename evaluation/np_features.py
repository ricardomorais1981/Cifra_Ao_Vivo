"""
Versão de AVALIAÇÃO do cálculo de chroma e do baixo, só com numpy/scipy.

Uso exclusivo do agente diário (ambiente sem librosa). Imita o que
local_engine/recognition/engine.py::_chroma_cqt faz com librosa:
  - HPSS por filtro de mediana (como librosa.effects.hpss: n_fft 2048,
    hop 512, kernel 31, máscara suave potência 2);
  - estimativa de afinação (desvio em frações de semitom);
  - "pseudo-CQT": STFT longa (n_fft 16384) com cada bin atribuído à
    nota mais próxima por peso gaussiano em escala log, normalizado pela
    largura de banda (como na CQT, cada nota pesa igual);
  - chroma L2 + suavização de 9 frames; baixo de Mi1 a Lá3 (30 semitons)
    normalizado por _normalize_bass do próprio motor.
NÃO substitui o código de produção. Os números medidos com ela são
aproximações do motor real.
"""
from __future__ import annotations

import numpy as np
from scipy import signal
from scipy.ndimage import median_filter, uniform_filter1d


def hpss_harmonic(y: np.ndarray, sr: int) -> np.ndarray:
    n_fft, hop = 2048, 512
    _, _, Z = signal.stft(y, fs=sr, nperseg=n_fft, noverlap=n_fft - hop,
                          boundary=None, padded=True)
    S = np.abs(Z).astype(np.float32)
    H = median_filter(S, size=(1, 31), mode="reflect")
    P = median_filter(S, size=(31, 1), mode="reflect")
    Hp, Pp = H ** 2, P ** 2
    mask = Hp / (Hp + Pp + 1e-10)
    _, yh = signal.istft(Z * mask, fs=sr, nperseg=n_fft,
                         noverlap=n_fft - hop, boundary=False)
    yh = yh[: len(y)]
    if len(yh) < len(y):
        yh = np.pad(yh, (0, len(y) - len(yh)))
    return yh.astype(np.float32)


def _spectrogram(y: np.ndarray, sr: int, hop: int, n_fft: int = 16384):
    pad = n_fft // 2
    yp = np.pad(y, (pad, pad))
    n_frames = 1 + (len(yp) - n_fft) // hop
    win = np.hanning(n_fft).astype(np.float32)
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n_frames)[:, None]
    frames = yp[idx] * win
    S = np.abs(np.fft.rfft(frames, axis=1)).T  # bins × frames
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    return S, freqs


def estimate_tuning(S: np.ndarray, freqs: np.ndarray) -> float:
    """Desvio de afinação em frações de semitom (−0,5..0,5)."""
    sel = (freqs > 100) & (freqs < 2000)
    Ss, fs = S[sel], freqs[sel]
    # picos locais acima da mediana do frame
    peaks = (Ss[1:-1] > Ss[:-2]) & (Ss[1:-1] > Ss[2:]) & \
            (Ss[1:-1] > np.median(Ss, axis=0, keepdims=True) * 4)
    r, c = np.nonzero(peaks)
    if len(r) < 50:
        return 0.0
    f = fs[1:-1][r]
    midi = 69 + 12 * np.log2(f / 440.0)
    dev = midi - np.round(midi)
    w = Ss[1:-1][r, c]
    hist, edges = np.histogram(dev, bins=100, range=(-0.5, 0.5), weights=w)
    return float((edges[np.argmax(hist)] + edges[np.argmax(hist) + 1]) / 2)


def _pitch_matrix(freqs: np.ndarray, tuning: float, p_lo: int, p_hi: int,
                  sigma: float = 0.25) -> np.ndarray:
    """Matriz (n_pitches × n_bins): peso de cada bin em cada nota MIDI."""
    with np.errstate(divide="ignore"):
        m = 69 + tuning + 12 * np.log2(np.maximum(freqs, 1e-6) / 440.0)
    pitches = np.arange(p_lo, p_hi + 1)
    W = np.exp(-0.5 * ((m[None, :] - (pitches[:, None] + tuning)) / sigma) ** 2)
    W[:, freqs < 20] = 0.0
    W /= W.sum(axis=1, keepdims=True) + 1e-12   # média por nota (≈ CQT)
    return W


def chroma_and_bass(y: np.ndarray, sr: int, hop: int = 2048):
    from local_engine.recognition.engine import _normalize_bass

    yh = hpss_harmonic(y, sr)
    S, freqs = _spectrogram(yh, sr, hop)
    tuning = estimate_tuning(S, freqs)

    # chroma: C1 (24) a B7 (107), 7 oitavas como chroma_cqt padrão
    W = _pitch_matrix(freqs, tuning, 24, 107)
    P = W @ S
    C = np.zeros((12, P.shape[1]))
    for i, p in enumerate(range(24, 108)):
        C[p % 12] += P[i]
    C /= np.linalg.norm(C, axis=0, keepdims=True) + 1e-12
    C = uniform_filter1d(C, size=9, axis=1)
    C /= np.maximum(np.linalg.norm(C, axis=0, keepdims=True), 1e-9)

    # baixo: E1 (28) a A3 (57)
    Wb = _pitch_matrix(freqs, tuning, 28, 57)
    Pb = Wb @ S
    bass = np.zeros((12, Pb.shape[1]))
    for i, p in enumerate(range(28, 58)):
        bass[p % 12] += Pb[i]
    bass = _normalize_bass(uniform_filter1d(bass, size=9, axis=1))
    return C, bass
