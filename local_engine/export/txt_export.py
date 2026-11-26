"""
Exportação do resultado para formato TXT clássico (cifra sobre letra).
"""

from __future__ import annotations
import os
import re
from typing import Optional
import textwrap
from shared.schemas.music_data import MusicData, PipelineStatus, ChordEvent, LyricLine

# Largura máxima de coluna
LINE_WIDTH = 80
# Espaço mínimo entre acordes consecutivos
MIN_CHORD_GAP = 2


def _status_label(status: PipelineStatus) -> str:
    return {
        PipelineStatus.APPROVED:            "APROVADO",
        PipelineStatus.APPROVED_AFTER_FIX:  "APROVADO APOS CORRECAO",
        PipelineStatus.QUALITY_UNCONFIRMED: "QUALIDADE NAO CONFIRMADA",
    }.get(status, status.value.upper())


_SHARP = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
_FLAT  = ["C","Db","D","Eb","E","F","Gb","G","Ab","A","Bb","B"]


def _shift_key(key: str, n: int, flats: bool = False) -> str:
    """Transpõe um tom no formato 'B' ou 'G# minor' por n semitons."""
    m = re.match(r'^([A-G][#b]?)(.*)$', key.strip())
    if not m or n % 12 == 0 and not flats:
        return key
    root = m.group(1)
    idx = (_SHARP.index(root) if root in _SHARP else _FLAT.index(root))
    names = _FLAT if flats else _SHARP
    return names[(idx + n) % 12] + m.group(2)


def _build_header(music: MusicData, capo: int = 0, transpose: int = 0,
                  flats: bool = False) -> str:
    lines = []
    sep = "=" * LINE_WIDTH
    lines.append(sep)
    lines.append(f"  MUSICA : {music.title}")
    if music.artist:
        lines.append(f"  ARTISTA: {music.artist}")
    if music.key:
        lines.append(f"  TOM    : {_shift_key(music.key, transpose, flats)}")
    if music.tempo:
        lines.append(f"  TEMPO  : {music.tempo:.0f} BPM")
    ms = getattr(music, "music_start", 0.0) or 0.0
    if ms >= 0.5:
        lines.append(f"  INICIO : musica comeca em {ms:.1f}s da gravacao "
                     "(trecho anterior ignorado)")
    if capo:
        forma = (f" (formas de {_shift_key(music.key, transpose - capo, flats)})"
                 if music.key else "")
        lines.append(f"  CAPO   : {capo}a casa{forma}")
    lines.append(sep)
    return "\n".join(lines)


def _build_quality_report(music: MusicData) -> str:
    lines = []
    sep = "-" * LINE_WIDTH
    lines.append(sep)
    lines.append("RELATORIO DE QUALIDADE")
    lines.append(sep)

    status = _status_label(music.pipeline_status)
    lines.append(f"STATUS: {status}")

    if music.validation_1:
        v = music.validation_1
        lines.append(f"\nAnalise inicial:")
        lines.append(f"  Cobertura       : {v.coverage:.0%}")
        lines.append(f"  Confianca       : {v.confidence:.0%}")
        lines.append(f"  Coerencia harm. : {v.harmonic_coherence:.0%}")
        lines.append(f"  Score           : {v.score:.2f}")
        if v.notes:
            for n in v.notes:
                lines.append(f"  ! {n}")

    if music.corrections:
        lines.append(f"\nCorrecao teorica:")
        lines.append(f"  {len(music.corrections)} acorde(s) corrigido(s).")
        for c in music.corrections[:5]:
            lines.append(f"  t={c.t:.1f}s  {c.original} -> {c.corrected}  ({c.reason})")
        if len(music.corrections) > 5:
            lines.append(f"  ... e mais {len(music.corrections)-5} correcao(oes).")

    if music.validation_2:
        v = music.validation_2
        lines.append(f"\nSegunda validacao:")
        lines.append(f"  Score: {v.score:.2f}  {'OK' if v.passed else 'ATENCAO'}")
        for n in v.notes:
            lines.append(f"  ! {n}")

    if music.modulation_at is not None:
        lines.append(f"\nModulacao detectada a partir de {music.modulation_at:.0f}s.")

    if music.pipeline_status == PipelineStatus.QUALITY_UNCONFIRMED:
        lines.append("")
        lines.append("OBSERVACAO: alguns acordes nao foram confirmados com")
        lines.append("seguranca. Recomenda-se revisao manual.")

    lines.append(sep)
    return "\n".join(lines)


def _simplify_chord(name: str) -> str:
    """
    Simplifica o nome do acorde para a forma básica (maior ou menor).
    Exemplos: Cmaj7 → C, Dm7 → Dm, G7 → G, Gsus4 → G, Bdim → Bm
    """
    if not name:
        return name
    # Separa a nota base (ex: C, C#, Db)
    import re
    m = re.match(r'^([A-G][b#]?)(.*)', name)
    if not m:
        return name
    root, quality = m.group(1), m.group(2).strip("(?)").lower()
    if quality.startswith("m") and not quality.startswith("maj"):
        return root + "m"   # menor
    return root              # maior (descarta maj7, 7, sus2, sus4, add9 etc.)


def _chord_at(chords: list[ChordEvent], t: float,
              transpose: int = 0, flats: bool = False,
              simplify: bool = False) -> str:
    """Retorna o nome do acorde ativo no instante t."""
    for c in reversed(chords):
        if c.start <= t:
            name = c.chord_name(transpose, flats)
            return _simplify_chord(name) if simplify else name
    return ""


# Trechos sem letra
INTRO_MIN_S      = 2.0   # [Intro] só aparece se a letra começa depois disto
GAP_S            = 5.0   # intervalo sem letra que vira [Instrumental]
MIN_LIST_CHORD_S = 0.6   # acordes mais curtos são omitidos em [Intro]/[Instrumental]


def _name(c: ChordEvent, transpose: int, flats: bool, simplify: bool) -> str:
    n = c.chord_name(transpose, flats)
    return _simplify_chord(n) if simplify else n


def _sequence(chords: list[ChordEvent], t0: float, t1: float,
              transpose: int, flats: bool, simplify: bool) -> list[str]:
    """Acordes tocados entre t0 e t1, sem repetir o mesmo acorde em seguida."""
    seq: list[str] = []
    for c in chords:
        ov = min(c.end, t1) - max(c.start, t0)
        if ov <= 0 or ov < min(MIN_LIST_CHORD_S, t1 - t0):
            continue
        n = _name(c, transpose, flats, simplify)
        if not seq or seq[-1] != n:
            seq.append(n)
    return seq


def _build_sheet(music: MusicData, transpose: int = 0, flats: bool = False,
                 simplify: bool = False, lyrics_offset: float = 0.0) -> str:
    """
    Constrói a cifra: acordes na linha de cima, letra na de baixo.

    - Um acorde só é escrito quando MUDA (não se repete enquanto continua
      soando, nem de uma linha para a outra).
    - O acorde vai sobre a palavra em que a mudança acontece; se a mudança
      cai depois da última palavra, ele fica à direita do fim da linha.
    - Trechos sem letra ganham linha própria: [Intro], [Instrumental], [Final].

    lyrics_offset: segundos somados aos tempos da letra. Positivo = a letra é
    cantada mais tarde no áudio do que diz o LRC.
    """
    chords = sorted(music.chords, key=lambda c: c.start)

    if not music.lyrics:
        lines = ["ACORDES (sem letra sincronizada):", ""]
        last = None
        for c in chords:
            name = _name(c, transpose, flats, simplify)
            if name == last:
                continue
            unc = "?" if c.uncertain else ""
            lines.append(f"  {c.start:6.1f}s  {name}{unc}")
            last = name
        return "\n".join(lines)

    off = float(lyrics_offset or 0.0)
    lyr = [ln for ln in music.lyrics if (ln.text or "").strip()]
    end_t = max([c.end for c in chords] + [music.duration or 0.0])
    out: list[str] = []
    last: Optional[str] = None

    def emit_section(label: str, t0: float, t1: float):
        nonlocal last
        seq = _sequence(chords, t0, t1, transpose, flats, simplify)
        if seq and seq[0] == last:      # acorde que já vinha soando
            seq = seq[1:]
        if seq:
            out.append(f"[{label}] " + "  ".join(seq))
            out.append("")
            last = seq[-1]

    def line_bounds(ln):
        words = ln.words or [{"w": w, "s": ln.t, "e": ln.t} for w in ln.text.split()]
        return words, words[0]["s"] + off, words[-1]["e"] + off

    # Introdução
    if lyr:
        _, first_s, _ = line_bounds(lyr[0])
        if first_s > INTRO_MIN_S:
            emit_section("Intro", 0.0, first_s)

    for i, ln in enumerate(lyr):
        words, ls, le_words = line_bounds(ln)
        next_s = line_bounds(lyr[i + 1])[1] if i + 1 < len(lyr) else end_t
        gap = next_s - le_words
        win_end = le_words + 0.5 if gap > GAP_S else next_s

        # Colunas das palavras
        text = " ".join(w["w"] for w in words)
        cols, col = [], 0
        for w in words:
            cols.append((w["s"] + off, w["e"] + off, col))
            col += len(w["w"]) + 1

        # Mudanças de acorde dentro da janela da linha
        events: list[tuple[float, str]] = []
        for c in chords:
            if c.end <= ls or c.start >= win_end:
                continue
            events.append((max(c.start, ls), _name(c, transpose, flats, simplify)))

        buf: list[str] = []
        next_free = 0
        after_text = len(text) + 2
        for t, name in events:
            if name == last:
                continue
            if t <= le_words + 0.3:
                # palavra em que a mudança acontece
                wcol = cols[0][2]
                for ws, _we, wc in cols:
                    if ws <= t + 0.15:
                        wcol = wc
            else:
                wcol = after_text
            wcol = max(wcol, next_free)
            if len(buf) < wcol + len(name):
                buf.extend(" " * (wcol + len(name) - len(buf)))
            buf[wcol:wcol + len(name)] = list(name)
            next_free = wcol + len(name) + MIN_CHORD_GAP
            if wcol >= after_text:
                after_text = next_free
            last = name

        chord_str = "".join(buf).rstrip()
        if chord_str:
            out.append(chord_str)
        out.append(text)
        out.append("")

        # Trecho instrumental depois desta linha (ou final da música)
        if gap > GAP_S:
            label = "Instrumental" if i + 1 < len(lyr) else "Final"
            emit_section(label, win_end, next_s)

    return "\n".join(out).rstrip() + "\n"


def export_txt(music: MusicData, transpose: int = 0, flats: bool = False,
               simplify: bool = False, capo: int | None = None,
               lyrics_offset: float = 0.0) -> str:
    """
    lyrics_offset: ajuste da letra em segundos (ver _build_sheet).
    capo: casa do capotraste (0 = sem capo). Os acordes saem nas FORMAS que
    se tocam com o capo (som real − capo); o TOM continua sendo o som real.
    Se não for informado, usa music.capo.
    """
    capo = music.capo if capo is None else capo
    capo = max(0, min(11, int(capo or 0)))
    parts = [
        _build_header(music, capo, transpose, flats),
        "",
        _build_quality_report(music),
        "",
        _build_sheet(music, transpose - capo, flats, simplify, float(lyrics_offset or 0)),
    ]
    return "\n".join(parts)


def save_txt(music: MusicData, output_path: str,
             transpose: int = 0, flats: bool = False,
             simplify: bool = False, capo: int | None = None,
             lyrics_offset: float = 0.0) -> str:
    content = export_txt(music, transpose, flats, simplify, capo, lyrics_offset)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path
