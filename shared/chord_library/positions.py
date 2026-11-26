"""
Posições básicas de acordes para violão/guitarra.
Formato: {nome: {"frets": [e,A,D,G,B,e], "fingers": [...], "barre": optional_fret}}
-1 = corda abafada (X), 0 = corda solta.
"""

CHORD_POSITIONS: dict[str, dict] = {
    # --- Maiores ---
    "C":  {"frets": [-1, 3, 2, 0, 1, 0], "fingers": [0, 3, 2, 0, 1, 0]},
    "D":  {"frets": [-1,-1, 0, 2, 3, 2], "fingers": [0, 0, 0, 1, 3, 2]},
    "E":  {"frets": [ 0, 2, 2, 1, 0, 0], "fingers": [0, 2, 3, 1, 0, 0]},
    "F":  {"frets": [ 1, 1, 2, 3, 3, 1], "fingers": [1, 1, 2, 4, 3, 1], "barre": 1},
    "G":  {"frets": [ 3, 2, 0, 0, 0, 3], "fingers": [2, 1, 0, 0, 0, 3]},
    "A":  {"frets": [-1, 0, 2, 2, 2, 0], "fingers": [0, 0, 1, 2, 3, 0]},
    "Bb": {"frets": [-1, 1, 3, 3, 3, 1], "fingers": [0, 1, 2, 3, 4, 1], "barre": 1},
    "B":  {"frets": [-1, 2, 4, 4, 4, 2], "fingers": [0, 1, 2, 3, 4, 1], "barre": 2},

    # --- Menores ---
    "Cm": {"frets": [-1, 3, 5, 5, 4, 3], "fingers": [0, 1, 3, 4, 2, 1], "barre": 3},
    "Dm": {"frets": [-1,-1, 0, 2, 3, 1], "fingers": [0, 0, 0, 2, 3, 1]},
    "Em": {"frets": [ 0, 2, 2, 0, 0, 0], "fingers": [0, 2, 3, 0, 0, 0]},
    "Fm": {"frets": [ 1, 1, 3, 3, 2, 1], "fingers": [1, 1, 3, 4, 2, 1], "barre": 1},
    "Gm": {"frets": [ 3, 5, 5, 3, 3, 3], "fingers": [1, 3, 4, 1, 1, 1], "barre": 3},
    "Am": {"frets": [-1, 0, 2, 2, 1, 0], "fingers": [0, 0, 2, 3, 1, 0]},
    "Bm": {"frets": [-1, 2, 4, 4, 3, 2], "fingers": [0, 1, 3, 4, 2, 1], "barre": 2},

    # --- Sétimas dominantes ---
    "C7":  {"frets": [-1, 3, 2, 3, 1, 0], "fingers": [0, 3, 2, 4, 1, 0]},
    "D7":  {"frets": [-1,-1, 0, 2, 1, 2], "fingers": [0, 0, 0, 2, 1, 3]},
    "E7":  {"frets": [ 0, 2, 0, 1, 0, 0], "fingers": [0, 2, 0, 1, 0, 0]},
    "F7":  {"frets": [ 1, 1, 2, 1, 1, 1], "fingers": [1, 1, 3, 2, 1, 1], "barre": 1},
    "G7":  {"frets": [ 3, 2, 0, 0, 0, 1], "fingers": [3, 2, 0, 0, 0, 1]},
    "A7":  {"frets": [-1, 0, 2, 0, 2, 0], "fingers": [0, 0, 2, 0, 3, 0]},
    "B7":  {"frets": [-1, 2, 1, 2, 0, 2], "fingers": [0, 2, 1, 3, 0, 4]},

    # --- Maior com sétima maior ---
    "Cmaj7": {"frets": [-1, 3, 2, 0, 0, 0], "fingers": [0, 3, 2, 0, 0, 0]},
    "Dmaj7": {"frets": [-1,-1, 0, 2, 2, 2], "fingers": [0, 0, 0, 1, 1, 1]},
    "Emaj7": {"frets": [ 0, 2, 1, 1, 0, 0], "fingers": [0, 3, 1, 2, 0, 0]},
    "Fmaj7": {"frets": [ 0, 0, 3, 2, 1, 0], "fingers": [0, 0, 4, 3, 1, 0]},
    "Gmaj7": {"frets": [ 3, 2, 0, 0, 0, 2], "fingers": [3, 2, 0, 0, 0, 1]},
    "Amaj7": {"frets": [-1, 0, 2, 1, 2, 0], "fingers": [0, 0, 3, 1, 4, 0]},

    # --- Suspensos ---
    "Csus4": {"frets": [-1, 3, 3, 0, 1, 1], "fingers": [0, 3, 4, 0, 1, 2]},
    "Dsus4": {"frets": [-1,-1, 0, 2, 3, 3], "fingers": [0, 0, 0, 1, 2, 3]},
    "Esus4": {"frets": [ 0, 2, 2, 2, 0, 0], "fingers": [0, 1, 2, 3, 0, 0]},
    "Gsus4": {"frets": [ 3, 3, 0, 0, 1, 3], "fingers": [2, 3, 0, 0, 1, 4]},
    "Asus4": {"frets": [-1, 0, 2, 2, 3, 0], "fingers": [0, 0, 1, 2, 3, 0]},
}


def get_positions(chord_name: str) -> dict | None:
    """Retorna a posição do acorde ou None se não mapeado."""
    return CHORD_POSITIONS.get(chord_name)


def list_available() -> list[str]:
    """Lista todos os acordes com posição definida."""
    return sorted(CHORD_POSITIONS.keys())
