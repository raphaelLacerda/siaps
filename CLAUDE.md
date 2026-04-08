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

## Dashboard com Metabase

### Arquitetura

```
docker-compose up -d
     │
     ├─► postgres     (banco de dados)
     │        │
     │        ▼
     ├─► flyway       (migrations)
     │        │
     │        ▼
     ├─► importer     (importa CSVs automaticamente)
     │        │
     │        ▼
     └─► metabase     (dashboard)
```

### Iniciar o ambiente

```bash
# Subir tudo (postgres → flyway → importer → metabase)
docker-compose up -d

# Os CSVs são importados automaticamente!
```

### Reimportar novos dados

Quando baixar mais CSVs, basta rodar o importer novamente:

```bash
docker-compose run --rm importer
```

O importer é **idempotente**: só importa arquivos novos ou modificados.

### Acessar o Metabase

- URL: http://localhost:3000
- Na primeira vez, configure uma conta admin
- Adicione o banco de dados:
  - Tipo: PostgreSQL
  - Host: `postgres` (ou `localhost` se acessando de fora do Docker)
  - Porta: `5432`
  - Banco: `siaps`
  - Usuário: `alyne`
  - Senha: `alyne123`

### Estrutura do banco

| Tabela/View | Descrição |
|---|---|
| `indicadores` | Dados por competência (downloads/csv) |
| `crescimento` | Evolução entre competências (reports/) |
| `import_control` | Controle de arquivos importados |
| `v_indicadores_resumo` | Resumo por indicador/competência |
| `v_evolucao_temporal` | Evolução temporal por equipe |
| `v_ranking_crescimento` | Ranking de crescimento por indicador |
| `v_equipes_em_queda` | Equipes com desempenho em queda |

### Migrations (Flyway)

As migrations ficam em `db/migrations/`:

```
db/migrations/
├── V1__create_indicadores_table.sql
├── V2__create_crescimento_table.sql
├── V3__create_views.sql
└── V4__create_import_control_table.sql
```

Para adicionar novas migrations, crie arquivos `V<N>__<descricao>.sql`.

### Parar o ambiente

```bash
docker-compose down        # para os containers
docker-compose down -v     # para e remove volumes (dados)
```

## Deploy no Render (Free Tier)

Deploy gratuito usando PostgreSQL + Metabase no Render.

### Passo 1: Criar o banco PostgreSQL

1. Acesse https://dashboard.render.com
2. Clique em **New** → **PostgreSQL**
3. Configure:
   - **Name**: `siaps-db`
   - **Database**: `siaps`
   - **User**: `alyne`
   - **Region**: escolha a mais próxima
   - **Plan**: **Free** (expira em 90 dias)
4. Clique em **Create Database**
5. Aguarde o banco ficar "Available"
6. Copie a **External Database URL**

### Passo 2: Importar dados localmente

```bash
# Exportar a URL do banco (copie do Render)
export DATABASE_URL="postgres://alyne:SENHA@HOST:5432/siaps"

# Rodar migrations + importação
pipenv run python deploy_render.py
```

### Passo 3: Criar o Metabase

1. No Render, clique em **New** → **Web Service**
2. Configure:
   - **Name**: `alyne-metabase`
   - **Region**: mesma do banco
   - **Runtime**: **Docker**
   - **Image URL**: `docker.io/metabase/metabase:latest`
   - **Plan**: **Free** (dorme após 15 min de inatividade)
3. Adicione as **Environment Variables**:
   ```
   MB_DB_TYPE=postgres
   MB_DB_HOST=<host do banco - veja no Render>
   MB_DB_PORT=5432
   MB_DB_DBNAME=siaps
   MB_DB_USER=alyne
   MB_DB_PASS=<senha do banco>
   JAVA_TIMEZONE=America/Sao_Paulo
   ```
4. Clique em **Create Web Service**

### Passo 4: Configurar o Metabase

1. Acesse a URL do seu Metabase (ex: `https://alyne-metabase.onrender.com`)
2. Crie uma conta admin
3. Adicione o banco de dados:
   - Tipo: **PostgreSQL**
   - Host: mesmo do `MB_DB_HOST`
   - Porta: `5432`
   - Database: `siaps`
   - User: `alyne`
   - Password: mesma do `MB_DB_PASS`

### Atualizar dados

Quando baixar novos CSVs:

```bash
# 1. Baixar novos dados
pipenv run python download_siaps.py

# 2. Reimportar para o Render
export DATABASE_URL="postgres://..."
pipenv run python deploy_render.py
```

### Limitações do Free Tier

| Recurso | Limitação |
|---------|-----------|
| PostgreSQL | Expira em 90 dias |
| Metabase | Dorme após 15 min, ~60s para acordar |
| Storage | 1 GB no banco |

Para uso contínuo, considere o plano **Starter** ($7/mês por serviço).
