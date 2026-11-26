# Relatório de Avaliação — gospel_br_001

**Música:** Grande e o Senhor (Nova Versao)
**Artista:** Comunidade Crista Maranata
**Data de anotação:** 2026-11-18
**Método:** Chromagrama STFT manual (hop=0.5s, win=2s, 48kHz→22050Hz)

---

## 3. Relatório de Cobertura

| Categoria | Duração (s) | Duração (min:ss) | % da música |
|-----------|-------------|-----------------|-------------|
| **Duração total** | 283.3 | 4:43.27 | 100.0% |
| Anotada (total) | 271.0 | 4:31.00 | 95.7% |
| — Alta certeza | 219.5 | 3:39.50 | 77.5% |
| — Média certeza | 47.5 | 0:47.50 | 16.8% |
| — Baixa certeza | 4.0 | 0:04.00 | 1.4% |
| **Não anotada (gaps)** | 12.3 | 0:12.27 | 4.3% |

> **Cobertura de alta certeza: 77.5%** (meta de referência: 70%)
> **Cobertura total anotada: 95.7%**

### Detalhamento dos gaps (trechos não anotados)

| Início | Fim | Duração | Motivo |
|--------|-----|---------|--------|
| 0:00.00 | 0:01.00 | 1.0s | Silêncio do intro |
| 1:04.00 | 1:04.50 | 0.5s | Micro gap entre acordes (transição) |
| 1:19.00 | 1:19.50 | 0.5s | Micro gap entre acordes (transição) |
| 1:51.00 | 1:51.50 | 0.5s | Micro gap entre acordes (transição) |
| 2:01.00 | 2:01.50 | 0.5s | Micro gap entre acordes (transição) |
| 2:26.50 | 2:27.00 | 0.5s | Micro gap entre acordes (transição) |
| 2:29.00 | 2:29.50 | 0.5s | Micro gap entre acordes (transição) |
| 2:31.00 | 2:31.50 | 0.5s | Micro gap entre acordes (transição) |
| 2:33.00 | 2:33.50 | 0.5s | Micro gap entre acordes (transição) |
| 2:53.50 | 2:54.50 | 1.0s | Micro gap entre acordes (transição) |
| 2:58.50 | 2:59.00 | 0.5s | Micro gap entre acordes (transição) |
| 3:01.00 | 3:01.50 | 0.5s | Micro gap entre acordes (transição) |
| 3:05.50 | 3:06.00 | 0.5s | Micro gap entre acordes (transição) |
| 3:14.50 | 3:15.00 | 0.5s | Micro gap entre acordes (transição) |
| 3:22.00 | 3:22.50 | 0.5s | Micro gap entre acordes (transição) |
| 3:30.50 | 3:31.00 | 0.5s | Micro gap entre acordes (transição) |
| 4:02.00 | 4:03.00 | 1.0s | Micro gap entre acordes (transição) |
| 4:30.50 | 4:31.50 | 1.0s | Micro gap entre acordes (transição) |
| 4:42.00 | 4:43.27 | 1.3s | Silêncio/fade final |

---

## 4. Trechos cuja harmonia não pôde ser determinada com segurança

### 4.1 Trechos com certeza baixa

- **3:47.00–3:51.00** (4.0s): Am min — Zona de transicao tonal. Chromagram mostra Am-A. Modulacao para A major em andamento.

### 4.2 Trechos com incerteza estrutural (certeza média com divergência da referência)

- **0:33.50–0:35.00**: Am detectado vs Em da referência. O chromagram mostra Am com score 0.161. Pode ser passagem G→Em onde o cromograma captura o Am implícito do Em em contexto cadencial.
- **0:45.00–0:48.00**: G e Em detectados onde referência indica Bm→C→D. O padrão G/B (posição fundamental com baixo Si) é harmonicamente equivalente ao Bm em função cadencial, mas o chromagrama STFT não distingue inversões. Os eventos C e D desta frase também aparecem deslocados temporalmente.
- **0:48.00–0:50.50**: Am detectado onde referência indica C. Ambos contêm notas em comum (C-E-G vs A-C-E). Em velocidade gospel, o chromagrama de janela 2s pode misturar os dois acordes.
- **3:42.50–3:46.50 (222.5–227.0s)**: Em detectado como transição pré-modulação. Chromagram instável entre Em, Am e A. Região de transição tonal confirmada.
- **3:47.00–3:51.00 (227.0–231.0s)**: Zona de modulação Am→A. Certeza baixa. O chromagram mostra escores quase iguais para Am e A.
- **3:58.50–4:02.00 (238.5–242.0s)**: Em/G detectados no refrão em A major. Pode ser C/E (inversão do acorde C com baixo Mi) que o chromagrama não reconhece como acorde A-major diatônico. Requer verificação auditiva.
- **4:16.50–4:31.50 (256.0–262.5s)**: G detectado com score muito alto (0.230) no contexto do refrão final em A major. Possível acordes G como VII emprestado, ou o arranjo usa G como dominante da dominante (D7/G). Requer verificação auditiva da gravação.

---

## 5. Divergências entre a sequência fornecida e o que foi identificado na gravação

### Acorde Bm (verso 1 e 2 — 'Alegria de toda terra')

A referência indica G Am **Bm** C D na frase 'Alegria de toda terra'. O chromagram detecta G→Am→**G**→Em→Am nessa região (0:45–0:50). O Bm não aparece como acorde independente no chromagram. Hipótese: o arranjo usa G/B (posição fundamental de G com baixo Si) em vez de Bm. O resultado sonoro é harmonicamente semelhante, mas o chromagram vê G.

### C vs Am na região pós-'Alegria' (0:48–0:51)

A referência indica C→D ao final da frase 'Alegria'. O chromagram detecta Am (0.204). Am e C compartilham duas notas (Dó e Mi), tornando-os difíceis de distinguir com janela STFT de 2s. Certeza média atribuída.

### Ordem dos acordes no Verso 1 (início)

A referência indica início em G. O chromagram detecta Em (1–3s) antes do G. Possível explanação: a intro instrumental usa um pickup em Em antes da entrada vocal em G. Certeza média atribuída ao Em inicial.

### Refrões 3 e 4 em A major vs G major da referência

A referência harmônica fornecida está em G major (G Bm C Am D). O chromagram confirma inequivocamente A major a partir de ~231s: A (score 0.27+), F#m (0.24+), Bm, D. Esta modulação um tom acima é comum em gospel para elevar a intensidade no clímax. A análise identifica: A D (Bm) F#m D A em vez do G Bm C Am D da referência. A sequência em A major é: A=I, D=IV, F#m=vi, Bm=ii. Esta divergência é **esperada** e reflete a modulação real da gravação.

### G (256–262.5s) no contexto A major

Acorde G aparece com score muito alto (0.230) no meio do refrão final em A major. Na referência (G major): seria o acorde tônica. Em A major: seria o VII grau ou um empréstimo modal. Pode ser também uma seção de transição harmônica. Necessita confirmação auditiva da gravação.

### F#m vs Bm no refrão final

O chromagram do refrão final (4:26–4:30, 266–270.5s) mostra F#m claramente. Na referência em G major, o vi grau seria Em. Em A major, o vi grau é F#m. Esta é consistente com a modulação para A major confirmada.

---

## Notas gerais do método

- **Sem librosa/soundfile no ambiente de desenvolvimento:** o chromagram foi calculado com numpy STFT manual (sem CQT, sem HPSS). Isso reduz a precisão em regiões com muita sobreposição espectral (passagens rápidas, acordes com extensões) mas é adequado para identificar acordes principais estáveis.
- **Inversões não detectáveis:** o chromagrama STFT não distingue posição fundamental de inversões. Nenhuma inversão foi anotada.
- **Scores baixos indicam ambiguidade:** scores abaixo de 0.14 foram anotados com certeza média ou baixa, independentemente da referência.
- **A anotação precedência acústica:** onde o chromagram diverge da referência, a anotação reflete o que o método detectou na gravação, com as divergências documentadas acima.