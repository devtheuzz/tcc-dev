# Nexa Play / Nexa Quest

Site desenvolvido em **Flask**, utilizando templates Jinja, banco de dados SQLite e API REST com autenticação JWT.

O frontend e o backend funcionam no mesmo servidor, compartilhando o banco de dados.

**Requisito:** Python 3.12 ou superior.

## Instalação e execução

Na pasta principal do projeto, instale as dependências:

```bash
pip install -r requirements.txt
```

Inicie o servidor:

```bash
python app.py
```

Acesse:

http://127.0.0.1:5000

As páginas HTML devem ser acessadas pelo servidor Flask, pois utilizam templates Jinja.

O banco de dados e a chave local são criados automaticamente em `backend/instance/`.

Para configurar variáveis próprias, utilize `backend/.env.example` como referência.

**Importante:** não publique arquivos `.env`, bancos de dados ou chaves privadas.

## Estrutura do projeto

```text
NexaPlay/
├── app.py
├── requirements.txt
├── backend/
│   ├── __init__.py
│   ├── server.py
│   ├── web.py
│   ├── api.py
│   ├── auth.py
│   ├── game_api.py
│   ├── game.py
│   ├── commands.py
│   ├── database_manager.py
│   ├── database/
│   │   └── nexadb.sql
│   ├── instance/
│   ├── templates/
│   └── static/
└── docs/
    ├── documentacao_api.md
    ├── documentacao_api.pdf
    └── integracao_jogo.md
```

### Principais arquivos

| Arquivo | Função |
|---|---|
| `app.py` | Inicialização do servidor |
| `backend/server.py` | Configuração do Flask |
| `backend/web.py` | Páginas e sessões |
| `backend/api.py` | Endpoints REST |
| `backend/auth.py` | Cadastro e autenticação |
| `backend/game_api.py` | Integração com o jogo |
| `backend/game.py` | Missões, XP e conquistas |
| `backend/commands.py` | Comandos administrativos |
| `backend/database_manager.py` | Gerenciamento do SQLite |
| `backend/templates/` | Páginas HTML |
| `backend/static/` | CSS, JavaScript e imagens |
| `docs/` | Documentação do projeto |

## Funcionalidades

- Cadastro e login com senhas protegidas por hash.
- Autenticação por sessão no site e JWT na API.
- Perfil de usuário com nível, XP e conquistas.
- Ranking de jogadores.
- Jornadas, missões e desafios.
- Sincronização de progresso com o jogo.
- Modo claro e escuro.
- Formulário de contato com armazenamento no banco de dados.

## Integração com o jogo

A Nexa Play disponibiliza uma API REST para receber e consultar o progresso dos jogadores.

**Endpoint:**

```http
GET /api/jogo/progresso
POST /api/jogo/progresso
```

Os dados sincronizados incluem:

- Nível do jogador.
- XP total.
- Conquistas desbloqueadas.
- Versão do progresso.

A autenticação utiliza o token JWT da conta Nexa Play.

Cada atualização deve possuir uma versão crescente para evitar conflitos e duplicação de progresso.

### Endereço da API

**Produção:**

```text
https://nexaplay.vercel.app
```

**Desenvolvimento local:**

```text
http://127.0.0.1:5000
```

O endereço de produção pode ser utilizado caso a API esteja publicada e funcionando corretamente.

A documentação de integração está disponível em:

`docs/integracao_jogo.md`

## Banco de dados

O projeto utiliza SQLite para armazenar usuários, jornadas, missões, conquistas, progresso e mensagens de contato.

O banco é inicializado automaticamente na primeira execução.

**Atenção:** em hospedagens como a Vercel, o armazenamento local não é persistente. Para uso em produção, é necessário configurar um banco de dados persistente.

## Documentação

Os arquivos de documentação estão disponíveis na pasta `docs/`.

- `documentacao_api.md`: documentação geral.
- `documentacao_api.pdf`: documentação em PDF.
- `integracao_jogo.md`: integração do jogo com a API.

## Tecnologias

- **Backend:** Python e Flask
- **Frontend:** HTML, CSS, JavaScript e Jinja2
- **Banco de dados:** SQLite
- **Autenticação:** JWT e sessões Flask
- **API:** REST com JSON
