"""
Junta trechos seguidos do mesmo acorde que o reconhecimento separou só por
oscilar entre versões parecidas (D / D7, Bm / Bm7, Em / Em7, Esus2 / E).
"""

from __future__ import annotations
from dataclasses import replace
from shared.schemas.music_data import ChordEvent

_FAMILY = {
    "maj": "maior", "7": "maior", "maj7": "maior", "sus2": "maior", "sus4": "maior",
    "min": "menor", "min7": "menor",
    "dim": "dim",
}


def _family(c: ChordEvent) -> tuple:
    return (c.root % 12, _FAMILY.get(c.quality, c.quality), c.bass)


def merge_chord_family(chords: list[ChordEvent]) -> list[ChordEvent]:
    """
    Une acordes consecutivos com a mesma fundamental e a mesma família
    (maior ou menor). O nome final é a versão que soou por mais tempo no
    trecho (empate: a tríade simples). Confiança = média ponderada pela duração.
    """
    out: list[ChordEvent] = []
    group: list[ChordEvent] = []

    def flush():
        if not group:
            return
        if len(group) == 1:
            out.append(group[0]); return
        time_by_q: dict[str, float] = {}
        for c in group:
            time_by_q[c.quality] = time_by_q.get(c.quality, 0.0) + c.duration
        simple = {"maior": "maj", "menor": "min"}.get(_FAMILY.get(group[0].quality, ""), "")
        best_q = max(time_by_q, key=lambda q: (time_by_q[q], q == simple))
        total = sum(c.duration for c in group) or 1.0
        conf = sum(c.confidence * c.duration for c in group) / total
        main = max((c for c in group if c.quality == best_q), key=lambda c: c.duration)
        out.append(replace(main, start=group[0].start, end=group[-1].end,
                           quality=best_q, confidence=conf,
                           uncertain=all(c.uncertain for c in group)))

    for c in sorted(chords, key=lambda c: c.start):
        if group and _family(c) == _family(group[-1]):
            group.append(c)
        else:
            flush(); group = [c]
    flush()
    return out
