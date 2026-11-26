"""
Avaliador principal do motor Cifra ao Vivo.

Uso:
    python -m evaluation.evaluator [--split dev|test|all] [--id gospel_001]

Lê anotações de evaluation/reference/annotations/*.json
Executa o motor sobre evaluation/reference/audio/<audio_file>
Compara resultados com evaluation/metrics.py
Gera relatório em evaluation/reports/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Optional

# Garante que o raiz do projeto está no path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from evaluation.schemas.annotation import ReferenceAnnotation, Certainty
from evaluation.metrics import evaluate, EvaluationReport


# ---------------------------------------------------------------------------
# Carregamento da coleção
# ---------------------------------------------------------------------------
_ANN_DIR   = os.path.join(_ROOT, "evaluation", "reference", "annotations")
_AUDIO_DIR = os.path.join(_ROOT, "evaluation", "reference", "audio")
_RPT_DIR   = os.path.join(_ROOT, "evaluation", "reports")


def load_collection(split: Optional[str] = None) -> list[ReferenceAnnotation]:
    """
    Carrega todas as anotações do diretório padrão.
    Se split='dev' ou 'test', filtra pelo campo split.
    """
    if not os.path.isdir(_ANN_DIR):
        return []

    refs = []
    for fname in sorted(os.listdir(_ANN_DIR)):
        if not fname.endswith(".json"):
            continue
        try:
            ref = ReferenceAnnotation.load(os.path.join(_ANN_DIR, fname))
            if split and ref.split != split:
                continue
            refs.append(ref)
        except Exception as e:
            print(f"[AVISO] Falha ao carregar {fname}: {e}")
    return refs


# ---------------------------------------------------------------------------
# Executa motor sobre um arquivo de áudio
# ---------------------------------------------------------------------------
def run_engine(audio_path: str) -> tuple[list[dict], float]:
    """
    Executa o motor de reconhecimento atual e retorna:
    (hypothesis: list[dict], duration: float)

    hypothesis: lista de dicts {start, end, root (int), quality (str), bass (int|None)}
    """
    from local_engine.audio.prepare import load_audio
    from local_engine.recognition.engine import recognize
    from local_engine.validation.pipeline import run_pipeline
    from shared.schemas.music_data import MusicData, ChordEvent

    prepared = load_audio(audio_path)

    raw_events = recognize(prepared.y, prepared.sr)

    music = MusicData(
        title    = os.path.basename(audio_path),
        duration = prepared.duration,
        chords   = [
            ChordEvent(
                start=e["start"], end=e["end"],
                root=e["root"], quality=e["quality"],
                confidence=e["confidence"],
            )
            for e in raw_events
        ],
    )
    music = run_pipeline(music)

    hypothesis = [
        {
            "start":   c.start,
            "end":     c.end,
            "root":    c.root,
            "quality": c.quality,
            "bass":    c.bass,
        }
        for c in music.chords
    ]
    return hypothesis, prepared.duration


# ---------------------------------------------------------------------------
# Avalia uma música
# ---------------------------------------------------------------------------
def evaluate_one(
    ref: ReferenceAnnotation,
    save_report: bool = True,
) -> Optional[EvaluationReport]:
    """Avalia uma música. Retorna None se o áudio não estiver disponível."""
    audio_path = os.path.join(_AUDIO_DIR, ref.audio_file) if ref.audio_file else ""

    if not ref.audio_file or not os.path.isfile(audio_path):
        print(f"  [PULADO] {ref.id}: áudio '{ref.audio_file}' não encontrado.")
        return None

    print(f"  Processando: {ref.title} ({ref.artist})...")
    t0 = time.time()
    try:
        hypothesis, _ = run_engine(audio_path)
    except Exception as e:
        print(f"  [ERRO] Motor falhou: {e}")
        return None

    elapsed = time.time() - t0
    report  = evaluate(ref, hypothesis)
    print(f"  Concluído em {elapsed:.1f}s — Root: {report.root_accuracy.pct if report.root_accuracy else 'N/A'}")

    if save_report:
        _save_report(report)

    return report


# ---------------------------------------------------------------------------
# Salva relatório JSON
# ---------------------------------------------------------------------------
def _save_report(report: EvaluationReport):
    os.makedirs(_RPT_DIR, exist_ok=True)
    path = os.path.join(_RPT_DIR, f"{report.music_id}.json")

    def _serialize(obj):
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.__dict__, f, default=_serialize,
                  ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Relatório agregado
# ---------------------------------------------------------------------------
def aggregate_reports(reports: list[EvaluationReport]) -> dict:
    """
    Calcula médias agregadas sobre a coleção.
    Separa por split (dev/test).
    Inclui aviso explícito sobre tamanho da amostra.
    """
    def _avg(reports, attr):
        vals = []
        for r in reports:
            m = getattr(r, attr, None)
            if m and m.total_seconds > 0:
                vals.append(m.score)
        if not vals:
            return None
        return sum(vals) / len(vals)

    def _summarize(subset, label):
        if not subset:
            return {label: "nenhuma música avaliada"}
        n = len(subset)
        return {
            "label": label,
            "n_songs": n,
            "statistical_warning": (
                f"Amostra pequena (n={n}). Estimativas com alta incerteza. "
                "Não generalizar para repertório não avaliado."
            ),
            "root_accuracy":    _avg(subset, "root_accuracy"),
            "majmin_accuracy":  _avg(subset, "majmin_accuracy"),
            "thirds_accuracy":  _avg(subset, "thirds_accuracy"),
            "sevenths_accuracy":_avg(subset, "sevenths_accuracy"),
            "tetrads_accuracy": _avg(subset, "tetrads_accuracy"),
            "bass_accuracy":    _avg(subset, "bass_accuracy"),
            "inversion_accuracy": _avg(subset, "inversion_accuracy"),
            "segmentation_f1":  _avg(subset, "segmentation"),
        }

    dev_set  = [r for r in reports if r.split == "dev"]
    test_set = [r for r in reports if r.split == "test"]

    return {
        "total_evaluated": len(reports),
        "dev":  _summarize(dev_set,  "dev"),
        "test": _summarize(test_set, "test"),
        "all":  _summarize(reports,  "all"),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Avalia o motor Cifra ao Vivo sobre a coleção de referência.")
    parser.add_argument("--split",  default="all",
                        choices=["dev", "test", "all"],
                        help="Conjunto a avaliar (padrão: all)")
    parser.add_argument("--id",     default=None,
                        help="Avaliar apenas esta música (ex: gospel_001)")
    parser.add_argument("--no-save", action="store_true",
                        help="Não salvar relatórios individuais")
    args = parser.parse_args()

    split = None if args.split == "all" else args.split
    collection = load_collection(split)

    if args.id:
        collection = [r for r in collection if r.id == args.id]

    if not collection:
        print("Nenhuma anotação encontrada. "
              "Adicione arquivos em evaluation/reference/annotations/")
        sys.exit(0)

    print(f"\nAvaliando {len(collection)} música(s)...\n")

    reports = []
    for ref in collection:
        report = evaluate_one(ref, save_report=not args.no_save)
        if report:
            reports.append(report)

    if not reports:
        print("\nNenhuma música pôde ser avaliada (áudios ausentes).")
        sys.exit(0)

    # Sumário
    print("\n" + "=" * 60)
    print("SUMÁRIO INDIVIDUAL")
    print("=" * 60)
    for r in reports:
        print(r.summary())
        print()

    # Agregado
    agg = aggregate_reports(reports)
    print("=" * 60)
    print("MÉDIAS AGREGADAS")
    print("=" * 60)
    for split_key in ("dev", "test", "all"):
        s = agg.get(split_key, {})
        if isinstance(s, str) or s.get("n_songs", 0) == 0:
            continue
        print(f"\n[{split_key.upper()}]  n={s['n_songs']}")
        print(f"  AVISO: {s['statistical_warning']}")
        for metric in ("root_accuracy", "majmin_accuracy", "thirds_accuracy",
                       "sevenths_accuracy", "tetrads_accuracy",
                       "bass_accuracy", "segmentation_f1"):
            val = s.get(metric)
            label = metric.replace("_", " ").title()
            print(f"  {label:<25}: {val:.1%}" if val is not None
                  else f"  {label:<25}: N/A")

    # Salva agregado
    os.makedirs(_RPT_DIR, exist_ok=True)
    agg_path = os.path.join(_RPT_DIR, "aggregate.json")
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)
    print(f"\nRelatório agregado salvo em: {agg_path}")


if __name__ == "__main__":
    main()
