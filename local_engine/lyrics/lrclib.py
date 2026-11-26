"""
Integração com LRCLIB para busca de letras sincronizadas.
Porta Python do lyrics.js da extensão v1.4.
"""

from __future__ import annotations
import re
from typing import Optional
import httpx

from shared.schemas.music_data import LyricLine

LRCLIB_BASE = "https://lrclib.net/api"
TIMEOUT     = 10.0


def parse_lrc(text: str) -> list[LyricLine]:
    """
    Converte texto LRC (sincronizado) em lista de LyricLine.
    Formato: [01:23.45] texto
    """
    out: list[LyricLine] = []
    for raw in text.splitlines():
        stamps = re.findall(r'\[(\d{1,3}):(\d{2}(?:[.:]?\d{1,3})?)\]', raw)
        if not stamps:
            continue
        txt = re.sub(r'\[[^\]]*\]', '', raw).strip()
        if not txt:
            continue
        for m, s in stamps:
            t = int(m) * 60 + float(s.replace(":", "."))
            out.append(LyricLine(t=t, text=txt))
    out.sort(key=lambda x: x.t)
    return out


def lrc_to_words(lines: list[LyricLine]) -> list[LyricLine]:
    """
    Estima o tempo de cada palavra dentro de cada linha
    (proporcionalmente ao comprimento de cada palavra).
    Modifica words[] em cada LyricLine.
    """
    for i, ln in enumerate(lines):
        words_txt = ln.text.split()
        if not words_txt:
            continue
        next_t = lines[i + 1].t if i + 1 < len(lines) else ln.t + 5.0
        total_chars = sum(len(w) for w in words_txt) + len(words_txt) - 1
        end = min(next_t - 0.1, ln.t + total_chars * 0.14 + 0.6)
        dur = max(0.3, end - ln.t)

        acc = 0
        word_list = []
        for k, w in enumerate(words_txt):
            s = ln.t + (dur * acc) / max(total_chars, 1)
            acc += len(w)
            e = ln.t + (dur * acc) / max(total_chars, 1)
            acc += 1
            word_list.append({
                "w":  w,
                "s":  s,
                "e":  max(e, s + 0.05),
                "nl": k == 0,
            })
        ln.words = word_list
    return lines


# Diferença máxima aceita entre a duração do áudio e a da versão da letra
MAX_DURATION_DIFF = 10.0


def _norm(txt: str) -> str:
    """Minúsculas, sem acentos e sem pontuação — para comparar nomes."""
    import unicodedata
    t = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z0-9 ]+", " ", t.lower().replace("&", " e "))
    return re.sub(r"\s+", " ", t).strip()


def clean_title(title: str) -> str:
    """Tira do título o que atrapalha a busca: (Ao Vivo), [Clipe Oficial],
    hashtags, 'feat. X' e o que vier depois de ' - ' ou ' | '."""
    t = re.sub(r"[\(\[][^\)\]]*[\)\]]", " ", title or "")
    t = re.split(r"\s+[-–—|]\s+|\s*\|\s*", t)[0]
    t = re.sub(r"#\S+", " ", t)
    t = re.sub(r"\b(feat|ft)\.?\s.*$", " ", t, flags=re.I)
    t = re.sub(r"\b(ao vivo|clipe oficial|official( music)? video|lyric video|videoclipe)\b",
               " ", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()


def _artist_variants(artist: str) -> list[str]:
    a = (artist or "").strip()
    out = [a]
    if " e " in a:  out.append(a.replace(" e ", " & "))
    if " & " in a:  out.append(a.replace(" & ", " e "))
    return [x for i, x in enumerate(out) if x and x not in out[:i]]


def _same_artist(found: str, wanted: str) -> bool:
    """Confere o artista do resultado (tolerante a '&'/'e', acentos e 'feat.')."""
    if not wanted:
        return True
    f, w = _norm(found), _norm(wanted)
    return bool(f) and (w in f or f in w or w.split(" ")[0] == f.split(" ")[0])


def _pick_closest(items: list[dict], duration: Optional[float]) -> Optional[dict]:
    """Entre os resultados com letra sincronizada, escolhe o de duração mais
    próxima do áudio. Sem duração conhecida, mantém a ordem do LRCLIB."""
    synced = [it for it in items if it.get("syncedLyrics")]
    if not synced:
        return None
    if not duration:
        return synced[0]
    return min(synced, key=lambda it: abs(float(it.get("duration") or 0) - duration))


async def fetch_lrclib(title: str, artist: str,
                       duration: Optional[float] = None,
                       errors: Optional[list] = None) -> Optional[list[LyricLine]]:
    """
    Busca letra sincronizada no LRCLIB, tentando do mais exato ao mais amplo:
      1. /get com título e artista (e a duração do áudio, se houver)
      2. o mesmo com o título limpo e o artista com '&' ou 'e'
      3. /search por título + artista
      4. /search só pelo título, aceitando resultados do mesmo artista
    Entre as versões encontradas, escolhe a de duração mais próxima do áudio.
    """
    titles = [t for i, t in enumerate([title.strip(), clean_title(title)])
              if t and t not in [title.strip(), clean_title(title)][:i]]
    artists = _artist_variants(artist) or [""]
    found: list[dict] = []

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async def get_json(path, params):
            try:
                r = await client.get(f"{LRCLIB_BASE}/{path}", params=params)
                return r.json() if r.status_code == 200 else None
            except Exception as exc:
                if errors is not None:
                    errors.append(f"{type(exc).__name__}: {exc}")
                return None

        # 1–2. Busca exata
        for t in titles:
            for a in artists:
                if not a:
                    continue
                if duration:
                    d = await get_json("get", {"track_name": t, "artist_name": a,
                                               "duration": int(round(duration))})
                    if d and d.get("syncedLyrics"):
                        return lrc_to_words(parse_lrc(d["syncedLyrics"]))
                d = await get_json("get", {"track_name": t, "artist_name": a})
                if d and d.get("syncedLyrics"):
                    found.append(d)

        # 3. Busca por título + artista
        if not found:
            for t in titles:
                arr = await get_json("search", {"q": f"{artist} {t}".strip()}) or []
                found += [it for it in arr if _same_artist(it.get("artistName", ""), artist)]
                if any(it.get("syncedLyrics") for it in found):
                    break

        # 4. Busca só pelo título
        if not any(it.get("syncedLyrics") for it in found):
            for t in titles:
                arr = await get_json("search", {"track_name": t}) or []
                found += [it for it in arr if _same_artist(it.get("artistName", ""), artist)]
                if any(it.get("syncedLyrics") for it in found):
                    break

    best = _pick_closest(found, duration)
    if best is not None:
        return lrc_to_words(parse_lrc(best["syncedLyrics"]))
    # letra sem sincronia como último recurso
    for item in found:
        plain = item.get("plainLyrics", "")
        if plain:
            lines = [LyricLine(t=float(i * 5), text=ln)
                     for i, ln in enumerate(plain.splitlines()) if ln.strip()]
            return lrc_to_words(lines)
    return None


def parse_title_artist(page_title: str) -> tuple[str, str]:
    """
    Tenta extrair artista e título de uma string como
    'Artista - Música | YouTube'.
    """
    # Remove sufixos de plataforma
    clean = re.sub(
        r'\s*[-|]\s*(YouTube Music|YouTube|Spotify|Deezer|SoundCloud)\s*$',
        '', page_title, flags=re.I
    )
    # Remove tags de qualidade
    clean = re.sub(
        r'[\(\[][^\)\]]*(official|video|lyrics?|letra|audio|hd|4k|ao vivo|live|ft\.?|feat\.?)'
        r'[^\)\]]*[\)\]]', '', clean, flags=re.I
    )
    clean = re.sub(r'\s+', ' ', clean).strip()

    parts = re.split(r'\s+[-–—]\s+', clean, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return "", clean
