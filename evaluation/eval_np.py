"""
Avaliação no ambiente do agente diário (sem librosa/soundfile).

Uso:  python3 -m evaluation.eval_np

Roda o motor de produção (engine.recognize + validation.pipeline) e o
avaliador/métricas oficiais (evaluation.evaluator.run_engine + metrics),
trocando APENAS a leitura do WAV (scipy) e o cálculo de chroma/baixo
(evaluation.np_features, versão numpy/scipy da CQT). Áudios: cópias 22 kHz
em evaluation/reference/audio_22k/.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy.io import wavfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from evaluation import evaluator
from evaluation.metrics import evaluate
from evaluation.schemas.annotation import ReferenceAnnotation
from evaluation.np_features import chroma_and_bass
from local_engine.audio import prepare
from local_engine.recognition import engine

AUDIO_22K = os.path.join(_ROOT, "evaluation", "reference", "audio_22k")
IDS = ["gospel_br_001", "gospel_us_001"]


def _load_audio_scipy(path: str, target_sr: int = prepare.TARGET_SR):
    sr, y = wavfile.read(path)
    y = y.astype(np.float32)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != target_sr:
        raise ValueError(f"esperado {target_sr} Hz, veio {sr}")
    peak = np.abs(y).max()
    if peak > 1e-6:
        y = y / peak
    info = prepare.AudioInfo(path=path, size_mb=os.path.getsize(path) / 1e6,
                             extension=".wav")
    return prepare.PreparedAudio(y=y, sr=sr, duration=len(y) / sr, info=info)


def install_patches():
    prepare.load_audio = _load_audio_scipy
    engine._chroma_cqt = lambda y, sr, hop=2048: chroma_and_bass(y, sr, hop)


def main():
    install_patches()
    scores = []
    for mid in IDS:
        ref = ReferenceAnnotation.load(os.path.join(
            evaluator._ANN_DIR, f"{mid}.json"))
        # gospel_br_001 grava alguns menores como root "Em"/"Am"/"Bm" com
        # quality "min" (o schema espera só a nota). Corrige SÓ na memória,
        # sem alterar o arquivo de anotação.
        for e in ref.events:
            if len(e.root) >= 2 and e.root.endswith("m") and e.quality == "min":
                e.root = e.root[:-1]
        hyp, _ = evaluator.run_engine(os.path.join(AUDIO_22K, f"{mid}.wav"))
        rep = evaluate(ref, hyp)
        mm, rt = rep.majmin_accuracy.score, rep.root_accuracy.score
        scores.append(mm)
        print(f"{mid}: MajMin {mm:.1%}  Root {rt:.1%}  "
              f"(cobertura {rep.evaluation_coverage:.0%}, "
              f"{len(hyp)} acordes)")
    print(f"MÉDIA MajMin: {np.mean(scores):.1%}")


if __name__ == "__main__":
    main()
