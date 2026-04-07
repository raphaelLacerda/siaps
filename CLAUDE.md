# CLAUDE.md — Instruções para o agente

## Como executar o programa

Sempre use `pipenv run` para rodar o script (o virtualenv é gerenciado pelo pipenv):

```bash
# Baixar todos os grupos de equipes do equipes_indicadores.json
pipenv run python download_siaps.py

# Baixar equipes específicas (separadas por espaço)
pipenv run python download_siaps.py eMulti
pipenv run python download_siaps.py eMulti eCR eSB

# Baixar um grupo combinado (eAP e eSF são um único grupo no JSON)
pipenv run python download_siaps.py eAP&eSF

# Misto: grupo combinado + equipes individuais
pipenv run python download_siaps.py eAP&eSF eMulti eCR
```

## Dependências

```bash
pipenv install        # instala tudo do Pipfile
pyenv global 3.11.4   # se "pipenv: command not found"
```

## Arquivos importantes

| Arquivo | Finalidade |
|---|---|
| `download_siaps.py` | Script principal |
| `equipes_indicadores.json` | Configura competências, grupos de equipes e indicadores |
| `.env` | Token de autenticação (`bearer_token=Bearer <token>`) |
| `downloads/csv/` | CSVs gerados |
| `downloads/xlsx/` | XLSXs gerados (requer openpyxl) |

## Estrutura do equipes_indicadores.json

```json
{
  "competencias": ["2025-04", "2025-08", "2025-12"],
  "equipes": [
    {
      "sgEquipes": ["eAP", "eSF"],
      "indicadores": [
        { "nome": "maisAcesso", "codigo": 110 }
      ]
    }
  ]
}
```

- **`competencias`**: lista de meses a baixar (formato `YYYY-MM`)
- **`sgEquipes`**: siglas do grupo — quando há mais de uma, são enviadas juntas na mesma requisição
- **`indicadores`**: lista de indicadores daquele grupo, com nome e código da API

## Lógica de filtragem de equipes (argumento via CLI)

- Argumento simples (`eMulti`) → seleciona grupos onde `sgEquipes` contém `eMulti`
- Argumento com `&` (`eAP&eSF`) → seleciona grupos onde `sgEquipes` contém **ambas** `eAP` e `eSF`
- Múltiplos argumentos → une os resultados (OR entre os argumentos)

## Nome dos arquivos gerados

Padrão: `<equipes>-<indicador-slug>-<YYYY-MM>-relatorio-competencia.csv`

Exemplo: `eAP-eSF-prevencao-do-cancer-2025-12-relatorio-competencia.csv`

## Município fixo

O script usa `coMunicipioIbge=530010` (Brasília/DF). Para mudar, edite as funções
`get_total_records` e `fetch_data` em `download_siaps.py`.
