"""
Métricas de avaliação de reconhecimento harmônico.

Baseadas nas métricas padrão de MIR (Music Information Retrieval):
- Root accuracy
- MajMin accuracy
- Thirds (tríades)
- Sevenths
- Tetrads
- Bass note accuracy
- Inversão accuracy
- Segmentação temporal

Cada métrica é calculada por sobreposição temporal (weighted overlap),
não por contagem de eventos — um evento longo tem mais peso que um curto.

Referência: Harte et al., "Automatic Chord Identification using a
Quantised Chromagram", AES 2005.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math

from evaluation.schemas.annotation import AnnotatedChord, ReferenceAnnotation


# ---------------------------------------------------------------------------
# Resultado de uma métrica
# ---------------------------------------------------------------------------
@dataclass
class MetricResult:
    name: str
    score: float                        # 0.0 – 1.0
    correct_seconds: float              # segundos corretos (sobreposição)
    total_seconds: float                # total avaliável
    n_events_ref: int                   # eventos na referência
    n_events_hyp: int                   # eventos na hipótese
    notes: list[str] = field(default_factory=list)

    @property
    def pct(self) -> str:
        return f"{self.score:.1%}"


@dataclass
class EvaluationReport:
    """Relatório completo para uma música."""
    music_id: str
    title: str
    artist: str
    split: str
    style: str
    difficulty: str

    root_accuracy:   Optional[MetricResult] = None
    majmin_accuracy: Optional[MetricResult] = None
    thirds_accuracy: Optional[MetricResult] = None
    sevenths_accuracy: Optional[MetricResult] = None
    tetrads_accuracy: Optional[MetricResult] = None
    bass_accuracy:   Optional[MetricResult] = None
    inversion_accuracy: Optional[MetricResult] = None
    segmentation:    Optional[MetricResult] = None

    n_ref_high_certainty: int = 0
    n_ref_total: int = 0
    evaluation_coverage: float = 0.0   # fração da música com referência high-certainty

    limitations: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"=== {self.title} ({self.artist}) ===",
            f"Split: {self.split}  |  Dificuldade: {self.difficulty}",
            f"Eventos alta certeza: {self.n_ref_high_certainty}/{self.n_ref_total}",
            f"Cobertura avaliada: {self.evaluation_coverage:.1%}",
        ]
        for name, r in [
            ("Root",     self.root_accuracy),
            ("MajMin",   self.majmin_accuracy),
            ("Tríades",  self.thirds_accuracy),
            ("Sétimas",  self.sevenths_accuracy),
            ("Tétrades", self.tetrads_accuracy),
            ("Baixo",    self.bass_accuracy),
            ("Inversão", self.inversion_accuracy),
        ]:
            if r:
                lines.append(f"  {name:<12}: {r.pct}  ({r.correct_seconds:.1f}/{r.total_seconds:.1f}s)")
        for lim in self.limitations:
            lines.append(f"  [!] {lim}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Motor de comparação por sobreposição temporal
# ---------------------------------------------------------------------------
def _overlap(a_start: float, a_end: float,
             b_start: float, b_end: float) -> float:
    """Sobreposição em segundos entre dois intervalos."""
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _weighted_score(
    ref_events: list[AnnotatedChord],
    hyp_events: list[dict],
    match_fn,
) -> tuple[float, float, float]:
    """
    Calcula score ponderado por duração temporal.

    match_fn(ref: AnnotatedChord, hyp: dict) -> bool

    Retorna (score, correct_seconds, total_seconds).
    """
    correct = 0.0
    total   = 0.0

    for ref in ref_events:
        for hyp in hyp_events:
            ov = _overlap(ref.start, ref.end, hyp["start"], hyp["end"])
            if ov <= 0:
                continue
            total += ov
            if match_fn(ref, hyp):
                correct += ov

    # Se algum segundo de referência não tem hipótese, conta como errado
    # (total já cobre isso pelo denominador)
    total_ref = sum(e.duration for e in ref_events)
    total = max(total, total_ref)

    score = correct / total if total > 0 else 0.0
    return score, correct, total


# ---------------------------------------------------------------------------
# Funções de match por nível
# ---------------------------------------------------------------------------
def _root_match(ref: AnnotatedChord, hyp: dict) -> bool:
    return ref.root_int == (hyp.get("root", -1) % 12)


def _majmin_match(ref: AnnotatedChord, hyp: dict) -> bool:
    if not _root_match(ref, hyp):
        return False
    ref_fam = ref.quality_family
    hyp_q   = hyp.get("quality", "")
    hyp_fam = "min" if (hyp_q.startswith("m") and not hyp_q.startswith("maj")) else "maj"
    return ref_fam == hyp_fam


def _thirds_match(ref: AnnotatedChord, hyp: dict) -> bool:
    """Tríade: fundamental + terça (maior ou menor)."""
    if not _root_match(ref, hyp):
        return False
    ref_q = ref.quality.lower()
    hyp_q = hyp.get("quality", "").lower()
    # Agrupa qualidades por terça
    _MAJOR_THIRDS = {"maj", "7", "maj7", "sus2", "sus4", "aug", "add9", "6", "9"}
    _MINOR_THIRDS = {"min", "min7", "m7b5", "dim", "dim7", "m6", "m9"}
    ref_fam = "maj" if ref_q in _MAJOR_THIRDS else ("min" if ref_q in _MINOR_THIRDS else None)
    hyp_fam = "maj" if hyp_q in _MAJOR_THIRDS else ("min" if hyp_q in _MINOR_THIRDS else None)
    return ref_fam is not None and ref_fam == hyp_fam


def _sevenths_match(ref: AnnotatedChord, hyp: dict) -> bool:
    """Fundamental + tipo de sétima (maior, menor, sem)."""
    if not _thirds_match(ref, hyp):
        return False
    _NO_7   = {"maj", "min", "sus2", "sus4", "aug", "dim", "add9", "6", "m6"}
    _MIN7   = {"7", "min7", "m7b5", "9", "m9", "11", "13"}
    _MAJ7   = {"maj7", "minmaj7"}
    _DIM7   = {"dim7"}

    def _7th_class(q):
        q = q.lower()
        if q in _NO_7:   return "none"
        if q in _MIN7:   return "min7"
        if q in _MAJ7:   return "maj7"
        if q in _DIM7:   return "dim7"
        return "other"

    return _7th_class(ref.quality) == _7th_class(hyp.get("quality", ""))


def _tetrads_match(ref: AnnotatedChord, hyp: dict) -> bool:
    """Acorde completo até a sétima — qualidade exata."""
    if not _root_match(ref, hyp):
        return False
    return ref.quality.lower() == hyp.get("quality", "").lower()


def _bass_match(ref: AnnotatedChord, hyp: dict) -> bool:
    """Nota do baixo correta (quando anotada)."""
    ref_bass = ref.bass_int
    if ref_bass is None:
        ref_bass = ref.root_int   # sem inversão → baixo = fundamental
    hyp_bass = hyp.get("bass")
    if hyp_bass is None:
        hyp_bass = hyp.get("root", -1) % 12
    else:
        hyp_bass = hyp_bass % 12
    return ref_bass == hyp_bass


def _inversion_match(ref: AnnotatedChord, hyp: dict) -> bool:
    """Inversão exata — avaliada apenas quando referência tem inversão anotada."""
    ref_bass = ref.bass_int
    hyp_bass = hyp.get("bass")
    if hyp_bass is not None:
        hyp_bass = hyp_bass % 12
    # Ambos sem baixo explícito = concordância (posição fundamental)
    if ref_bass is None and hyp_bass is None:
        return True
    if ref_bass is None or hyp_bass is None:
        return False
    return ref_bass == hyp_bass


# ---------------------------------------------------------------------------
# Segmentação temporal
# ---------------------------------------------------------------------------
def _segmentation_score(
    ref_events: list[AnnotatedChord],
    hyp_events: list[dict],
    tolerance: float = 0.35,
) -> tuple[float, float, float]:
    """
    Mede precisão dos limites de acorde.
    Um limite hipótese é correto se houver um limite referência a ± tolerance segundos.
    Retorna (f1, precision, recall).
    """
    ref_bounds = set()
    for e in ref_events:
        ref_bounds.add(round(e.start, 3))
        ref_bounds.add(round(e.end, 3))

    hyp_bounds = set()
    for e in hyp_events:
        hyp_bounds.add(round(e["start"], 3))
        hyp_bounds.add(round(e["end"], 3))

    def _has_match(t: float, pool: set) -> bool:
        return any(abs(t - p) <= tolerance for p in pool)

    tp_hyp = sum(1 for t in hyp_bounds if _has_match(t, ref_bounds))
    tp_ref = sum(1 for t in ref_bounds if _has_match(t, hyp_bounds))

    precision = tp_hyp / max(len(hyp_bounds), 1)
    recall    = tp_ref / max(len(ref_bounds), 1)
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)
    return f1, precision, recall


# ---------------------------------------------------------------------------
# Avaliação completa de uma música
# ---------------------------------------------------------------------------
def evaluate(
    reference: ReferenceAnnotation,
    hypothesis: list[dict],
    use_only_high_certainty: bool = True,
) -> EvaluationReport:
    """
    Compara a hipótese do motor com a anotação de referência.

    hypothesis: lista de dicts com chaves start, end, root (int 0-11),
                quality (str), bass (int|None).

    Avalia apenas eventos de alta certeza por padrão.
    """
    report = EvaluationReport(
        music_id   = reference.id,
        title      = reference.title,
        artist     = reference.artist,
        split      = reference.split,
        style      = reference.style,
        difficulty = reference.difficulty,
    )

    all_events  = reference.events
    eval_events = reference.high_certainty_events() if use_only_high_certainty \
                  else all_events

    report.n_ref_total         = len(all_events)
    report.n_ref_high_certainty = len(reference.high_certainty_events())

    if not eval_events:
        report.limitations.append(
            "Nenhum evento de alta certeza disponível — avaliação impossível.")
        return report

    total_ref_dur  = sum(e.duration for e in all_events)
    eval_dur       = sum(e.duration for e in eval_events)
    report.evaluation_coverage = eval_dur / total_ref_dur if total_ref_dur > 0 else 0.0

    if report.evaluation_coverage < 0.5:
        report.limitations.append(
            f"Apenas {report.evaluation_coverage:.0%} da música tem anotação "
            f"de alta certeza — resultados com incerteza elevada.")

    def _make(name, match_fn):
        score, correct, total = _weighted_score(eval_events, hypothesis, match_fn)
        return MetricResult(
            name            = name,
            score           = score,
            correct_seconds = correct,
            total_seconds   = total,
            n_events_ref    = len(eval_events),
            n_events_hyp    = len(hypothesis),
        )

    report.root_accuracy     = _make("Root",     _root_match)
    report.majmin_accuracy   = _make("MajMin",   _majmin_match)
    report.thirds_accuracy   = _make("Thirds",   _thirds_match)
    report.sevenths_accuracy = _make("Sevenths", _sevenths_match)
    report.tetrads_accuracy  = _make("Tetrads",  _tetrads_match)
    report.bass_accuracy     = _make("Bass",     _bass_match)

    # Inversão: avaliada apenas quando há eventos com baixo anotado
    inv_events = [e for e in eval_events if e.bass is not None]
    if inv_events:
        score, correct, total = _weighted_score(inv_events, hypothesis, _inversion_match)
        report.inversion_accuracy = MetricResult(
            name="Inversion", score=score,
            correct_seconds=correct, total_seconds=total,
            n_events_ref=len(inv_events), n_events_hyp=len(hypothesis),
        )
    else:
        report.limitations.append(
            "Nenhuma inversão anotada — métrica de inversão não calculada.")

    # Segmentação
    f1, prec, rec = _segmentation_score(eval_events, hypothesis)
    report.segmentation = MetricResult(
        name="Segmentation (F1)", score=f1,
        correct_seconds=prec, total_seconds=rec,
        n_events_ref=len(eval_events), n_events_hyp=len(hypothesis),
        notes=[f"Precision={prec:.1%}  Recall={rec:.1%}"],
    )

    return report
