# SIAPS — Download de Relatórios por Competência

Script para baixar dados do SIAPS (Visão por Competência) e gerar arquivos CSV e XLSX a partir
das configurações definidas em `equipes_indicadores.json`.

## O que o programa faz

- Lê `equipes_indicadores.json` (lista de competências e grupos de equipes + indicadores).
- Para cada combinação competência × indicador × grupo de equipes, faz chamadas à API do SIAPS
	e baixa os registros disponíveis.
- Gera arquivos CSV em `downloads/csv/` e, se o pacote `openpyxl` estiver instalado, gera também
	arquivos XLSX em `downloads/xlsx/`.

## Requisitos

- Python 3.8+
- Biblioteca `requests` (obrigatória)
- Biblioteca `openpyxl` (opcional — gera arquivos `.xlsx`)

Instale dependências via pip, por exemplo:

```bash
pip install requests openpyxl
```

## Configuração

- Token de autorização: crie um arquivo `.env` na raiz do projeto com a variável `bearer_token`:

```
bearer_token=Bearer <seu_token_aqui>
```

- Arquivo de configuração: `equipes_indicadores.json` — formato esperado:

```json
{
	"competencias": ["2025-04", "2025-08", "2025-12"],
	"equipes": [
		{
			"sgEquipes": ["eAP", "eSF"],
			"indicadores": [ {"nome": "maisAcesso", "codigo": 110}, ... ]
		},
		{
			"sgEquipes": ["eSB"],
			"indicadores": [ {"nome": "1ª Consulta Odontológica", "codigo": 111}, ... ]
		}
	]
}
```

- Observações importantes:
	- O script atualmente usa `coMunicipioIbge=530010` (Brasília). Altere no código se quiser outro município.
	- Os slugs dos indicadores são mapeados no dicionário `INDICADOR_SLUGS` em `download_siaps.py`.

## Uso

Instale as dependências com pipenv:

```bash
pipenv install
```

**Baixar todos os grupos de equipes:**

```bash
pipenv run python download_siaps.py
```

**Baixar equipes específicas (separadas por espaço):**

```bash
pipenv run python download_siaps.py eMulti
pipenv run python download_siaps.py eMulti eCR
pipenv run python download_siaps.py eSB eAPP
```

**Baixar um grupo de equipes combinadas (ligadas por `&`):**

Use `&` para referenciar um grupo que contenha *ambas* as equipes juntas no JSON:

```bash
pipenv run python download_siaps.py eAP&eSF
```

Combinações mistas também são suportadas:

```bash
pipenv run python download_siaps.py eAP&eSF eMulti eCR
```

Saída padrão na execução mostra progresso e mensagens de erro HTTP quando ocorrem.

## Saída

- CSVs: `downloads/csv/` — cada arquivo contém um cabeçalho descritivo seguido por colunas separadas
	por ponto-e-vírgula. O encode usado é `utf-8-sig` para compatibilidade com Excel.
- XLSX: `downloads/xlsx/` — gerado apenas se `openpyxl` estiver instalado.

## Estrutura dos CSVs

- Colunas principais:
	- `CNES`, `ESTABELECIMENTO`, `TIPO DO ESTABELECIMENTO`, `INE`, `NOME DA EQUIPE`, `SIGLA DA EQUIPE`,
		`NÚMERO TOTAL DE ATENDIMENTOS POR DEMANDA PROGRAMADA`, `NÚMERO TOTAL DE ATENDIMENTOS POR TODOS OS TIPOS DE DEMANDAS (ESPONTÂNEAS E PROGRAMADAS)`, `PONTUAÇÃO`.

## Notas e sugestões

- Para adicionar/alterar equipes ou indicadores, edite `equipes_indicadores.json` seguindo o exemplo.
- Para mudar o município alvo, atualize `coMunicipioIbge` nas funções `get_total_records` e `fetch_data`.
- Se desejar gerar apenas um indicador/competência, considerar adicionar parâmetros de linha de comando (melhoria futura).

---

Arquivo de configuração: `equipes_indicadores.json` — edite conforme necessário.

Relatórios gerados em `downloads/csv` e `downloads/xlsx`.

