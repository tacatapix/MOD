# Economia DayZ

Aplicativo desktop Windows que replica 100% das macros do arquivo
`Economia_16.01.2023.xlsm`. Portado para Python + Tkinter para rodar
nativamente em Windows **sem depender do Excel**.

## O que ele faz

Gera automaticamente, a partir dos dados da planilha embutida
(`resources/Economia.xlsm`):

| Macro (botão na interface) | Saída |
|---|---|
| `GERARTYPES` | `types.xml` (mais de 1.5 MB) |
| `TRATAMENTOTYPES` | lista `CLASS,` para usar em loot tables |
| `IDENTIFICAÇÃOMOD` | marca mod de cada item em `ListaritensMOD` |
| `GERARTRADERCONFIG` | `TraderConfig.txt` (Dr. Jones / Expansion) |
| `GERARTRADEROBJECTS` | `TraderObjects.txt` |
| `SPAWNABLETYPES` | `cfgspawnabletypes.xml` |
| `TP_General`, `TP_IDs`, `TP_Price` | Configurações TraderPlus (JSON) |
| `SORTEIO` / `CATEGORIASORTEIO` | Sorteio de itens para eventos |
| `EVENTO_CJ187`, `EVENTO_AIRDROP`, `EVENTO_TREASURE`, `EVENTO_KOTH` | Configuração dos eventos |
| `ARMASDUPLICADAS` | Marca armas duplicadas na listagem |

Cada ação **grava o arquivo em `Saida\`** (ao lado do executável) e
**copia o conteúdo para a área de transferência** — exatamente como a
planilha original fazia.

## Instalação (Windows)

Baixe o instalador e dê duplo clique:

```
packaging/EconomiaApp-Setup.exe   (31 MB)
```

O instalador coloca o app em
`%LOCALAPPDATA%\Programs\EconomiaApp` (não pede admin), cria atalhos
no Menu Iniciar e na Área de Trabalho, e traz um desinstalador
normal do Windows.

## Executar do fonte (desenvolvedores)

```powershell
pip install -r EconomiaApp\requirements.txt
python EconomiaApp\EconomiaApp.py
```

A planilha embutida fica em `EconomiaApp\resources\Economia.xlsm`.

## Estrutura

```
EconomiaApp/
├── src/
│   ├── workbook.py      # leitor em memória do .xlsm (openpyxl), API 1-based estilo VBA
│   ├── macros.py        # porte das 19 macros VBA
│   ├── gui.py           # interface Tkinter (réplica do UserForm1)
│   └── __main__.py
├── resources/
│   └── Economia.xlsm    # planilha embutida (workbook fonte)
├── packaging/
│   └── installer.nsi    # script NSIS do instalador Windows
├── EconomiaApp.py       # launcher Python
├── requirements.txt
└── README.md
```

## Construir o instalador do zero

Pré-requisitos: NSIS (`apt install nsis` ou `choco install nsis`) e
uma cópia do Python 3.11 portátil para Windows em
`dist/EconomiaApp/python/` (pode ser extraído de
[python-build-standalone](https://github.com/astral-sh/python-build-standalone)).

```bash
cd EconomiaApp/packaging
makensis installer.nsi
# produz EconomiaApp-Setup.exe
```
