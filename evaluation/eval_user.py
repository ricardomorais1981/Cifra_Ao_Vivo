"""
Comparação QUALITATIVA do motor com a cifra (sem tempos) de uma música do usuário.

ATENÇÃO: o resultado NÃO é a medida oficial de confiabilidade (que exige
anotação com tempos, evaluation/evaluator.py + metrics.py). Aqui comparamos:
  1. tom detectado × tom da cifra (levando em conta o capo);
  2. conjunto de acordes (fundamental + maior/menor) reconhecidos × cifra;
  3. sequência do motor, sem repetições, alinhada à sequência da cifra por
     distância de edição -> % de acordes da cifra que batem.

Uso:
  python3 -m evaluation.eval_user AUDIO.wav evaluation/reference/cifras_user/X.json [--capo N]

O áudio deve ser WAV 22050 Hz mono (converter antes com ffmpeg). Usa a versão
de AVALIAÇÃO numpy/scipy do chroma/baixo (evaluation/np_features.py).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_PC = {n: i for i, n in enumerate(NOTES)}
_PC.update({"Db": 1, "Eb": 3, "Gb": 6, "Ab": 8, "Bb": 10})
_MINOR_Q = {"min", "min7", "dim"}


def parse_symbol(sym: str) -> tuple[int, str]:
    """'Am7' -> (9, 'min'); 'F9/C' -> (5, 'maj'); 'G11' -> (7, 'maj')."""
    m = re.match(r"^([A-G][#b]?)(.*)$", sym.strip())
    if not m:
        raise ValueError(sym)
    root = _PC[m.group(1)]
    rest = m.group(2).split("/")[0]
    is_min = rest.startswith("m") and not rest.startswith("maj")
    return root, ("min" if is_min else "maj")


def label(root: int, mm: str) -> str:
    return NOTES[root % 12] + ("m" if mm == "min" else "")


def ref_sequence(ref: dict, capo: int) -> list[str]:
    seq = []
    for sec in ref["secoes"]:
        for s in sec["acordes"]:
            r, q = parse_symbol(s)
            lab = label(r + capo, q)
            if not seq or seq[-1] != lab:
                seq.append(lab)
    return seq


def align(ref: list[str], hyp: list[str]):
    """Levenshtein com backtrack. Retorna (n_iguais, operações)."""
    n, m = len(ref), len(hyp)
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        D[i][0] = i
    for j in range(m + 1):
        D[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = 0 if ref[i - 1] == hyp[j - 1] else 1
            D[i][j] = min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + c)
    i, j, ops, ok = n, m, [], 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and D[i][j] == D[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            same = ref[i - 1] == hyp[j - 1]
            ok += same
            ops.append(("=" if same else "~", ref[i - 1], hyp[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and D[i][j] == D[i - 1][j] + 1:
            ops.append(("-", ref[i - 1], None)); i -= 1
        else:
            ops.append(("+", None, hyp[j - 1])); j -= 1
    return ok, ops[::-1]


def run(audio: str, ref_path: str, capo: int | None = None) -> dict:
    from evaluation import eval_np, evaluator
    from local_engine.audio import prepare
    from local_engine.validation import pipeline

    ref = json.load(open(ref_path, encoding="utf-8"))
    if capo is None:
        capo = ref.get("capo") or 0
    eval_np.install_patches()
    hyp, dur = evaluator.run_engine(audio)

    # tom: mesmo cálculo do pipeline, sobre os acordes finais
    from shared.schemas.music_data import ChordEvent
    evs = [ChordEvent(start=h["start"], end=h["end"], root=h["root"],
                      quality=h["quality"], confidence=1.0) for h in hyp]
    k, mode = pipeline.estimate_key(evs)
    key_det = label(k, "min" if mode == "minor" else "maj")
    kr, kq = parse_symbol(ref["tom_cifra"])
    key_ref = label(kr + capo, kq)

    # tempo por acorde (maior/menor) e sequência sem repetições
    tempo = Counter()
    seq = []
    for h in hyp:
        lab = label(h["root"], "min" if h["quality"] in _MINOR_Q else "maj")
        tempo[lab] += h["end"] - h["start"]
        if not seq or seq[-1] != lab:
            seq.append(lab)
    rseq = ref_sequence(ref, capo)
    ok, ops = align(rseq, seq)
    rset, hset = set(rseq), set(seq)
    total = sum(tempo.values()) or 1.0
    tempo_fora = sum(v for c, v in tempo.items() if c not in rset) / total
    return dict(duracao=dur, tom_detectado=key_det, tom_cifra_soando=key_ref,
                capo=capo, faltam=sorted(rset - hset), sobram=sorted(hset - rset),
                tempo_por_acorde={c: round(v, 1) for c, v in tempo.most_common()},
                pct_tempo_fora_da_cifra=tempo_fora,
                seq_motor=len(seq), seq_cifra=len(rseq),
                pct_seq_batem=ok / len(rseq),
                pct_motor_batem=ok / max(len(seq), 1), ops=ops)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("ref")
    ap.add_argument("--capo", type=int, default=None)
    ap.add_argument("--ops", action="store_true", help="mostra o alinhamento")
    a = ap.parse_args()
    r = run(a.audio, a.ref, a.capo)
    print(f"Tom detectado: {r['tom_detectado']}  | cifra (soando, capo {r['capo']}): "
          f"{r['tom_cifra_soando']}  -> {'OK' if r['tom_detectado'] == r['tom_cifra_soando'] else 'DIFERENTE'}")
    print(f"Acordes que faltam: {r['faltam']}  | sobram: {r['sobram']}")
    print(f"Tempo em acordes fora da cifra: {r['pct_tempo_fora_da_cifra']:.1%}")
    print(f"Tempo por acorde (s): {r['tempo_por_acorde']}")
    print(f"Sequência: motor {r['seq_motor']} trocas, cifra {r['seq_cifra']}; "
          f"da cifra batem {r['pct_seq_batem']:.1%}, do motor batem "
          f"{r['pct_motor_batem']:.1%} (NÃO é a medida oficial)")
    if a.ops:
        for op in r["ops"]:
            print(*[x or "·" for x in op])


if __name__ == "__main__":
    main()
