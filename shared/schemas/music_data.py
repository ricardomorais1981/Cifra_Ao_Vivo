"""
Modelos de dados compartilhados por todo o sistema Cifra ao Vivo v2.0.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Constantes de notas
# ---------------------------------------------------------------------------
NOTE_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_NAMES_FLAT  = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def note_name(pitch: int, flats: bool = False) -> str:
    """Converte número MIDI (0=C) em nome de nota."""
    names = NOTE_NAMES_FLAT if flats else NOTE_NAMES_SHARP
    return names[pitch % 12]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class PipelineStatus(str, Enum):
    PENDING               = "pending"
    PROCESSING            = "processing"
    APPROVED              = "aprovado"
    APPROVED_AFTER_FIX    = "aprovado_apos_correcao"
    QUALITY_UNCONFIRMED   = "qualidade_nao_confirmada"
    ERROR                 = "erro"


class TaskStatus(str, Enum):
    QUEUED     = "queued"
    PROCESSING = "processing"
    DONE       = "done"
    ERROR      = "error"


# ---------------------------------------------------------------------------
# Sub-estruturas
# ---------------------------------------------------------------------------
@dataclass
class ValidationResult:
    passed: bool
    score: float                      # 0.0 – 1.0
    coverage: float = 0.0
    confidence: float = 0.0
    oscillation: float = 0.0
    harmonic_coherence: float = 0.0
    agreement: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class CorrectionEntry:
    t: float
    original: str
    corrected: str
    reason: str
    certainty: float = 0.8            # 0–1


@dataclass
class LyricLine:
    t: float                          # início (s)
    text: str
    words: list[dict] = field(default_factory=list)
    # words: [{"w": str, "s": float, "e": float, "nl": bool}]


@dataclass
class Section:
    label: str                        # "Verso 1", "Refrão", …
    start: float
    end: float


# ---------------------------------------------------------------------------
# Evento de acorde
# ---------------------------------------------------------------------------
# Como cada qualidade aparece no nome do acorde (Em, Em7, Bm7, C7, Cmaj7...)
_QUALITY_DISPLAY = {"maj": "", "min": "m", "min7": "m7"}


@dataclass
class ChordEvent:
    start: float
    end: float
    root: int                         # 0=C … 11=B
    quality: str                      # "maj", "min", "7", "maj7", …
    bass: Optional[int] = None        # nota do baixo se diferente da fundamental
    confidence: float = 0.8
    alternatives: list[str] = field(default_factory=list)
    uncertain: bool = False

    def chord_name(self, transpose: int = 0, flats: bool = False) -> str:
        root = (self.root + transpose) % 12
        name = note_name(root, flats)
        q = _QUALITY_DISPLAY.get(self.quality, self.quality)
        result = name + q
        if self.bass is not None:
            bass_root = (self.bass + transpose) % 12
            result += "/" + note_name(bass_root, flats)
        return result

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


# ---------------------------------------------------------------------------
# Dados completos de uma música
# ---------------------------------------------------------------------------
@dataclass
class MusicData:
    title: str = "Desconhecido"
    artist: str = ""
    duration: float = 0.0
    key: str = ""
    tempo: float = 0.0
    capo: int = 0
    chords: list[ChordEvent] = field(default_factory=list)
    lyrics: list[LyricLine] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    pipeline_status: PipelineStatus = PipelineStatus.PENDING
    validation_1: Optional[ValidationResult] = None
    validation_2: Optional[ValidationResult] = None
    corrections: list[CorrectionEntry] = field(default_factory=list)
    modulation_at: Optional[float] = None
    audio_file: str = ""
    audio_format: str = ""
    error_message: str = ""
