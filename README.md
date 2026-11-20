# Nexa Play / Nexa Quest

Site em Flask com templates Jinja, SQLite e API REST com JWT. As páginas e a API usam o mesmo servidor e o mesmo banco. Python 3.12 ou superior.

## Rodar

Na pasta do projeto, execute:

```bash
python -m venv .venv
```

Ative o ambiente no Linux/macOS:

```bash
source .venv/bin/activate
```

No Fish: `source .venv/bin/activate.fish`.

No Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

Instale e inicie:

```bash
python -m pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:5000. Não abra os HTMLs diretamente: eles precisam ser renderizados pelo Flask. Também funcionam `python backend/main.py` e `python -m flask --app app run`.

O banco e uma chave local são criados automaticamente em `backend/instance/`. Para usar variáveis próprias, copie `backend/.env.example` para `backend/.env`. Não publique `.env`, bancos ou chaves.

## Estrutura

| Caminho | Responsabilidade |
|---|---|
| `app.py` | Entrada do servidor e aplicação WSGI |
| `backend/server.py` | Fábrica `create_app`, configuração e registro de rotas |
| `backend/web.py` | Páginas, formulários, sessão e proteção CSRF |
| `backend/api.py` | Endpoints JSON com autenticação JWT |
| `backend/auth.py` | Validação, cadastro e verificação de senha |
| `backend/game_api.py` | Mini API de sincronização do jogo |
| `backend/game.py` | Missões, desafios, pontos e conquistas |
| `backend/commands.py` | Comandos locais para criar administrador e dados de exemplo |
| `backend/database_manager.py` | Acesso ao SQLite e migração |
| `backend/database/nexadb.sql` | Tabelas, índices, níveis e conquistas iniciais |
| `backend/templates/` | HTML com Jinja e layout compartilhado |
| `backend/static/` | CSS, JavaScript, imagens, fontes e licença |
| `docs/documentacao_api.md` | Guia completo de execução e integração |
| `docs/documentacao_api.pdf` | Versão em PDF do guia |
| `tests/test_app.py` | Testes de integração |

A antiga pasta `frontend/` foi incorporada ao pacote Flask. Os recursos usam `url_for('static', filename=...)`, e os links usam `url_for('web.nome_da_rota')`.

## Experimentar o jogo

O banco começa sem usuários e sem jornadas. Para adicionar uma jornada de exemplo:

```bash
python -m flask --app app seed-demo
```

Crie sua conta pelo site, abra **Explorar**, entre na jornada e inicie a missão. Responda `print` ao desafio e conclua a missão. O fluxo concede 100 XP no total e desbloqueia duas conquistas. Repetir a conclusão não concede pontos extras.

Para criar um administrador, execute o comando e preencha os campos solicitados:

```bash
python -m flask --app app create-admin
```

A administração dos conteúdos é feita pela API. Não há painel administrativo visual.

## Testar

```bash
python -m unittest discover -s tests -v
```

Os testes usam bancos temporários, sem modificar os dados do site.

## Integração com o jogo

O jogo pode consultar e enviar nível, XP total e conquistas em `GET` e `POST /api/jogo/progresso`, usando o JWT da própria conta. Cada novo envio tem uma `versao` crescente. Envios idênticos podem ser repetidos sem duplicar XP.

O guia para o desenvolvedor do jogo está em [docs/integracao_jogo.md](docs/integracao_jogo.md), com o formato JSON, autenticação, tratamento de erros e exemplos de JavaScript e cURL.

Após a primeira sincronização, o painel e o ranking passam a exibir o estado enviado pelo jogo. As missões locais continuam salvas separadamente. Atualize a página do site para ver o último envio.

## Recursos e limites

- Cadastro e login reais com senha armazenada como hash.
- Site autenticado por cookie de sessão; API autenticada por Bearer JWT.
- Perfil, progresso, XP e conquistas lidos do SQLite.
- Modo escuro com cores separadas para fundo, texto e campos.
- Login e cadastro com ilustração proporcional, sem sobrepor o texto.
- Formulário de contato grava em `mensagens_contato`; não envia e-mail.
- Tema dia/noite salvo neste navegador.
- Personalização do mascote ainda não implementada; botão identificado como “Em breve”.
- Oficinas, eventos e redes sociais mantêm o conteúdo visual original; não possuem gestão própria.
- Desafios com correção automática exigem `resposta_correta`. Atividades com avaliação manual não têm fluxo de revisão nesta versão.

Para publicar, use um servidor WSGI, configure chaves próprias, HTTPS e `COOKIE_SECURE=1`. O comando `python app.py` serve para desenvolvimento local.

## Documentação

O PDF geral corresponde à documentação Flask anterior à integração do jogo. Para as novas rotas, consulte `docs/integracao_jogo.md`.

