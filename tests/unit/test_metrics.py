"""
Testes unitários para evaluation/metrics.py

Cobertura:
- Sobreposição temporal (_overlap)
- Score ponderado (_weighted_score)
- Funções de match por nível (root, majmin, thirds, sevenths, tetrads, bass, inversion)
- Segmentação temporal (_segmentation_score)
- Avaliação completa (evaluate)
- Casos de borda (sem eventos, sem sobreposição, cobertura parcial)
"""

import sys
import os
import pytest

# Garante que a raiz do projeto está no path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from evaluation.schemas.annotation import AnnotatedChord, ReferenceAnnotation, Certainty
from evaluation.metrics import (
    _overlap,
    _weighted_score,
    _root_match,
    _majmin_match,
    _thirds_match,
    _sevenths_match,
    _tetrads_match,
    _bass_match,
    _inversion_match,
    _segmentation_score,
    evaluate,
    MetricResult,
    EvaluationReport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _chord(start: float, end: float, root: str, quality: str,
           bass: str | None = None, certainty: str = Certainty.HIGH) -> AnnotatedChord:
    return AnnotatedChord(start=start, end=end, root=root, quality=quality,
                          bass=bass, certainty=certainty)


def _hyp(start: float, end: float, root_int: int, quality: str,
         bass: int | None = None) -> dict:
    return {"start": start, "end": end, "root": root_int,
            "quality": quality, "bass": bass}


def _ref(events: list[AnnotatedChord], id_: str = "test_001") -> ReferenceAnnotation:
    return ReferenceAnnotation(
        id=id_, title="Teste", artist="Artista",
        duration=sum(e.duration for e in events),
        key="C major", split="dev", style="test", difficulty="easy",
        events=events,
    )


# ---------------------------------------------------------------------------
# _overlap
# ---------------------------------------------------------------------------
class TestOverlap:
    def test_completa(self):
        assert _overlap(0.0, 4.0, 0.0, 4.0) == pytest.approx(4.0)

    def test_parcial_inicio(self):
        assert _overlap(0.0, 4.0, 2.0, 6.0) == pytest.approx(2.0)

    def test_parcial_fim(self):
        assert _overlap(2.0, 6.0, 0.0, 4.0) == pytest.approx(2.0)

    def test_sem_sobreposicao(self):
        assert _overlap(0.0, 2.0, 3.0, 5.0) == pytest.approx(0.0)

    def test_adjacentes(self):
        # Fim de um = início do outro → sobreposição zero
        assert _overlap(0.0, 2.0, 2.0, 4.0) == pytest.approx(0.0)

    def test_contido(self):
        assert _overlap(1.0, 3.0, 0.0, 5.0) == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# _root_match
# ---------------------------------------------------------------------------
class TestRootMatch:
    def test_correto(self):
        ref = _chord(0, 4, "G", "maj")
        hyp = _hyp(0, 4, 7, "maj")  # G=7
        assert _root_match(ref, hyp) is True

    def test_errado(self):
        ref = _chord(0, 4, "G", "maj")
        hyp = _hyp(0, 4, 0, "maj")  # C=0
        assert _root_match(ref, hyp) is False

    def test_enarmonia(self):
        # F# (6) e Gb (6) são o mesmo pitch
        ref = _chord(0, 4, "F#", "maj")
        hyp = _hyp(0, 4, 6, "maj")
        assert _root_match(ref, hyp) is True

    def test_root_int_modulo_12(self):
        # root=12 deve ser equivalente a 0 (C)
        ref = _chord(0, 4, "C", "maj")
        hyp = _hyp(0, 4, 12, "maj")
        assert _root_match(ref, hyp) is True


# ---------------------------------------------------------------------------
# _majmin_match
# ---------------------------------------------------------------------------
class TestMajminMatch:
    def test_ambos_maior(self):
        ref = _chord(0, 4, "G", "maj")
        hyp = _hyp(0, 4, 7, "7")  # G7 é família maior
        assert _majmin_match(ref, hyp) is True

    def test_ambos_menor(self):
        ref = _chord(0, 4, "A", "min")
        hyp = _hyp(0, 4, 9, "min7")
        assert _majmin_match(ref, hyp) is True

    def test_root_errado(self):
        ref = _chord(0, 4, "G", "maj")
        hyp = _hyp(0, 4, 0, "maj")  # root diferente
        assert _majmin_match(ref, hyp) is False

    def test_qualidade_oposta(self):
        ref = _chord(0, 4, "A", "min")
        hyp = _hyp(0, 4, 9, "maj")
        assert _majmin_match(ref, hyp) is False

    def test_maj7_e_maior(self):
        ref = _chord(0, 4, "C", "maj7")
        hyp = _hyp(0, 4, 0, "maj")
        assert _majmin_match(ref, hyp) is True


# ---------------------------------------------------------------------------
# _thirds_match
# ---------------------------------------------------------------------------
class TestThirdsMatch:
    def test_dim_familia_menor(self):
        ref = _chord(0, 4, "B", "dim")
        hyp = _hyp(0, 4, 11, "min")  # min tem terça menor
        assert _thirds_match(ref, hyp) is True

    def test_aug_familia_maior(self):
        ref = _chord(0, 4, "C", "aug")
        hyp = _hyp(0, 4, 0, "maj")
        assert _thirds_match(ref, hyp) is True

    def test_cross_familia(self):
        ref = _chord(0, 4, "C", "maj")
        hyp = _hyp(0, 4, 0, "min")
        assert _thirds_match(ref, hyp) is False


# ---------------------------------------------------------------------------
# _sevenths_match
# ---------------------------------------------------------------------------
class TestSeventhsMatch:
    def test_ambos_sem_setima(self):
        ref = _chord(0, 4, "G", "maj")
        hyp = _hyp(0, 4, 7, "maj")
        assert _sevenths_match(ref, hyp) is True

    def test_ref_7_hyp_7(self):
        ref = _chord(0, 4, "G", "7")
        hyp = _hyp(0, 4, 7, "7")
        assert _sevenths_match(ref, hyp) is True

    def test_ref_maj7_hyp_7(self):
        # maj7 ≠ min7 (dominante)
        ref = _chord(0, 4, "C", "maj7")
        hyp = _hyp(0, 4, 0, "7")
        assert _sevenths_match(ref, hyp) is False

    def test_ref_min7_hyp_min(self):
        # min sem sétima ≠ min7
        ref = _chord(0, 4, "A", "min7")
        hyp = _hyp(0, 4, 9, "min")
        assert _sevenths_match(ref, hyp) is False


# ---------------------------------------------------------------------------
# _tetrads_match
# ---------------------------------------------------------------------------
class TestTetradsMatch:
    def test_exato(self):
        ref = _chord(0, 4, "G", "7")
        hyp = _hyp(0, 4, 7, "7")
        assert _tetrads_match(ref, hyp) is True

    def test_case_insensitive(self):
        ref = _chord(0, 4, "C", "maj7")
        hyp = _hyp(0, 4, 0, "MAJ7")
        assert _tetrads_match(ref, hyp) is True

    def test_diferente(self):
        ref = _chord(0, 4, "C", "maj7")
        hyp = _hyp(0, 4, 0, "7")
        assert _tetrads_match(ref, hyp) is False


# ---------------------------------------------------------------------------
# _bass_match
# ---------------------------------------------------------------------------
class TestBassMatch:
    def test_posicao_fundamental_ambos(self):
        ref = _chord(0, 4, "C", "maj", bass=None)
        hyp = _hyp(0, 4, 0, "maj", bass=None)
        assert _bass_match(ref, hyp) is True

    def test_inversao_ref_sem_hipotese(self):
        # Referência com baixo em E (primeira inversão de C), hipótese sem baixo
        # Hipótese assume root=C, referência tem baixo=E → não bate
        ref = _chord(0, 4, "C", "maj", bass="E")  # E=4
        hyp = _hyp(0, 4, 0, "maj", bass=None)      # assume baixo = root = C
        assert _bass_match(ref, hyp) is False

    def test_inversao_correta(self):
        ref = _chord(0, 4, "C", "maj", bass="E")
        hyp = _hyp(0, 4, 0, "maj", bass=4)  # E=4
        assert _bass_match(ref, hyp) is True

    def test_root_errado_ignora_baixo(self):
        ref = _chord(0, 4, "C", "maj", bass=None)
        hyp = _hyp(0, 4, 7, "maj", bass=None)  # G≠C
        assert _bass_match(ref, hyp) is False


# ---------------------------------------------------------------------------
# _inversion_match
# ---------------------------------------------------------------------------
class TestInversionMatch:
    def test_ambos_sem_baixo(self):
        ref = _chord(0, 4, "G", "maj", bass=None)
        hyp = _hyp(0, 4, 7, "maj", bass=None)
        assert _inversion_match(ref, hyp) is True

    def test_ref_sem_hyp_com_baixo(self):
        ref = _chord(0, 4, "G", "maj", bass=None)
        hyp = _hyp(0, 4, 7, "maj", bass=11)  # B
        assert _inversion_match(ref, hyp) is False

    def test_ambos_com_mesmo_baixo(self):
        ref = _chord(0, 4, "C", "maj", bass="E")  # E=4
        hyp = _hyp(0, 4, 0, "maj", bass=4)
        assert _inversion_match(ref, hyp) is True


# ---------------------------------------------------------------------------
# _weighted_score
# ---------------------------------------------------------------------------
class TestWeightedScore:
    def test_tudo_correto(self):
        ref_events = [_chord(0, 4, "G", "maj"), _chord(4, 8, "C", "maj")]
        hyp_events = [_hyp(0, 4, 7, "maj"), _hyp(4, 8, 0, "maj")]
        score, correct, total = _weighted_score(ref_events, hyp_events, _root_match)
        assert score == pytest.approx(1.0, abs=1e-6)
        assert correct == pytest.approx(8.0, abs=1e-6)

    def test_tudo_errado(self):
        ref_events = [_chord(0, 4, "G", "maj")]
        hyp_events = [_hyp(0, 4, 0, "maj")]  # C, não G
        score, correct, total = _weighted_score(ref_events, hyp_events, _root_match)
        assert score == pytest.approx(0.0, abs=1e-6)

    def test_metade_correta(self):
        # 4s corretos (G) + 4s errados (G→C)
        ref_events = [_chord(0, 4, "G", "maj"), _chord(4, 8, "C", "maj")]
        hyp_events = [_hyp(0, 4, 7, "maj"), _hyp(4, 8, 7, "maj")]  # 2º G errado
        score, correct, total = _weighted_score(ref_events, hyp_events, _root_match)
        assert score == pytest.approx(0.5, abs=1e-6)

    def test_sem_hipotese(self):
        ref_events = [_chord(0, 4, "G", "maj")]
        score, correct, total = _weighted_score(ref_events, [], _root_match)
        assert score == pytest.approx(0.0, abs=1e-6)
        assert total == pytest.approx(4.0, abs=1e-6)

    def test_hipotese_mais_longa(self):
        # Hipótese cobre mais do que a referência — só a sobreposição conta
        ref_events = [_chord(1, 3, "G", "maj")]
        hyp_events = [_hyp(0, 4, 7, "maj")]
        score, correct, total = _weighted_score(ref_events, hyp_events, _root_match)
        assert score == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# _segmentation_score
# ---------------------------------------------------------------------------
class TestSegmentationScore:
    def test_limites_perfeitos(self):
        ref = [_chord(0, 4, "G", "maj"), _chord(4, 8, "C", "maj")]
        hyp = [_hyp(0, 4, 7, "maj"), _hyp(4, 8, 0, "maj")]
        f1, prec, rec = _segmentation_score(ref, hyp)
        assert f1 == pytest.approx(1.0, abs=1e-6)

    def test_dentro_tolerancia(self):
        # Limite de referência em 4.0s, hipótese em 4.2s (dentro de 350ms)
        ref = [_chord(0, 4.0, "G", "maj"), _chord(4.0, 8.0, "C", "maj")]
        hyp = [_hyp(0, 4.2, 7, "maj"), _hyp(4.2, 8.0, 0, "maj")]
        f1, prec, rec = _segmentation_score(ref, hyp)
        assert f1 == pytest.approx(1.0, abs=1e-6)

    def test_fora_tolerancia(self):
        # Limite de referência em 4.0s, hipótese em 4.5s (além de 350ms)
        ref = [_chord(0, 4.0, "G", "maj"), _chord(4.0, 8.0, "C", "maj")]
        hyp = [_hyp(0, 4.5, 7, "maj"), _hyp(4.5, 8.0, 0, "maj")]
        f1, prec, rec = _segmentation_score(ref, hyp)
        # 0.0s não corresponde (ambos têm), 4.0 não tem correspondência em hyp
        assert f1 < 1.0

    def test_sem_hipotese(self):
        ref = [_chord(0, 4, "G", "maj")]
        f1, prec, rec = _segmentation_score(ref, [])
        assert f1 == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# evaluate — casos de borda
# ---------------------------------------------------------------------------
class TestEvaluate:
    def test_sem_eventos(self):
        ref = _ref([])
        report = evaluate(ref, [])
        assert report.root_accuracy is None
        assert any("impossível" in lim for lim in report.limitations)

    def test_apenas_baixa_certeza(self):
        ref = _ref([_chord(0, 4, "G", "maj", certainty=Certainty.LOW)])
        report = evaluate(ref, [_hyp(0, 4, 7, "maj")])
        assert report.root_accuracy is None
        assert any("impossível" in lim for lim in report.limitations)

    def test_perfeito(self):
        events = [
            _chord(0.0, 4.0, "G",  "maj"),
            _chord(4.0, 8.0, "C",  "maj"),
            _chord(8.0, 12.0, "D", "7"),
            _chord(12.0, 16.0, "G", "maj"),
        ]
        ref = _ref(events)
        hyp = [
            _hyp(0.0,  4.0,  7, "maj"),
            _hyp(4.0,  8.0,  0, "maj"),
            _hyp(8.0,  12.0, 2, "7"),
            _hyp(12.0, 16.0, 7, "maj"),
        ]
        report = evaluate(ref, hyp)
        assert report.root_accuracy.score == pytest.approx(1.0, abs=1e-4)
        assert report.majmin_accuracy.score == pytest.approx(1.0, abs=1e-4)
        assert report.tetrads_accuracy.score == pytest.approx(1.0, abs=1e-4)

    def test_root_correto_qualidade_errada(self):
        # G maj reconhecido como G min — root correto, qualidade errada
        ref = _ref([_chord(0, 4, "G", "maj")])
        hyp = [_hyp(0, 4, 7, "min")]
        report = evaluate(ref, hyp)
        assert report.root_accuracy.score   == pytest.approx(1.0, abs=1e-4)
        assert report.majmin_accuracy.score == pytest.approx(0.0, abs=1e-4)

    def test_cobertura_baixa_emite_aviso(self):
        # Apenas 1s anotado de alta certeza, 10s de baixa → cobertura < 50%
        events = (
            [_chord(0, 1, "G", "maj", certainty=Certainty.HIGH)] +
            [_chord(i, i+1, "C", "maj", certainty=Certainty.LOW) for i in range(1, 10)]
        )
        ref = _ref(events)
        hyp = [_hyp(0, 10, 7, "maj")]
        report = evaluate(ref, hyp)
        assert any("incerteza elevada" in lim for lim in report.limitations)

    def test_sem_inversoes_anotadas(self):
        ref = _ref([_chord(0, 4, "G", "maj")])
        hyp = [_hyp(0, 4, 7, "maj")]
        report = evaluate(ref, hyp)
        assert report.inversion_accuracy is None
        assert any("inversão" in lim.lower() for lim in report.limitations)

    def test_relatorio_summary_nao_falha(self):
        """summary() deve funcionar mesmo com métricas parcialmente preenchidas."""
        events = [_chord(0, 4, "G", "maj")]
        ref = _ref(events)
        hyp = [_hyp(0, 4, 7, "maj")]
        report = evaluate(ref, hyp)
        summary = report.summary()
        assert "Teste" in summary  # título presente
