"""
Testes unitários do pipeline de validação/correção harmônica.
Execute com: python -m pytest tests/unit/test_pipeline.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from shared.schemas.music_data import ChordEvent, MusicData, PipelineStatus
from local_engine.validation.pipeline import (
    estimate_key,
    validate_recognition,
    correct_harmony,
    validate_correction,
    run_pipeline,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_chord(root: int, quality: str, start: float, duration: float,
               confidence: float = 0.9) -> ChordEvent:
    return ChordEvent(
        start=start, end=start + duration,
        root=root, quality=quality,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# 1. Estimativa de tonalidade
# ---------------------------------------------------------------------------
class TestEstimateKey:
    def test_c_major(self):
        # I-IV-V-I em Dó maior (C-F-G-C)
        chords = [
            make_chord(0, "maj", 0,  4),   # C
            make_chord(5, "maj", 4,  4),   # F
            make_chord(7, "maj", 8,  4),   # G
            make_chord(0, "maj", 12, 4),   # C
        ]
        root, mode = estimate_key(chords)
        assert root == 0
        assert mode == "major"

    def test_a_minor(self):
        # i-iv-V em Lá menor
        chords = [
            make_chord(9, "min", 0,  4),   # Am
            make_chord(2, "min", 4,  4),   # Dm
            make_chord(4, "maj", 8,  4),   # E
            make_chord(9, "min", 12, 4),   # Am
        ]
        root, mode = estimate_key(chords)
        assert root == 9
        assert mode == "minor"

    def test_g_major(self):
        # G-Em-C-D (I-vi-IV-V)
        chords = [
            make_chord(7, "maj", 0,  4),   # G
            make_chord(4, "min", 4,  4),   # Em
            make_chord(0, "maj", 8,  4),   # C
            make_chord(2, "maj", 12, 4),   # D
        ]
        root, mode = estimate_key(chords)
        assert root == 7
        assert mode == "major"


# ---------------------------------------------------------------------------
# 2. Validação do reconhecimento
# ---------------------------------------------------------------------------
class TestValidateRecognition:
    def test_good_sequence_passes(self):
        # Sequência limpa, diatônica, sem oscilação
        chords = [
            make_chord(0, "maj", i * 2, 2, confidence=0.9)
            for i in range(10)
        ]
        v = validate_recognition(chords, total_duration=20.0)
        assert v.passed is True
        assert v.score > 0.6

    def test_empty_fails(self):
        v = validate_recognition([], total_duration=10.0)
        assert v.passed is False

    def test_low_confidence_fails(self):
        chords = [
            make_chord(0, "maj", i * 2, 2, confidence=0.4)
            for i in range(10)
        ]
        v = validate_recognition(chords, total_duration=20.0)
        assert v.passed is False

    def test_oscillation_detected(self):
        # Muitos acordes com duração < 0.4s
        chords = [
            make_chord(0, "maj", i * 0.2, 0.2, confidence=0.9)
            for i in range(50)
        ]
        v = validate_recognition(chords, total_duration=10.0)
        assert v.oscillation < 0.85  # oscilação elevada detectada


# ---------------------------------------------------------------------------
# 3. Correção harmônica
# ---------------------------------------------------------------------------
class TestCorrectHarmony:
    def test_no_correction_needed(self):
        # Todos diatônicos com qualidade certa → sem correções
        chords = [
            make_chord(0, "maj", 0,  4),   # I C
            make_chord(5, "maj", 4,  4),   # IV F
            make_chord(7, "maj", 8,  4),   # V G
            make_chord(9, "min", 12, 4),   # vi Am
        ]
        corrected, log = correct_harmony(chords, key=0, mode="major")
        assert len(log) == 0

    def test_wrong_quality_corrected(self):
        # ii com qualidade "maj" deveria ser "min" (Dm, não D)
        chords = [
            make_chord(0, "maj",  0, 4),   # I C
            make_chord(2, "maj",  4, 4),   # ii com maj (errado — deveria ser min)
            make_chord(5, "maj",  8, 4),   # IV F
            make_chord(0, "maj", 12, 4),   # I C
        ]
        corrected, log = correct_harmony(chords, key=0, mode="major")
        # Esperamos que o acorde no índice 1 seja corrigido para "min"
        assert corrected[1].quality == "min"
        assert len(log) >= 1

    def test_secondary_dominant_preserved(self):
        # E7 (IV/vi ou V7/vi) deve ser preservado
        chords = [
            make_chord(0,  "maj", 0, 4),   # C
            make_chord(4,  "7",   4, 4),   # E7 (dominante secundária)
            make_chord(9,  "min", 8, 4),   # Am
        ]
        corrected, log = correct_harmony(chords, key=0, mode="major")
        assert corrected[1].quality == "7"  # preservado


# ---------------------------------------------------------------------------
# 4. Segunda validação
# ---------------------------------------------------------------------------
class TestValidateCorrection:
    def test_good_correction_passes(self):
        original = [make_chord(0, "maj", 0, 4, confidence=0.9)]
        corrected = [make_chord(0, "maj", 0, 4, confidence=0.9)]
        log = []
        v = validate_correction(original, corrected, log)
        assert v.passed is True

    def test_too_many_changes_fails(self):
        original  = [make_chord(i % 12, "maj", i*2, 2, 0.9) for i in range(20)]
        corrected = [make_chord((i+1) % 12, "min", i*2, 2, 0.9) for i in range(20)]
        from shared.schemas.music_data import CorrectionEntry
        log = [CorrectionEntry(t=i*2, original="X", corrected="Y",
                               reason="test") for i in range(20)]
        v = validate_correction(original, corrected, log)
        assert v.passed is False


# ---------------------------------------------------------------------------
# 5. Pipeline completo
# ---------------------------------------------------------------------------
class TestRunPipeline:
    def test_approved_pipeline(self):
        chords = [
            make_chord(0, "maj", i * 2, 2, confidence=0.88)
            for i in range(12)
        ]
        music = MusicData(
            title="Test", duration=24.0,
            chords=chords,
        )
        result = run_pipeline(music)
        assert result.pipeline_status in (
            PipelineStatus.APPROVED,
            PipelineStatus.APPROVED_AFTER_FIX,
            PipelineStatus.QUALITY_UNCONFIRMED,
        )
        assert result.key != ""  # tonalidade estimada

    def test_empty_chords_error(self):
        music = MusicData(title="Vazio", duration=10.0, chords=[])
        result = run_pipeline(music)
        assert result.pipeline_status == PipelineStatus.ERROR


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
