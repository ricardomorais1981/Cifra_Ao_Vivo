# Como adicionar uma nova música à coleção de referência

Este documento descreve o procedimento completo para adicionar uma música à
coleção de avaliação do motor Cifra ao Vivo v2.0.

---

## 1. Visão geral da estrutura

```
evaluation/
  reference/
    annotations/       <- Um arquivo JSON por música (a "verdade")
    audio/             <- Arquivos de áudio (MP3 ou WAV), não versionados no git
  COMO_ADICIONAR.md    <- Este arquivo
  collection_manifest.json  <- Índice da coleção
```

---

## 2. Decidir o split da música

| Split  | Quando usar | Restrição |
|--------|-------------|-----------|
| `dev`  | Músicas usadas para desenvolver e calibrar o motor | Nenhuma |
| `test` | Músicas reservadas para avaliação final independente | **Nunca** usar para ajuste de parâmetros |

> **Regra de ouro:** Se você usou a música para decidir qualquer parâmetro
> do motor, ela pertence ao split `dev`. Músicas `test` só devem ser
> consultadas quando o desenvolvimento de uma fase estiver completo.

**Distribuição alvo da coleção:**
- Dev: ~80% das músicas
- Test: ~20%, variadas em estilo e dificuldade

---

## 3. Escolher o ID da música

O ID deve ser único e seguir o padrão:

```
<estilo>_<número_três_dígitos>
```

Exemplos:
- `gospel_br_006`  — 6ª música gospel brasileiro
- `pop_int_003`    — 3ª música pop internacional
- `acoustic_002`  — 2ª música acústica solo

Estilos disponíveis:
- `gospel_br` — Gospel/Worship em português (Brasil)
- `gospel_us` — Gospel/Worship em inglês (EUA)
- `pop_br`    — MPB e pop brasileiro
- `pop_int`   — Pop internacional
- `acoustic`  — Violão/guitarra solo ou minimalista
- `rock`      — Rock (pop-rock, rock clássico)
- `jazz`      — Jazz (reservado para fase futura)

---

## 4. Adicionar o arquivo de áudio

1. Copie o arquivo MP3 ou WAV para `evaluation/reference/audio/`
2. Nomeie-o como `<id>.mp3` (ou `.wav`)
3. Qualidade mínima: 128 kbps MP3 ou 44 kHz WAV
4. **Não versionar áudio no git** — arquivos de áudio ficam apenas localmente

---

## 5. Criar o esqueleto de anotação

Crie `evaluation/reference/annotations/<id>.json` com este template:

```json
{
  "id": "<id>",
  "title": "<título completo>",
  "artist": "<intérprete principal>",
  "duration": 0.0,
  "key": "<tonalidade, ex: G major ou A minor>",
  "bpm": null,
  "time_signature": "4/4",
  "split": "<dev ou test>",
  "style": "<estilo>",
  "difficulty": "<easy | medium | hard>",
  "audio_file": "<id>.mp3",
  "source_url": "<URL da cifra de referência, se houver>",
  "annotator_notes": "AGUARDANDO ANOTAÇÃO.",
  "events": []
}
```

**Critérios de dificuldade:**

| Nível    | Características típicas |
|----------|------------------------|
| `easy`   | Tríades simples I-IV-V, sem inversões, sem cromatismo |
| `medium` | Acordes com 7ª, dominantes secundárias ocasionais |
| `hard`   | Inversões frequentes, modulações, cromatismo, vocabulário estendido |

---

## 6. Preencher os eventos de acorde

Este é o passo mais importante e mais trabalhoso. Use um editor de áudio
com visualização de forma de onda (Audacity, musescore, etc.) para
identificar os tempos de mudança de acorde.

### 6.1. Formato de um evento

```json
{
  "start": 4.21,
  "end": 6.03,
  "root": "G",
  "quality": "maj",
  "bass": null,
  "inversion": null,
  "certainty": "high",
  "notes": ""
}
```

**Campos de acorde:**

| Campo      | Valores possíveis |
|------------|-------------------|
| `root`     | C, C#, Db, D, D#, Eb, E, F, F#, Gb, G, G#, Ab, A, A#, Bb, B |
| `quality`  | `maj`, `min`, `7`, `maj7`, `min7`, `dim`, `dim7`, `aug`, `sus2`, `sus4`, `m7b5`, `add9`, `6`, `m6` |
| `bass`     | Nota do baixo se diferente da fundamental. `null` = posição fundamental |
| `inversion`| `"1st"`, `"2nd"`, `"3rd"` ou `null` |
| `certainty`| `"high"` (certo), `"medium"` (provável), `"low"` (ambíguo) |
| `notes`    | Texto livre sobre ambiguidades ou observações |

### 6.2. Regras de anotação

1. **Evidência acústica primeiro.** O que você *ouve* importa mais do que
   o que a teoria prevê. Se soa como menor, anote como menor.

2. **Apenas certeza `high` conta para as métricas principais.** Use
   `medium` para transições rápidas ou passagens ambíguas. Use `low`
   para seções onde não consegue determinar com confiança.

3. **Inversões somente com evidência clara.** Se o baixo está no primeiro
   grau, deixe `bass: null`. Só preencha `bass` quando a nota de baixo
   é audível e diferente da fundamental.

4. **Tempos em segundos com duas casas decimais.** Os eventos devem ser
   contíguos: `end` de um evento = `start` do próximo.

5. **Cobrir pelo menos 70% da música.** Seções instrumentais sem harmonia
   clara podem ser omitidas, mas refrões e versos devem estar cobertos.

### 6.3. Exemplo de progressão gospel I-IV-V-I em G

```json
"events": [
  {"start": 0.00, "end": 4.20, "root": "G", "quality": "maj",
   "certainty": "high", "notes": "Intro"},
  {"start": 4.20, "end": 8.40, "root": "C", "quality": "maj",
   "certainty": "high", "notes": ""},
  {"start": 8.40, "end": 12.60, "root": "D", "quality": "7",
   "certainty": "high", "notes": ""},
  {"start": 12.60, "end": 16.80, "root": "G", "quality": "maj",
   "certainty": "high", "notes": ""},
  {"start": 16.80, "end": 20.10, "root": "E", "quality": "min",
   "certainty": "medium", "notes": "Passagem rápida, pode ser E7"}
]
```

---

## 7. Atualizar a duração real

Após preencher os eventos, atualize o campo `duration` com a duração
real do arquivo de áudio em segundos.

Você pode obter a duração com:
```bash
python3 -c "import librosa; y, sr = librosa.load('audio/<id>.mp3', sr=None); print(librosa.get_duration(y=y, sr=sr))"
```

---

## 8. Atualizar o manifesto

Edite `evaluation/reference/collection_manifest.json`:

1. Adicione a música ao array `songs`
2. Atualize `statistics.total`
3. Atualize `statistics.by_split`, `by_style`, `by_difficulty`
4. Se adicionou áudio: `statistics.with_audio += 1` e `has_audio: true`
5. Se adicionou eventos: `statistics.with_annotations += 1`

---

## 9. Verificar com o validador

```bash
cd /caminho/para/CifraAoVivo_fase1
python3 -c "
from evaluation.schemas.annotation import ReferenceAnnotation
ref = ReferenceAnnotation.load('evaluation/reference/annotations/<id>.json')
print(f'Carregado: {ref.title}')
print(f'Eventos: {len(ref.events)}')
print(f'Alta certeza: {len(ref.high_certainty_events())}')
print(f'Duração coberta: {sum(e.duration for e in ref.events):.1f}s de {ref.duration:.1f}s')
"
```

---

## 10. Testar a avaliação (somente se tiver áudio)

```bash
cd /caminho/para/CifraAoVivo_fase1
python3 -m evaluation.evaluator --id <id>
```

O resultado será salvo em `evaluation/reports/<id>.json`.

---

## Checklist rápido

- [ ] ID único escolhido e seguindo o padrão
- [ ] Split decidido corretamente (dev ou test)
- [ ] Arquivo JSON criado em `annotations/`
- [ ] Áudio copiado para `audio/` (se disponível)
- [ ] Eventos de acorde preenchidos (mínimo: refrão e versos)
- [ ] Campo `duration` atualizado com valor real
- [ ] Manifesto atualizado
- [ ] Validador executado sem erros
