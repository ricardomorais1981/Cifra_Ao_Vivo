# Cifra ao Vivo v2.0

Transcrição automática de acordes e letra para música gospel brasileira e americana.

## Requisitos

- **Windows 10/11**
- **Python 3.9+** instalado com "Add Python to PATH" marcado
  → Baixe em: https://www.python.org/downloads/

## Como usar

1. Extraia a pasta `CifraAoVivo` em qualquer lugar do seu PC.
2. **Duplo-clique em `run.bat`** — o servidor inicia e o navegador abre sozinho.
3. Na tela que abrir (http://localhost:8000):
   - Preencha o título e artista (opcional, melhora a busca de letra)
   - Arraste o arquivo de áudio ou clique em "Selecionar arquivo"
   - Clique em **▶ Processar**
4. Aguarde o processamento (varia com o tamanho do arquivo).
5. A cifra aparece alinhada com a letra. Use **⬇ Baixar .txt** para salvar.

## Formatos de áudio suportados

MP3, WAV, FLAC, AAC, M4A, OGG, OPUS, WMA, WEBM, AIFF — até 500 MB.

## Ajustes disponíveis

| Ajuste | O que faz |
|---|---|
| **Transpor** | Transpõe os acordes (+/- semitons) |
| **Bemóis** | Exibe Bb em vez de A#, Eb em vez de D# etc. |
| **⬇ Baixar .txt** | Salva a cifra com o relatório de qualidade |
| **📋 Copiar** | Copia o texto para a área de transferência |

## Relatório de qualidade

Cada transcrição recebe um status:

| Status | Significado |
|---|---|
| ✓ **Aprovado** | Reconhecimento direto com boa confiança |
| ✦ **Corrigido** | Correção harmônica aplicada automaticamente |
| ⚠ **Incompleto** | Alguns trechos com incerteza — revisar manualmente |

## Estilo musical suportado

Foco em **música gospel brasileira e americana** (1980–2000):
- Progressões diatônicas e cadências plagais (IV→I)
- Dominantes secundárias preservadas (E7 em Dó maior = V7/vi)
- Linhas de baixo descendentes (C–G/B–Am–F/A)
- Acordes maj7 e add9 no I e IV grau
- Detecção de modulação nos últimos 40% da música

## Estrutura do projeto

```
CifraAoVivo/
├── run.bat                      ← Iniciar aqui
├── requirements.txt
├── shared/
│   ├── schemas/music_data.py    ← Modelos de dados
│   └── chord-library/           ← Posições de acorde
├── local_engine/
│   ├── audio/prepare.py         ← Carregamento de áudio
│   ├── recognition/engine.py    ← CQT + NNLS + Viterbi
│   ├── validation/pipeline.py   ← 2 camadas de validação
│   ├── export/txt_export.py     ← Geração do TXT
│   ├── lyrics/lrclib.py         ← Letra sincronizada (LRCLIB)
│   └── api/main.py              ← Servidor FastAPI
├── webapp/
│   ├── templates/index.html
│   └── static/css|js/
└── tests/
    ├── unit/test_pipeline.py
    └── integration/test_api.py
```

## Executar os testes

```bash
python -m pytest tests/ -v
```

## Próximos passos (uso comercial)

- Empacotar com **PyInstaller** (gera `.exe` sem precisar do Python)
- Publicar no **Microsoft Store** ou como instalador NSIS/Inno Setup
- Adicionar suporte a Whisper para transcrição offline
- Versão Android via Kivy ou BeeWare

---
Versão 2.0 · Uso pessoal · Foco: Gospel BR/EUA
