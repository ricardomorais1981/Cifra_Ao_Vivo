"""
Schema de anotação de referência para avaliação musical.

Uma anotação representa a verdade musical de uma música, determinada
por escuta atenta e, quando disponível, por cifras verificadas.

Formato de arquivo: JSON, um arquivo por música.
Localização: evaluation/reference/annotations/<id>.json
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import json
import os


# ---------------------------------------------------------------------------
# Certeza da anotação
# ---------------------------------------------------------------------------
class Certainty:
    """
    Grau de certeza da anotação de um evento.
    Usado para excluir eventos ambíguos das métricas principais
    e analisá-los separadamente.
    """
    HIGH   = "high"    # acorde identificado com segurança
    MEDIUM = "medium"  # acorde provável, pequena dúvida
    LOW    = "low"     # ambíguo — registrar mas não usar como verdade absoluta


# ---------------------------------------------------------------------------
# Evento harmônico anotado
# ---------------------------------------------------------------------------
@dataclass
class AnnotatedChord:
    """
    Um evento harmônico com início e fim precisos.

    Campos obrigatórios: start, end, root, quality.
    Campos opcionais: bass, inversion, certainty, notes.

    Inversão é registrada apenas quando há evidência acústica clara.
    Nunca presumida a partir da teoria.
    """
    start: float                        # início em segundos
    end: float                          # fim em segundos
    root: str                           # "C", "C#", "Db", ... "B"
    quality: str                        # "maj", "min", "7", "maj7", etc.

    bass: Optional[str] = None          # nota do baixo se diferente da fundamental
    inversion: Optional[str] = None     # "1st", "2nd", "3rd" ou None
    certainty: str = Certainty.HIGH     # grau de certeza desta anotação
    notes: str = ""                     # observações livres sobre ambiguidades

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    @property
    def root_int(self) -> int:
        """Converte nome da nota para inteiro 0=C…11=B."""
        return _note_to_int(self.root)

    @property
    def bass_int(self) -> Optional[int]:
        return _note_to_int(self.bass) if self.bass else None

    @property
    def quality_family(self) -> str:
        """Família simplificada: 'maj' ou 'min'."""
        q = self.quality.lower()
        if q.startswith("m") and not q.startswith("maj"):
            return "min"
        return "maj"


# ---------------------------------------------------------------------------
# Conjunto de dados de uma música
# ---------------------------------------------------------------------------
@dataclass
class ReferenceAnnotation:
    """
    Anotação completa de uma música de referência.

    split: "dev" para desenvolvimento/calibração, "test" para avaliação
    independente. Nunca usar músicas de teste para ajuste de parâmetros.
    """
    id: str                             # identificador único, ex: "gospel_001"
    title: str
    artist: str
    duration: float                     # duração total em segundos
    key: str                            # tonalidade principal, ex: "G major"
    bpm: Optional[float] = None
    time_signature: str = "4/4"
    split: str = "dev"                  # "dev" ou "test"
    style: str = ""                     # "gospel_br", "gospel_us", "pop", etc.
    difficulty: str = "medium"          # "easy", "medium", "hard"
    audio_file: str = ""                # nome do arquivo em reference/audio/
    source_url: str = ""                # origem da cifra de referência (se houver)
    annotator_notes: str = ""           # observações gerais sobre a música
    events: list[AnnotatedChord] = field(default_factory=list)

    def events_by_certainty(self, certainty: str) -> list[AnnotatedChord]:
        return [e for e in self.events if e.certainty == certainty]

    def high_certainty_events(self) -> list[AnnotatedChord]:
        return self.events_by_certainty(Certainty.HIGH)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @staticmethod
    def from_dict(d: dict) -> "ReferenceAnnotation":
        events = [AnnotatedChord(**e) for e in d.pop("events", [])]
        return ReferenceAnnotation(**d, events=events)

    def save(self, directory: str) -> str:
        """Salva em directory/<id>.json"""
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"{self.id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    @staticmethod
    def load(path: str) -> "ReferenceAnnotation":
        with open(path, encoding="utf-8") as f:
            return ReferenceAnnotation.from_dict(json.load(f))


# ---------------------------------------------------------------------------
# Utilitários de nota
# ---------------------------------------------------------------------------
_NOTE_MAP = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "F": 5, "E#": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}

def _note_to_int(note: str) -> int:
    note = note.strip()
    if note not in _NOTE_MAP:
        raise ValueError(f"Nota desconhecida: '{note}'")
    return _NOTE_MAP[note]
