"""
Pipeline de validação e correção harmônica.
Porta Python do harmony.js + validator.js da extensão v1.4.
Foco: música gospel brasileira e americana, pop/rock.

v2.1 — melhorias em key estimation:
  - Perfis BellmanBudge em vez de Krumhansl-Schmuckler
    (BB reduz confusões entre tonalidades relativas, ex: C major vs A minor)
  - Chroma construído a partir das notas dos acordes com pesos por duração
    e com contribuição completa de root+terça+quinta (não só root)
  - Desempate por modo: em empate ou margem <0.02, prefere major
    (pop/rock/gospel têm predominância maior; evita falso "D minor")
"""

from __future__ import annotations
import math
from typing import Optional

from shared.schemas.music_data import (
    ChordEvent, MusicData, PipelineStatus,
    ValidationResult, CorrectionEntry,
)

# ---------------------------------------------------------------------------
# Perfis BellmanBudge
# Referência: Bellman & Budge 2006 (Journal of New Music Research)
# Reduz confusões entre tonalidades relativas vs. Krumhansl-Schmuckler
# ---------------------------------------------------------------------------
_BB_MAJOR = [16.80, 0.86, 12.95, 1.41, 13.49, 11.93,
              1.25, 20.28, 1.80, 8.04,  0.62,  9.42]
_BB_MINOR = [18.16, 0.69,  12.99, 13.34, 1.07, 11.15,
              1.38, 21.07,  7.49, 1.53,  0.92,  10.21]


def _corr(a: list[float], b: list[float]) -> float:
    n  = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da  = math.sqrt(sum((x - ma) ** 2 for x in a))
    db  = math.sqrt(sum((y - mb) ** 2 for y in b))
    return num / (da * db + 1e-9)


def estimate_key(events: list[ChordEvent]) -> tuple[int, str]:
    """
    Estima tonalidade via perfis BellmanBudge.
    Retorna (root: 0-11, mode: "major"|"minor").

    Chroma construído com root (peso 1.0), quinta (0.5) e terça (0.3)
    ponderados pela duração de cada acorde.
    Desempate por modo: prefere major quando margem < 0.02.
    """
    chroma = [0.0] * 12
    for e in events:
        dur = e.duration
        # Root — peso total
        chroma[e.root % 12] += dur
        # Quinta — presente em todos os acordes
        chroma[(e.root + 7) % 12] += dur * 0.5
        # Terça — maior ou menor conforme qualidade
        if e.quality in ("maj", "maj7", "7", "sus2"):
            chroma[(e.root + 4) % 12] += dur * 0.3   # terça maior
        elif e.quality in ("min", "min7", "dim"):
            chroma[(e.root + 3) % 12] += dur * 0.3   # terça menor
        # sus4: quarta justa (sem terça)
        elif e.quality == "sus4":
            chroma[(e.root + 5) % 12] += dur * 0.3

    best_r, best_mode, best_score = 0, "major", -999.0
    for root in range(12):
        rotated = chroma[root:] + chroma[:root]
        score_maj = _corr(rotated, _BB_MAJOR)
        score_min = _corr(rotated, _BB_MINOR)
        # Prefere major em empate ou margem estreita (evita falso minor)
        if score_maj > best_score:
            best_score, best_r, best_mode = score_maj, root, "major"
        if score_min > best_score + 0.02:   # minor precisa superar major por margem
            best_score, best_r, best_mode = score_min, root, "minor"

    return _relative_tiebreak(events, best_r, best_mode)


_MINOR_FAMILY = ("min", "min7")
_MAJOR_FAMILY = ("maj", "7", "maj7", "sus2", "sus4")
RELATIVE_MARGIN = 1.25   # o menor precisa soar 25% mais que o maior para vencer


def _tonic_time(events: list[ChordEvent], root: int, mode: str) -> float:
    """Tempo total em que o acorde da tônica (root, no modo dado) soa."""
    fam = _MINOR_FAMILY if mode == "minor" else _MAJOR_FAMILY
    return sum(e.duration for e in events if e.root % 12 == root and e.quality in fam)


def _relative_tiebreak(events: list[ChordEvent], root: int, mode: str) -> tuple[int, str]:
    """
    Tom maior e seu relativo menor (C × Am, B × G#m) têm as mesmas notas, e os
    perfis de tonalidade quase empatam. Desempata pelo acorde da tônica: em
    G#m, o próprio G#m soa muito mais que B; em C maior, C soa tanto ou mais
    que Am. O menor só vence com margem (pop/gospel é mais vezes maior).
    """
    if mode == "major":
        maj_r, min_r = root, (root + 9) % 12
    else:
        maj_r, min_r = (root + 3) % 12, root
    t_maj = _tonic_time(events, maj_r, "major")
    t_min = _tonic_time(events, min_r, "minor")
    if t_min > RELATIVE_MARGIN * t_maj and t_min > 0:
        return min_r, "minor"
    if t_maj > 0 and t_maj >= t_min:
        return maj_r, "major"
    return root, mode


# ---------------------------------------------------------------------------
# Tabelas gospel
# ---------------------------------------------------------------------------
# Graus diatônicos (semitônios a partir da tônica)
_DIATONIC_MAJOR = {0, 2, 4, 5, 7, 9, 11}
_DIATONIC_MINOR = {0, 2, 3, 5, 7, 8, 10}

# Qualidades esperadas por grau (maior)
_GOSPEL_QUALITY_MAJOR = {
    0: ("maj", "maj7", "add9", "9"),    # I
    2: ("min", "min7"),                 # ii
    4: ("min", "min7"),                 # iii
    5: ("maj", "maj7", "add9"),         # IV
    7: ("maj", "7", "sus4"),            # V
    9: ("min", "min7"),                 # vi
    11: ("dim",),                       # vii°
}
_GOSPEL_QUALITY_MINOR = {
    0: ("min", "min7"),
    2: ("dim",),
    3: ("maj", "maj7"),
    5: ("min", "min7"),
    7: ("maj", "7"),
    8: ("maj", "maj7"),
    10: ("maj", "7"),
}


def _degree(root: int, key: int, mode: str) -> int:
    """Intervalo em semitônios entre a tônica e a nota root."""
    return (root - key) % 12


def _is_diatonic(root: int, key: int, mode: str) -> bool:
    d = _degree(root, key, mode)
    return d in (_DIATONIC_MAJOR if mode == "major" else _DIATONIC_MINOR)


def _expected_quality(root: int, quality: str, key: int, mode: str) -> bool:
    d = _degree(root, key, mode)
    table = _GOSPEL_QUALITY_MAJOR if mode == "major" else _GOSPEL_QUALITY_MINOR
    expected = table.get(d, ())
    return quality in expected


def _is_secondary_dominant(root: int, quality: str,
                            key: int, mode: str) -> bool:
    """V7/x — dominante secundária (preservar sempre).
    Preserva apenas acordes de sétima dominante (quality='7') que resolvem
    num grau diatônico, ou o grau V natural do tom (quality='maj').
    Acordes maiores em outros graus NÃO são preservados automaticamente.
    """
    if quality == "7":
        # Sétima dominante resolvendo num grau diatônico
        target = (root + 5) % 12
        return _is_diatonic(target, key, mode)
    if quality == "maj":
        # Só preserva se for o grau V natural (ex: G em Dó maior)
        return _degree(root, key, mode) == 7
    return False


def _is_plagal(prev_root: int, cur_root: int, key: int) -> bool:
    """IV → I (cadência plagal, muito comum no gospel)."""
    return (_degree(prev_root, key, "major") == 5 and
            _degree(cur_root, key, "major") == 0)


def _descending_bass(events: list[ChordEvent], idx: int) -> bool:
    """Detecta linha de baixo descendente C–G/B–Am–F/A."""
    if idx < 2:
        return False
    basses = [
        events[i].bass if events[i].bass is not None else events[i].root
        for i in range(max(0, idx - 2), idx + 1)
    ]
    return all(basses[i] > basses[i + 1] for i in range(len(basses) - 1))


def _detect_modulation(events: list[ChordEvent],
                       total_duration: float) -> Optional[float]:
    """Detecta modulação de 1-2 semitons nos últimos 40% da música."""
    if total_duration < 60 or len(events) < 10:
        return None
    cutoff = total_duration * 0.6
    late = [e for e in events if e.start >= cutoff]
    if len(late) < 4:
        return None
    early_key, _ = estimate_key([e for e in events if e.start < cutoff])
    late_key, _  = estimate_key(late)
    diff = abs(late_key - early_key) % 12
    if diff in (1, 2, 11, 10):  # 1-2 semitônios para cima ou para baixo
        return cutoff
    return None


# ---------------------------------------------------------------------------
# Primeira validação
# ---------------------------------------------------------------------------
def validate_recognition(
    events: list[ChordEvent],
    total_duration: float,
    opts: Optional[dict] = None,
) -> ValidationResult:
    opts = opts or {}
    min_coverage   = opts.get("min_coverage",   0.95)
    min_confidence = opts.get("min_confidence", 0.75)
    max_osc        = opts.get("max_oscillation", 0.15)
    min_coherence  = opts.get("min_coherence",  0.60)
    min_agreement  = opts.get("min_agreement",  0.70)

    if not events or total_duration <= 0:
        return ValidationResult(passed=False, score=0.0,
                                notes=["Nenhum evento de acorde encontrado."])

    # 1. Cobertura
    covered = sum(e.duration for e in events)
    coverage = min(covered / total_duration, 1.0)

    # 2. Confiança média
    confidence = sum(e.confidence for e in events) / len(events)

    # 3. Oscilação (mudanças de acorde rápidas < 0.4s)
    quick = sum(1 for e in events if e.duration < 0.4)
    oscillation = 1.0 - quick / max(len(events), 1)

    # 4. Coerência harmônica
    key, mode = estimate_key(events)
    n_coherent = sum(
        1 for e in events
        if _is_diatonic(e.root, key, mode) or
           _is_secondary_dominant(e.root, e.quality, key, mode)
    )
    harmonic_coherence = n_coherent / len(events)

    # 5. Concordância (acordes repetidos com mesma qualidade)
    from collections import Counter
    roots = Counter(e.root for e in events)
    dominant_root = roots.most_common(1)[0][0]
    n_agree = sum(1 for e in events if e.root == dominant_root or
                  e.quality in ("maj", "min", "7"))
    agreement = min(n_agree / len(events), 1.0)

    score = (coverage * 0.25 + confidence * 0.25 +
             oscillation * 0.15 + harmonic_coherence * 0.20 +
             agreement * 0.15)

    passed = (coverage >= min_coverage and
              confidence >= min_confidence and
              oscillation >= (1 - max_osc) and
              harmonic_coherence >= min_coherence and
              agreement >= min_agreement)

    notes = []
    if coverage < min_coverage:
        notes.append(f"Cobertura baixa: {coverage:.0%}")
    if confidence < min_confidence:
        notes.append(f"Confiança baixa: {confidence:.0%}")
    if oscillation < (1 - max_osc):
        notes.append("Oscilação elevada (mudanças rápidas de acorde)")
    if harmonic_coherence < min_coherence:
        notes.append(f"Coerência harmônica baixa: {harmonic_coherence:.0%}")

    return ValidationResult(
        passed=passed, score=score,
        coverage=coverage, confidence=confidence,
        oscillation=oscillation,
        harmonic_coherence=harmonic_coherence,
        agreement=agreement,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Correção harmônica
# ---------------------------------------------------------------------------
def correct_harmony(
    events: list[ChordEvent],
    key: int,
    mode: str,
    max_change_pct: float = 0.10,
) -> tuple[list[ChordEvent], list[CorrectionEntry]]:
    """
    Corrige inconsistências harmônicas sem reprocessar o áudio.
    Preserva dominantes secundárias, cadências plagais, linhas de baixo.
    Altera no máximo max_change_pct dos eventos.
    """
    corrected = [ChordEvent(
        start=e.start, end=e.end, root=e.root, quality=e.quality,
        bass=e.bass, confidence=e.confidence,
        alternatives=list(e.alternatives), uncertain=e.uncertain,
    ) for e in events]

    max_changes = max(1, int(len(events) * max_change_pct))
    log: list[CorrectionEntry] = []
    n_changes = 0

    for i, e in enumerate(corrected):
        if n_changes >= max_changes:
            break

        # Preservações
        if _is_secondary_dominant(e.root, e.quality, key, mode):
            continue
        if i > 0 and _is_plagal(corrected[i-1].root, e.root, key):
            continue
        if _descending_bass(corrected, i):
            continue

        # Qualidade inesperada para grau diatônico?
        if _is_diatonic(e.root, key, mode):
            if not _expected_quality(e.root, e.quality, key, mode):
                table = (_GOSPEL_QUALITY_MAJOR if mode == "major"
                         else _GOSPEL_QUALITY_MINOR)
                deg = _degree(e.root, key, mode)
                expected_q = table.get(deg, ("maj",))
                new_q = expected_q[0]
                if new_q != e.quality:
                    orig_name = e.chord_name()
                    corrected[i].quality = new_q
                    log.append(CorrectionEntry(
                        t=e.start,
                        original=orig_name,
                        corrected=corrected[i].chord_name(),
                        reason=f"Qualidade inesperada para grau {deg} em {mode}",
                        certainty=0.75,
                    ))
                    n_changes += 1
            continue

        # Acorde cromático: marcar como incerto se confiança baixa
        if e.confidence < 0.65 and not e.uncertain:
            corrected[i].uncertain = True
            log.append(CorrectionEntry(
                t=e.start,
                original=e.chord_name(),
                corrected=e.chord_name() + "(?)",
                reason="Acorde não-diatônico com baixa confiança",
                certainty=0.5,
            ))
            n_changes += 1

    return corrected, log


# ---------------------------------------------------------------------------
# Segunda validação
# ---------------------------------------------------------------------------
def validate_correction(
    original: list[ChordEvent],
    corrected: list[ChordEvent],
    log_entries: list[CorrectionEntry],
) -> ValidationResult:
    """Verifica se a correção não introduziu novos problemas."""
    notes = []

    # 1. Todas as correções têm justificativa?
    all_justified = len(log_entries) == 0 or all(
        len(e.reason) > 5 for e in log_entries
    )

    # 2. Preservação de acordes confiantes
    n_confident = sum(1 for e in original if e.confidence >= 0.80)
    n_preserved = sum(
        1 for o, c in zip(original, corrected)
        if o.confidence >= 0.80 and o.root == c.root and o.quality == c.quality
    )
    preservation = n_preserved / max(n_confident, 1)

    # 3. Pct de mudanças ≤ 10%
    n_changed = sum(
        1 for o, c in zip(original, corrected)
        if o.root != c.root or o.quality != c.quality
    )
    change_pct = n_changed / max(len(original), 1)
    change_ok  = change_pct <= 0.10

    # 4. Ambiguidades marcadas?
    n_uncertain_before = sum(1 for e in original if e.uncertain)
    n_uncertain_after  = sum(1 for e in corrected if e.uncertain)
    ambiguity_handled  = n_uncertain_after >= n_uncertain_before

    score = (0.30 * float(all_justified) +
             0.30 * preservation +
             0.20 * float(change_ok) +
             0.20 * float(ambiguity_handled))

    if not all_justified:
        notes.append("Algumas correções sem justificativa registrada.")
    if preservation < 0.95:
        notes.append(f"Accordes confiantes alterados: {1-preservation:.0%}")
    if not change_ok:
        notes.append(f"Muitas correções: {change_pct:.0%} (limite 10%)")

    passed = all_justified and preservation >= 0.90 and change_ok

    return ValidationResult(
        passed=passed, score=score,
        coverage=1.0 - change_pct,
        confidence=preservation,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Pipeline completo
# ---------------------------------------------------------------------------
def run_pipeline(music: MusicData) -> MusicData:
    """
    Executa as duas camadas de validação/correção.
    Atualiza music.pipeline_status, .validation_1, .validation_2, .corrections.
    """
    music.pipeline_status = PipelineStatus.PROCESSING

    if not music.chords:
        music.pipeline_status = PipelineStatus.ERROR
        music.error_message = "Nenhum acorde reconhecido."
        return music

    # --- Etapa 1: validação do reconhecimento ---
    v1 = validate_recognition(music.chords, music.duration)
    music.validation_1 = v1

    # Detectar modulação
    music.modulation_at = _detect_modulation(music.chords, music.duration)

    if v1.passed:
        music.pipeline_status = PipelineStatus.APPROVED
        # Estimar tonalidade
        key, mode = estimate_key(music.chords)
        from shared.schemas.music_data import NOTE_NAMES_SHARP
        music.key = NOTE_NAMES_SHARP[key] + (" " + mode if mode == "minor" else "")
        return music

    # --- Etapa 2: correção harmônica ---
    key, mode = estimate_key(music.chords)
    from shared.schemas.music_data import NOTE_NAMES_SHARP
    music.key = NOTE_NAMES_SHARP[key] + (" " + mode if mode == "minor" else "")

    corrected, corr_log = correct_harmony(music.chords, key, mode)
    music.corrections = corr_log

    # --- Etapa 3: validação da correção ---
    v2 = validate_correction(music.chords, corrected, corr_log)
    music.validation_2 = v2

    if v2.passed:
        music.chords = corrected
        music.pipeline_status = PipelineStatus.APPROVED_AFTER_FIX
    else:
        music.chords = corrected   # usa mesmo assim, mas marca como não confirmado
        music.pipeline_status = PipelineStatus.QUALITY_UNCONFIRMED

    return music
