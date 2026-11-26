# Relatório da Coleção de Referência — v1.0

**Data:** 2026-11-17  
**Status:** Esqueletos criados · Aguardando áudio e anotações

---

## Resumo

| Item | Valor |
|------|-------|
| Total de músicas | 15 |
| Split dev | 12 (80%) |
| Split test | 3 (20%) |
| Com áudio | 0 |
| Com anotações | 0 |
| Testes de métricas | 48 / 48 passando |

---

## Composição da coleção

### Por estilo

| Estilo | n | Split |
|--------|---|-------|
| gospel_br | 5 | 5 dev |
| gospel_us | 5 | 5 dev |
| pop_br | 2 | 2 dev |
| pop_int | 2 | 2 test |
| acoustic | 1 | 1 test |

**Observação:** A coleção é intencionalmente pesada em gospel (66%), pois este
é o repertório alvo principal do sistema. O split test foi escolhido com
estilos e tonalidades diferentes do dev para maximizar a independência.

### Por dificuldade

| Dificuldade | n |
|-------------|---|
| easy | 4 |
| medium | 6 |
| hard | 5 |

A distribuição é equilibrada entre fácil-médio-difícil. Os 5 casos difíceis
cobrem inversões, modulações e vocabulário estendido — os pontos mais críticos
para o motor.

### Por tonalidade

As tonalidades do split dev cobrem: G, A, Bb, C, D, E major e A minor.  
Nenhuma tonalidade com muitos sustenidos ou bemóis (além de Bb) — adequado para
a fase inicial.

---

## Músicas dev (12 músicas)

| ID | Título | Artista | Tonalidade | Dificuldade | Observações |
|----|--------|---------|------------|-------------|-------------|
| gospel_br_001 | Grande é o Senhor | Ministério Ipiranga | G major | easy | I-IV-V gospel lento |
| gospel_br_002 | Deus Cuida de Mim | Fernanda Brum | A major | easy | I-V-vi-IV. Calibração básica |
| gospel_br_003 | Mais uma Vez | Soraya Moraes | Bb major | medium | Acordes de passagem, II-V-I |
| gospel_br_004 | Creio em Ti | Aline Barros | C major | medium | Dominantes secundárias |
| gospel_br_005 | Hallelujah (gospel BR) | Various | D major | hard | vi-IV-I-V com variações, inversões |
| gospel_us_001 | Amazing Grace | Traditional | G major | easy | Hino — linha de base root accuracy |
| gospel_us_002 | How Great Thou Art | Traditional | Bb major | easy | Tríades predominantes |
| gospel_us_003 | Shout to the Lord | Darlene Zschech | A major | medium | maj7 e sus4 frequentes |
| gospel_us_004 | Open the Eyes of My Heart | Paul Baloche | E major | medium | Intro longa, baixo em movimento |
| gospel_us_005 | Here I Am to Worship | Tim Hughes | E major | hard | Inversões C#m/B e A/E |
| pop_br_001 | Como é Grande o Meu Amor | Roberto Carlos | C major | medium | Balada lenta, cromatismo |
| pop_br_002 | Pais e Filhos | Legião Urbana | A minor | hard | Inversões e modulação |

---

## Músicas test (3 músicas — NÃO USAR PARA AJUSTE)

| ID | Título | Artista | Tonalidade | Dificuldade | Observações |
|----|--------|---------|------------|-------------|-------------|
| pop_int_001 | Let It Be | The Beatles | C major | medium | Clássico. Referência independente |
| pop_int_002 | Hallelujah | Leonard Cohen | C major | hard | Progressão complexa, inversões |
| acoustic_001 | Blackbird | The Beatles | G major | hard | Guitarra solo — maior dificuldade |

> **Aviso:** As 3 músicas de teste são reservadas exclusivamente para avaliação
> final independente ao término de cada fase. **Nenhuma decisão de parâmetro deve
> ser baseada nelas.**

---

## Infraestrutura criada (Prompt 2)

### Arquivos de código

| Arquivo | Descrição |
|---------|-----------|
| `evaluation/schemas/annotation.py` | Schema `AnnotatedChord` e `ReferenceAnnotation` |
| `evaluation/metrics.py` | Métricas temporalmente ponderadas (8 métricas) |
| `evaluation/evaluator.py` | Avaliador CLI + agregação por split |
| `evaluation/COMO_ADICIONAR.md` | Procedimento para adicionar músicas |
| `evaluation/RELATORIO_COLECAO_v1.md` | Este arquivo |
| `evaluation/reference/collection_manifest.json` | Índice da coleção |
| `tests/unit/test_metrics.py` | 48 testes unitários (todos passando) |

### Diretórios

```
evaluation/
  reference/
    annotations/    <- 15 arquivos JSON (esqueletos)
    audio/          <- Vazio; aguardando arquivos de áudio
  reports/          <- Será criado ao executar avaliação
  schemas/
  __init__.py
```

### Métricas implementadas

| Métrica | Critério de match | Referência |
|---------|------------------|------------|
| Root accuracy | Fundamental idêntica (mod 12) | Harte et al. 2005 |
| MajMin accuracy | Root + família maior/menor | mir_eval padrão |
| Thirds accuracy | Root + terça (maior/menor) | Progressivo |
| Sevenths accuracy | Root + terça + tipo de sétima | Progressivo |
| Tetrads accuracy | Qualidade exata | Estrito |
| Bass note accuracy | Nota de baixo | Especificidade de inversão |
| Inversion accuracy | Concordância de baixo | Apenas quando anotado |
| Segmentation F1 | Limites de acorde ± 350ms | mir_eval padrão |

Todas as métricas são calculadas por **sobreposição temporal** (weighted overlap),
não por contagem de eventos. Um acorde de 4s tem 4× o peso de um de 1s.

---

## Limitações conhecidas desta versão

1. **Sem áudio:** Nenhuma música pode ser avaliada até que os arquivos de
   áudio sejam adicionados manualmente em `evaluation/reference/audio/`.

2. **Sem anotações:** Os eventos de acorde estão vazios. As métricas
   retornarão "avaliação impossível" até que seja feita a anotação manual.

3. **Coleção pequena:** n=15 músicas não permite inferência estatística
   robusta. O sistema emite aviso explícito em todos os relatórios agregados.

4. **Sem músicas de jazz ou música clássica:** Vocabulário de extensões
   complexas (9ª, 11ª, 13ª) não está representado. Adequado para a fase atual.

---

## Próximos passos

1. Adicionar arquivos de áudio para músicas dev (começar pelas 4 "easy")
2. Anotar acordes manualmente (mínimo: refrão e versos principais)
3. Executar primeira avaliação com `python -m evaluation.evaluator --split dev`
4. Usar resultados como baseline antes do Prompt 3

---

*Relatório gerado automaticamente durante o Prompt 2 da Fase 1.*
