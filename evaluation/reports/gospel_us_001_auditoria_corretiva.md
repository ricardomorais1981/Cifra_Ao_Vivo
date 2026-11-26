# Auditoria Corretiva — gospel_us_001

**I Thank You for the Cross** | Colby Wedgeworth, Tauren Wells, Jonathan Smith  
Auditoria executada em: 2026-11-18  
Arquivo auditado: `evaluation/reference/annotations/gospel_us_001.json`  
Backup preservado: `gospel_us_001.json.bak_20261119_000404`

---

## 1. Escopo e Método

Esta auditoria examinou o JSON de anotação de `gospel_us_001` contra os critérios:

- Consistência entre `annotator_notes` e os eventos efetivamente anotados
- Integridade da distinção entre detecção e inferência
- Adequação da representação de acordes especiais
- Coerência das observações internas (campo `notes` de cada evento)
- Validade dos níveis de certeza e dos limiares declarados

**O motor de reconhecimento, o schema de avaliação e as outras músicas do benchmark não foram alterados.**

---

## 2. Problemas Encontrados e Correções Aplicadas

### 2.1 Limites de Seção no `annotator_notes` — CORRIGIDO

| Seção | Declarado (original) | Baseado nos eventos |
|---|---|---|
| Verso 1 | 7–55 s | 7–51 s |
| Verso 2 | 55–105 s | 51–105 s |
| Refrão 1 | 105–152 s | 105–163 s |
| Interlude | 152–172 s | 163–183,5 s |
| Bridge 1 | 172–212 s | 183,5–213 s |
| Bridge 2 | 212–247 s | 213–247,5 s |
| Half-Chorus | 247–267 s | 247,5–266,5 s |

**Evidência:** o primeiro evento marcado como "Verso 2" começa em 51,0 s (não 55 s); o primeiro evento "Interlude" começa em 163,0 s; o primeiro evento "Bridge 1" em 183,5 s; "Bridge 2" em 213,0 s; "Half-Chorus" em 247,5 s. O último evento termina em 266,5 s.

**Correção:** `annotator_notes` atualizado para refletir os limites reais dos eventos.

**Nota:** os eventos em si não foram alterados — apenas a descrição textual do `annotator_notes` foi corrigida para coincidir com eles.

---

### 2.2 Limiares de Certeza no `annotator_notes` — CORRIGIDO

**Problema:** o `annotator_notes` original declarava:
> "Certeza: alta = score>0.17 consistente com tonalidade; media = score 0.12–0.17 ou ambiguidade; baixa = score<0.12 ou transicao."

Os scores reais observados nos eventos variam de 0,73 a 1,39. Os limiares 0,17/0,12 são numericamente incompatíveis com a escala dos scores citados.

**Análise:** os scores são produtos internos normalizados (dot product de chromagrama vs. template), não probabilidades nem frações de 0 a 1. A escala real é aproximadamente 0,7–1,4 para matches válidos. Os limiares foram escritos erroneamente no `annotator_notes`.

**Correção:** os limiares numéricos foram removidos. O `annotator_notes` agora declara explicitamente que a certeza é uma **classificação qualitativa não calibrada**, baseada em:
- dominância do acorde no frame
- coerência com a tonalidade C major
- ausência ou presença de ambiguidade entre candidatos
- duração do acorde

**Os níveis de certeza dos eventos individuais não foram alterados**, pois os critérios qualitativos que os embasaram permanecem válidos mesmo com a correção dos limiares textuais.

---

### 2.3 Declaração de Inferência do Baixo — CORRIGIDO

**Problema fundamental:** o `annotator_notes` original afirmava "Inversoes identificadas pelo contexto harmonico e confirmadas pelo bass note" — o que implica detecção direta do baixo. Esta afirmação é incorreta.

**Fato técnico:** o chromagrama STFT integra toda a energia harmônica do sinal. Ele não separa grave do agudo. Nenhuma nota de baixo foi detectada diretamente no sinal para nenhum dos 21 eventos com `bass`.

**Classificação de todos os 21 eventos com `bass`:**

| Acorde | Ocorrências | Fonte real do baixo |
|---|---|---|
| G/B | 4 | Inferido: cifra + contexto harmônico (passagem G/B entre Am e C) |
| F/A | 10 | Inferido: cifra. A é componente da tríade Fadd9 — confirma o acorde, não o baixo |
| C/E | 6 | Inferido: cifra + contexto harmônico |
| C/G | 1 | Inferido: cifra + contexto ("Bass G inferido do contexto" — já declarado) |

**Correção no `annotator_notes`:** a frase foi substituída por declaração explícita de que todas as notas de baixo são inferências.

**Correção em eventos individuais com linguagem enganosa:**

- **27,0 s (F/A):** "confirmado pelo bass A" → corrigido para explicitar que A é componente da tríade Fadd9, não evidência do baixo. Baixo inferido da cifra.
- **64,5 s (G/B):** "Contexto harmonico G/B confirmado" → clarificado: B é a 3ª de G, não detectável separadamente; G/B inferido da cifra.
- **141,5 s (F/A):** "F area confirmada com bass A" → corrigido: A aparece em Fadd9 e Dm7; não confirma o baixo. Baixo inferido da cifra.

---

### 2.4 Evento 210,5–213,0 s — Observação Contraditória — CORRIGIDO

**Problema:** `root=G, quality=maj` mas `notes` dizia "F/A bridge 1 fecha (cifra: F/A — sem resolucao final no Bridge 1)". A menção de "F/A" numa observação de um evento G é ambígua e pode ser lida como contradição.

**Análise:** a cifra do Bridge 1 termina com F/A mas o chromagrama detectou G (resolução de cadência). O texto pretendia registrar essa divergência, mas o fez de forma ambígua.

**Correção:** `notes` reescrito para explicitar a divergência: "G de resolucao — Bridge 1 fecha aqui (cifra nesta posicao: F/A, mas chromagrama detecta G). Score G dominante. Incerteza: pode ser F/A nao resolvido ou G de cadencia."

---

### 2.5 Evento 213,0–216,5 s (G/B) — Ambiguidade Cromática — CORRIGIDO

**Problema:** `notes` dizia "Score Csus2 dominante, G/B inferido do contexto e cifra" sem explicar a relação entre Csus2 e G/B.

**Análise:** Csus2 = {C, D, G}; G/B = {G, B, D}. Ambos compartilham G e D. O chromagrama não distingue entre eles. A annotação é G/B exclusivamente por inferência da cifra.

**Correção:** `notes` expandido para tornar explícita a ambiguidade cromática e a dependência total da cifra.

---

### 2.6 Eventos com Notas Vazias — CORRIGIDO

**Problema:** quatro eventos tinham `notes` com apenas o nome do acorde sem rastreabilidade:
- 179,5 s (F/A): `"F/A."` → sem justificativa
- 181,5 s (C/E): `"C/E."` → sem justificativa
- 201,5 s (F/A): `"F/A."` → sem justificativa
- 204,5 s (C/E): `"C/E."` → sem justificativa

**Correção:** adicionada rastreabilidade mínima — referência à cifra e à analogia com o evento correspondente do mesmo padrão.

---

## 3. Problemas Identificados Sem Correção (Limitações Preservadas)

### 3.1 Campo `bass_source` Não Existe no Schema

**Problema:** o schema atual não possui campo para diferenciar `detected` / `inferred` / `unknown` para a nota de baixo. A auditoria demonstrou que **todos os 21 eventos com `bass` têm baixo inferido**, não detectado.

**Decisão:** o schema não foi alterado (critério da tarefa: "Não modifique o schema geral de avaliação"). A limitação foi registrada nos `annotator_notes` e nas `notes` dos eventos corrigidos.

**Recomendação para versão futura:** adicionar campo `bass_source` ao schema com valores `"inferred"`, `"detected"` e `"unknown"`.

---

### 3.2 Fm6 Representado como `quality: "min"` — Limitação de Schema

**Problema:** Fm6 (F–A♭–C–D) é representado como `quality: "min"` (Fm = F–A♭–C). A sexta (D) é perdida.

**Fato:** o schema não possui `quality: "min6"`. A representação `"min"` é a melhor aproximação disponível.

**Rastreabilidade:** os dois eventos Fm6 (155,0 s e 246,0 s) têm `notes` indicando "Fm6 (cifra: F-Fm6)". A informação original está preservada textualmente.

**Decisão:** nenhuma correção ao campo `quality` — mudá-lo para um valor inexistente no schema introduziria inconsistência maior. A limitação é registrada aqui.

---

### 3.3 Acordes Suspensos — Resolução Dependente da Cifra

**Fato técnico:** Csus4 e Fsus2 têm espectro cromático idêntico {C, F, G}. Gsus4 e Dsus2 têm espectro idêntico {G, C, D}. Asus4 e Esus2 têm espectro idêntico {A, D, E}.

O chromagrama por si só não pode distinguir entre essas alternativas. **Todos os 9 acordes suspensos foram resolvidos pela cifra de referência**, não pela análise do sinal.

**Decisão:** os eventos não foram alterados — a certeza `medium` já reflete essa ambiguidade. A limitação está agora documentada no `annotator_notes`.

---

### 3.4 C(no3) como `quality: "5"` — Aproximação Funcional

**Fato:** C(no3) = C sem terça. No contexto desta música (gospel pop), é funcionalmente equivalente a C5 (power chord C–G). O chromagrama confirma ausência de terça definida. A representação `quality: "5"` captura esse comportamento.

**Limitação residual:** se C(no3) incluísse extensões (sétima, etc.), `quality: "5"` seria insuficiente. No contexto observado, não há evidência de extensões.

**Decisão:** sem alteração. As `notes` já explicam a equivalência.

---

### 3.5 Certeza — Classificação Não Calibrada

**Declaração explícita:** os níveis `high`, `medium` e `low` são classificações qualitativas do anotador. Não foram calibrados contra um conjunto de validação. Não representam probabilidades. Os scores citados nos `notes` são produtos internos (dot product) de chromagrama normalizado vs. template de acorde, com escala aproximada de 0,7 a 1,4 para matches válidos.

**Consequência:** esses níveis não podem ser usados como probabilidades em cálculos estatísticos sem calibração prévia.

---

## 4. Lista de Eventos que Precisam de Confirmação Auditiva Adicional

| # | Evento | Problema |
|---|---|---|
| 1 | 20,0–23,0 s (G/B) | B não evidenciado no chromagrama; G/B só por cifra + contexto |
| 2 | 33,5–37,0 s (Gsus) | Csus4 e Fsus2 indistinguíveis; Gsus só pela cifra |
| 3 | 97,0–101,5 s (Gsus) | Dsus2/Asus4 indicando área G — Gsus pela cifra |
| 4 | 112,0–115,5 s (Csus) | D7/Dm7 transitório no mesmo frame; certeza media |
| 5 | 123,0–126,5 s (Asus) | Dsus2/Asus4 equivalentes; Asus pela cifra |
| 6 | 149,0–152,5 s (Gsus) | Csus4 frame; Gsus pela cifra |
| 7 | 152,5–155,0 s (F, low) | Score baixo; transição para Fm6; certeza baixa |
| 8 | 155,0–157,5 s (Fm) | Duração ~2,5 s próxima à janela; Fm6 não confirma sexta |
| 9 | 157,5–160,5 s (C/G) | Bass G inferido do contexto; C/G ou G próximos harmonicamente |
| 10 | 210,5–213,0 s (G) | Cifra diz F/A; chromagrama detecta G — divergência sem resolução auditiva |
| 11 | 213,0–216,5 s (G/B) | Score Csus2; G/B só pela cifra |
| 12 | 237,5–240,5 s (G/B) | "Bass B inferido" — sem evidência cromática direta |
| 13 | 247,5–251,0 s (C5) | C(no3) — ausência de terça confirmada, mas extensões não verificadas |
| 14 | 257,0–259,5 s (Asus) | Esus4/Asus2 dominante; Asus4 pela cifra |

---

## 5. Declaração Explícita: Detectado vs. Inferido

### 5.1 Detectado pelo chromagrama

As seguintes propriedades foram identificadas diretamente no sinal:

- **Raiz (root)** de todos os 81 eventos — pelo score mais alto do template de acorde no frame
- **Qualidade do acorde (quality)** para todos os eventos com certeza `high` ou `medium`
- **Dm7** (243,5 s e 264,0 s): detectado com score alto (1,00+ e 1,26) — a qualidade `min7` é confirmada pelo chromagrama
- **C5/C(no3)** (247,5 s e 251,0 s): ausência de terça detectada (score C5 dominante sem template de tríade completo)
- **Área Fm** (155,0 s): detecção do acorde menor de F confirmada pelo score Fmin
- **Ausência de nota de baixo específico**: nenhum baixo foi detectado diretamente

### 5.2 Inferido da cifra ou contexto harmônico

As seguintes propriedades foram **inferidas**, não detectadas:

- **Todas as 21 notas de baixo** (`bass` e `inversion`) — inferidas da cifra de referência; a nota de baixo é componente das tríades ou é coerente com o contexto, mas não é separável pelo chromagrama STFT
- **Todos os 9 acordes suspensos** (Csus, Gsus, Asus) — a raiz foi inferida da cifra, pois os equivalentes sus4/sus2 são cromáticamente indistinguíveis
- **Fm6 como qualidade** — a sexta (D) foi inferida da cifra; o chromagrama confirmou apenas a área Fm (min)
- **G/B em 213,0 s** — inferido exclusivamente da cifra; evidência cromática (Csus2) é ambígua

### 5.3 Ambíguo (evidência insuficiente para classificar)

- **210,5 s (G vs. F/A):** o chromagrama detecta G mas a cifra indica F/A — divergência sem resolução auditiva disponível

---

## 6. Status de Aprovação como Ground Truth

**Esta música NÃO é declarada aprovada como ground truth definitivo.**

Critérios atendidos:
- ✓ Cobertura: 99,3% (acima do limiar de 90%)
- ✓ Alta certeza: 70,0% (acima do limiar de 60%)
- ✓ 81 eventos com rastreabilidade de scores
- ✓ Incertezas preservadas nos campos de certeza
- ✓ Inconsistências corrigidas ou documentadas

Critérios pendentes de verificação independente:
- ✗ 14 eventos necessitam de confirmação auditiva (ver seção 4)
- ✗ Todas as 21 notas de baixo são inferências — requerem rastreamento de grave separado para confirmação
- ✗ 9 acordes suspensos resolvidos exclusivamente pela cifra — sem evidência acústica direta
- ✗ Divergência 210,5 s (G vs. F/A) não resolvida

**Recomendação:** utilizar como referência de desenvolvimento (split=`dev`) com as incertezas documentadas. Não utilizar os eventos de baixo como ground truth para avaliação de rastreamento de grave sem verificação adicional.

---

## 7. Resumo das Alterações ao JSON

| Campo | Tipo de alteração |
|---|---|
| `annotator_notes` | Corrigidos limites de seção, limiares de score e declaração de inferência do baixo |
| `events[27.0].notes` | Removida afirmação enganosa "confirmado pelo bass A" |
| `events[64.5].notes` | Clarificado: G/B inferido, não confirmado cromáticamente |
| `events[141.5].notes` | Removida afirmação enganosa "F area confirmada com bass A" |
| `events[179.5].notes` | Adicionada rastreabilidade mínima (era praticamente vazio) |
| `events[181.5].notes` | Adicionada rastreabilidade mínima |
| `events[201.5].notes` | Adicionada rastreabilidade mínima |
| `events[204.5].notes` | Adicionada rastreabilidade mínima |
| `events[210.5].notes` | Corrigida contradição root=G vs. texto "F/A" |
| `events[213.0].notes` | Expandida explicação da ambiguidade Csus2 vs. G/B |
| `events[232.0].notes` | Adicionada rastreabilidade mínima |

**Não alterados:** `root`, `quality`, `bass`, `inversion`, `start`, `end`, `certainty` de nenhum evento. Nenhuma propriedade musical foi modificada — apenas as observações textuais e os metadados descritivos.
