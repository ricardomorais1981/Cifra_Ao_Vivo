"""
Motor de reconhecimento de acordes via CQT + template matching + Viterbi.
Foco: música gospel brasileira e americana, pop/rock (1980-2000).

v2.3 — baixo como pista extra (desempata Em7 × G, Am7 × C etc.).
v2.2 — templates por nota+harmônicos, emissão por cosseno+prior.
v2.1 — melhorias baseadas em FMP AudioLabs, Chordino e literatura ISMIR:
  - Templates com decay harmônico (root=1.0, 5a=0.5, 3a=0.3) em vez de binários
  - hop_length=2048 (era 512) → frames de 93ms, CQT estável em baixas freq.
  - norm=2 (L2, era inf/L∞) → melhor discriminação de acordes menores
  - HPSS antes do CQT → remove percussão que contamina chroma
  - estimate_tuning() → corrige desvios de afinação antes do CQT
  - Suavização temporal (janela 9 frames) antes do NNLS
  - Viterbi self-transition prob=0.95 (era stability=4.0 ≈ 0.80)
  - Vocabulário expandido: add9, maj7 mantidos; dim mantido para vii°
"""

from __future__ import annotations
from typing import Callable, Optional
import numpy as np

# ---------------------------------------------------------------------------
# Templates de acordes (v2.2)
# Cada NOTA do acorde tem peso igual (terça e quinta são notas tocadas, não
# harmônicos fracos). O decaimento harmônico se aplica aos HARMÔNICOS de cada
# nota (h1..h6, s=0.6), como em Gómez 2006 / Chordino — não às notas do acorde.
# A v2.1 aplicava 0.3 à terça, o que apagava a diferença maior/menor e fazia
# sus2/dim vencerem.
# ---------------------------------------------------------------------------
QUALITIES = {            # intervalos em semitons a partir da fundamental
    "maj":  (0, 4, 7),
    "min":  (0, 3, 7),
    "7":    (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "min7": (0, 3, 7, 10),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "dim":  (0, 3, 6),
}
# Prior (log) por qualidade: tríades maiores/menores são o caso comum em
# pop/rock/gospel; qualidades raras precisam de evidência clara para vencer.
QUALITY_LOG_PRIOR = {
    "maj": 0.0, "min": 0.0,
    "7": -1.0, "min7": -0.6, "maj7": -1.5,
    "sus2": -2.5, "sus4": -2.5, "dim": -3.0,
}
QUALITY_NAMES = list(QUALITIES.keys())
N_QUALITIES   = len(QUALITY_NAMES)   # 8
N_ROOTS       = 12
N_STATES      = N_ROOTS * N_QUALITIES  # 96

_HARM_DECAY = 0.6
_N_HARM     = 6

def _note_profile(pc: int) -> np.ndarray:
    v = np.zeros(12)
    for k in range(1, _N_HARM + 1):
        v[(pc + int(round(12 * np.log2(k)))) % 12] += _HARM_DECAY ** (k - 1)
    return v

_TEMPLATES = np.zeros((N_STATES, 12), dtype=np.float64)
for _qi, (_qname, _ivs) in enumerate(QUALITIES.items()):
    for _root in range(12):
        t = np.zeros(12)
        for _iv in _ivs:
            t += _note_profile((_root + _iv) % 12)
        _TEMPLATES[_qi * N_ROOTS + _root] = t / np.linalg.norm(t)

_LOG_PRIOR = np.array([QUALITY_LOG_PRIOR[q] for q in QUALITY_NAMES
                       for _ in range(N_ROOTS)])


# Notas de cada acorde (1 = nota do acorde) e fundamental — usadas pelo baixo
_CHORD_TONES = np.zeros((N_STATES, 12))
_ROOT_ONEHOT = np.zeros((N_STATES, 12))
for _qi, (_qname, _ivs) in enumerate(QUALITIES.items()):
    for _root in range(12):
        _ROOT_ONEHOT[_qi * N_ROOTS + _root, _root] = 1.0
        for _iv in _ivs:
            _CHORD_TONES[_qi * N_ROOTS + _root, (_root + _iv) % 12] = 1.0
_OTHER_TONES = _CHORD_TONES - _ROOT_ONEHOT


def _build_templates() -> np.ndarray:
    return _TEMPLATES.copy()


# ---------------------------------------------------------------------------
# Matriz de transição HMM com self-transition prob
# Referência: Chordino selftransprob=0.99; FMP Beatles p≈0.95 para pop/rock
# ---------------------------------------------------------------------------
def _build_transition(self_prob: float = 0.95) -> np.ndarray:
    """
    Matriz N_STATES × N_STATES em log-espaço.
    self_prob: probabilidade de manter o acorde atual (0.90–0.99 para pop/rock).
    Probabilidade de mudar distribui-se igualmente entre os outros estados.
    """
    other_prob = (1.0 - self_prob) / (N_STATES - 1)
    T = np.full((N_STATES, N_STATES), other_prob, dtype=np.float64)
    np.fill_diagonal(T, self_prob)
    return np.log(T + 1e-12)


# ---------------------------------------------------------------------------
# CQT chroma com pré-processamento completo
# Referência: FMP C5S3, librosa docs, Mauch 2010
# ---------------------------------------------------------------------------
def _chroma_cqt(y: np.ndarray, sr: int, hop: int = 2048
                ) -> tuple[np.ndarray, np.ndarray]:
    """
    Retorna (chroma, bass), ambos 12 × n_frames:
    - chroma: CQT de toda a faixa, com HPSS, afinação, L2 e suavização;
    - bass:   só a região grave (Mi1 41 Hz a Lá3 220 Hz), onde fica o baixo.
              Normalizado pelo máximo de cada frame (1 = nota mais forte
              no grave). Frames sem baixo definido ficam próximos de zero.
    """
    import librosa
    from scipy.ndimage import uniform_filter1d

    y_harm, _ = librosa.effects.hpss(y)
    tuning = librosa.estimate_tuning(y=y_harm, sr=sr)

    C = librosa.feature.chroma_cqt(
        y=y_harm, sr=sr, hop_length=hop,
        bins_per_octave=36, tuning=tuning, norm=2,
    )
    C_smooth = uniform_filter1d(C, size=9, axis=1)
    col_norm = np.linalg.norm(C_smooth, axis=0, keepdims=True)
    col_norm[col_norm < 1e-9] = 1.0
    chroma = C_smooth / col_norm

    # Baixo: CQT de 30 semitons a partir de Mi1 (classe de altura 4)
    fmin = librosa.note_to_hz("E1")
    Q = np.abs(librosa.cqt(y_harm, sr=sr, hop_length=hop, fmin=fmin,
                           n_bins=30, bins_per_octave=12, tuning=tuning))
    bass = np.zeros((12, Q.shape[1]))
    for b in range(Q.shape[0]):
        bass[(4 + b) % 12] += Q[b]
    n = min(bass.shape[1], chroma.shape[1])
    bass = _normalize_bass(uniform_filter1d(bass[:, :n], size=9, axis=1))
    return chroma[:, :n], bass


def _normalize_bass(bass: np.ndarray) -> np.ndarray:
    """
    Divide pelo máximo de cada frame e multiplica pela 'clareza' do baixo
    (quanto a nota mais forte se destaca da média). Com baixo nítido, a nota
    dele fica perto de 1; sem baixo (só ruído espalhado), tudo fica perto de 0.
    """
    mx = bass.max(axis=0, keepdims=True) + 1e-12
    clarity = np.clip((mx - bass.mean(axis=0, keepdims=True)) / mx, 0.0, 1.0)
    clarity = np.clip((clarity - 0.4) / 0.4, 0.0, 1.0)   # <0.4 = sem baixo claro
    return bass / mx * clarity


# ---------------------------------------------------------------------------
# Emissão: similaridade de cosseno chroma×template + prior de qualidade
# (v2.1 usava NNLS sobre 96 templates sobrepostos: problema mal-posto que
#  espalhava energia entre acordes vizinhos)
# ---------------------------------------------------------------------------
_BETA = 25.0   # "temperatura": converte similaridade em log-probabilidade
_BASS_W = 6.0  # peso do baixo (ver _emission)

def _emission(chroma: np.ndarray, templates: np.ndarray,
              bass: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Retorna log-probabilidades normalizadas por frame (N_STATES × n_frames).

    Pontuação = cosseno(chroma, modelo) · β + prior da qualidade
              + peso do baixo · [baixo na fundamental + 0,3 · baixo em outra
                                 nota do acorde − 0,5 · baixo fora do acorde]
    O baixo desempata acordes que dividem quase todas as notas, como
    Em7 (Mi Sol Si Ré) × G (Sol Si Ré): o Mi no baixo indica Em7.
    A parcela de 0,3 mantém inversões (D/F#, C/E) ainda possíveis.
    """
    S = templates @ chroma                      # cosseno (ambos L2)
    scores = _BETA * S + _LOG_PRIOR[:, None]
    if bass is not None:
        n = min(bass.shape[1], chroma.shape[1])
        scores = scores[:, :n]
        b = bass[:, :n]
        on_root  = _ROOT_ONEHOT @ b
        on_other = np.max(_OTHER_TONES[:, :, None] * b[None, :, :], axis=1)
        off      = np.max((1 - _CHORD_TONES)[:, :, None] * b[None, :, :], axis=1)
        scores = scores + _BASS_W * (on_root + 0.3 * on_other - 0.5 * off)
    scores -= scores.max(axis=0, keepdims=True)
    log_norm = np.log(np.exp(scores).sum(axis=0, keepdims=True))
    return scores - log_norm


# ---------------------------------------------------------------------------
# Viterbi
# ---------------------------------------------------------------------------
def _viterbi(obs: np.ndarray, log_trans: np.ndarray) -> tuple[list[int], np.ndarray]:
    """
    obs: N_STATES × n_frames  (log-probabilidades de emissão)
    log_trans: N_STATES × N_STATES (log-probabilidades de transição)
    Retorna (sequência_estados, delta_último_frame).
    """
    n_frames = obs.shape[1]
    delta = obs[:, 0].copy()
    psi   = np.zeros((N_STATES, n_frames), dtype=np.int32)

    for t in range(1, n_frames):
        # Broadcast: delta[i] + log_trans[i,j] para todos i,j
        trans_scores = delta[:, None] + log_trans   # N×N
        best_prev    = trans_scores.argmax(axis=0)
        psi[:, t]    = best_prev
        delta        = trans_scores[best_prev, np.arange(N_STATES)] + obs[:, t]

    # Back-track
    path = [int(delta.argmax())]
    for t in range(n_frames - 1, 0, -1):
        path.append(int(psi[path[-1], t]))
    path.reverse()
    return path, delta


# ---------------------------------------------------------------------------
# Conversão estados → eventos
# ---------------------------------------------------------------------------
def _states_to_events(path: list[int], hop: int, sr: int,
                      min_chord_duration: float,
                      post: np.ndarray,
                      total_duration: float) -> list[dict]:
    """
    Agrupa frames consecutivos do mesmo estado em eventos de acorde.
    post: probabilidade por frame (N_STATES × n_frames).
    Confiança do segmento = probabilidade média da RAIZ escolhida
    (somando as qualidades), para não penalizar dúvida maj vs maj7.
    """
    events = []
    if not path:
        return events
    hop_dur = hop / sr
    root_post = post.reshape(N_QUALITIES, N_ROOTS, -1).sum(axis=0)  # 12 × T

    def _emit(a: int, b: int, end_t: float, state: int):
        if end_t - a * hop_dur < min_chord_duration:
            return
        qi, root = state // N_ROOTS, state % N_ROOTS
        conf = float(np.clip(root_post[root, a:b].mean(), 0.0, 1.0))
        events.append({"start": a * hop_dur, "end": end_t, "root": root,
                       "quality": QUALITY_NAMES[qi], "confidence": conf})

    start, cur = 0, path[0]
    for i in range(1, len(path)):
        if path[i] != cur:
            _emit(start, i, i * hop_dur, cur)
            start, cur = i, path[i]
    _emit(start, len(path), total_duration, cur)
    return events


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def recognize(
    y: np.ndarray,
    sr: int,
    hop: int = 2048,
    self_prob: float = 0.95,
    min_chord_duration: float = 0.3,
    progress_cb: Optional[Callable[[int, str], None]] = None,
) -> list[dict]:
    """
    Reconhece acordes num sinal de áudio mono float32.

    Parâmetros:
        y: sinal de áudio mono float32
        sr: taxa de amostragem
        hop: hop length em amostras (padrão 2048 = ~93ms @ 22050Hz)
        self_prob: probabilidade de self-transition no Viterbi (0.90–0.99)
        min_chord_duration: duração mínima de acorde em segundos
        progress_cb: callback(pct, mensagem)

    Retorna lista de dicts: {start, end, root, quality, confidence}
    """
    def _progress(pct: int, msg: str):
        if progress_cb:
            progress_cb(pct, msg)

    _progress(5,  "Separando harmônicos e estimando afinação...")
    chroma, bass = _chroma_cqt(y, sr, hop)

    _progress(30, "Comparando com modelos de acordes...")
    log_emit = _emission(chroma, _build_templates(), bass)

    _progress(60, "Decodificando com Viterbi...")
    log_trans = _build_transition(self_prob)
    path, _ = _viterbi(log_emit, log_trans)

    _progress(85, "Montando eventos...")
    total_duration = len(y) / sr
    events = _states_to_events(path, hop, sr, min_chord_duration,
                               np.exp(log_emit), total_duration)

    _progress(100, "Reconhecimento concluído.")
    return events
