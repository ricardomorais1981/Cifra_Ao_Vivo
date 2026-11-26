# Relatório de Cobertura — gospel_us_001

**I Thank You for the Cross** | Colby Wedgeworth, Tauren Wells, Jonathan Smith  
Arquivo: `gospel_us_001.wav` | Duração: 267.253 s | Tonalidade: C major | BPM: 75 | Compasso: 4/4

---

## 1. Sumário de Cobertura

| Métrica | Valor |
| --- | --- |
| Duração total do áudio | 267.3 s |
| Duração anotada | 265.5 s |
| Cobertura total | 99.3 % |
| Alta certeza (✓) | 187.0 s (70.0 %) |
| Média certeza (~) | 76.0 s (28.4 %) |
| Baixa certeza (?) | 2.5 s (0.9 %) |
| Lacunas não anotadas | 1.8 s (0.7 %) |
| Total de eventos | 81 |
| Eventos com baixo específico | 21 |

---

## 2. Lacunas Identificadas

| Lacuna | Intervalo | Duração | Motivo |
| --- | --- | --- | --- |
| Silêncio inicial | 0.00–1.00 s | 1.0 s | Silêncio / percussão sem harmonia definida |
| Micropausa final | 266.5–267.3 s | 0.8 s | Fade-out / sinal abaixo do limiar |

Apenas 2 lacunas identificadas; a música é altamente contínua harmonicamente (99.3% de cobertura).

---

## 3. Trechos com Harmonia Indeterminada ou Ambígua

| # | Intervalo | Acorde anotado | Motivo da ambiguidade |
| --- | --- | --- | --- |
| 1 | 2:03–2:05 | Csus (~) | Csus4 e Fsus2 têm espectro cromático idêntico; contexto decide Csus |
| 2 | 2:12–2:16 | Asus (~) | Dsus2/Asus4 equivalentes em chromagrama — Asus pelo contexto harmônico |
| 3 | 2:35–2:37 | F/A-Am zona (~) | Transição F/A→Am mal definida; limite estimado pelo BPM/contexto |
| 4 | 3:32–3:33 | F-G zona | Micropausa entre pontes; score baixo neste frame |
| 5 | 4:07.5–4:11 | C(no3) (~) | Ausência de terça real; C5 identificado sem tríade completa |
| 6 | 4:06–4:07 | Gsus (zona) | G5 / Dsus4 frame — transição Bridge→Half-Chorus |
| 7 | 2:32–2:33 | Fm6 (~) | Área Fm6 de curta duração; score menor de F confirmado mas qualidade min6 inferida |

---

## 4. Acordes com Baixo Específico

21 eventos contêm baixo específico — todos coerentes com a cifra de referência:

| Acorde cifra | Ocorrências | Bass anotado | Inversão |
| --- | --- | --- | --- |
| G/B | 4 | B | 1ª |
| F/A | 10 | A | 1ª |
| C/E | 6 | E | 1ª |
| C/G | 1 | G | 2ª |

O chromagrama não detecta diretamente a nota do baixo (integra toda a energia harmônica). As notas de baixo foram inferidas pelo contexto harmônico e pela cifra de referência. O motor de produção (com rastreamento de grave separado) deverá verificar essas inversões.

---

## 5. Divergências entre Referência (Cifra) e Gravação

| # | Trecho | Cifra | Anotado | Explicação |
| --- | --- | --- | --- | --- |
| 1 | 0:48–0:51 | Csus→C (passagem) | C maj direto | Transição Csus→C rápida; chromagrama não separa os 2s de janela |
| 2 | 1:37–1:40 | Gsus→G | G sus detectado mas score baixo | Gsus4 deduzido; score similar a Csus4 (compartilham espectro) |
| 3 | 2:12–2:16 | Am→Asus | Asus detectado como Dsus2/Asus4 | Ambos equivalentes em chromagrama; interpretado como Asus pelo contexto |
| 4 | 2:32–2:33 | F-Fm6-C/G-G | Fm6 / C/G com certeza baixa | Fm6 e C/G têm duração muito curta (~2s) para o hop=0.5s / janela=2s |
| 5 | 3:11–3:16 | F-G-F/A-C/E | Detectado como F área (Fadd9/Dm7) | Interlude em região de alta dinâmica — inversões F/A e C/E inferidas |
| 6 | 4:07.5–4:12 | C(no3)-C(no3) | Annotado como C 5 (power chord) | C(no3) = C sem terça ≈ C5 no chromagrama; representação equivalente |

Nenhuma divergência indica erro interpretativo fundamental. As divergências são consequência das limitações do STFT manual (janela larga, sem resolução de baixo) e da notação do chromagrama vs. acordes de passagem rápida.

---

## 6. Análise da Estrutura Musical

| Seção | Intervalo aprox. | Duração | Descrição |
| --- | --- | --- | --- |
| Intro | 0–7 s | 7 s | C sustentado; entrada gradual do arranjo |
| Verso 1 | 7–55 s | 48 s | Dm-C / Csus-C / G/B-Am / F/A-Am / Gsus-F / F-C |
| Verso 2 | 55–105 s | 50 s | Mesmo padrão do Verso 1 + Gsus-G final |
| Refrão 1 | 105–163 s | 58 s | C-C2 / Csus-C / Am-Asus / F/A-Am / F-G / F/A-Am / Gsus-F / F-Fm6-C/G-G |
| Interlude | 163–183 s | 20 s | F-G-F/A-C/E (×2) |
| Bridge 1 | 183–213 s | 30 s | F-G / F/A-C/E (×4) |
| Bridge 2 | 213–247 s | 34 s | G/B-C-C/E-F-G / F/A-C/E / F-G / F/A-G/B / C-Dm7-C/E / F-Fm6 |
| Half-Chorus | 247–267 s | 20 s | C(no3)×2 / Am-Asus / F/A-Am / F-G / … / Dm7 |

A cifra corresponde bem à gravação. Não foram identificadas seções adicionais ou omitidas em relação à cifra fornecida. Não foi identificada modulação de tonalidade — toda a música permanece em C major.

---

## 7. Notas Técnicas

- **Método:** STFT manual (hop=0.5s, win=2s, 48kHz→22050Hz), 531 frames
- **Qualidade vs. produção:** Inferior ao CQT da produção (librosa). Acordes com baixo específico não são diretamente detectados pelo chromagrama — inferidos pelo contexto e cifra.
- **Cobertura:** 99.3% — acima do limiar de 90% dos critérios de Tarefa.
- **Alta certeza:** 70.0% — acima do limiar de 60%.
- **Acordes suspensus:** Csus e Gsus frequentemente aparecem como Csus4/Fsus2 equivalentes no chromagrama. A decisão entre eles segue a cifra de referência.
- **C(no3):** Detectado corretamente como C5 (sem terça) no chromagrama do Half-Chorus.
- **Dm7:** Detectado diretamente como Dm7 no chromagrama com score alto (1.00+).
- **Fm6:** Duração muito curta (~2s); qualidade min6 inferida.
