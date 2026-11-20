# Nexa Play / Nexa Quest

> Para receber nível, XP e conquistas do jogo, veja [integracao_jogo.md](integracao_jogo.md). O guia abaixo descreve a API de missões e a estrutura geral. O PDF acompanha a versão anterior deste guia. Em contas já sincronizadas, o painel e o ranking usam o estado enviado pelo jogo.


Guia do projeto Flask e da API REST

Revisão: 20/11/2026. Python 3.12+, Flask, Jinja, SQLite e JWT.

## 1. Instalação e primeiro acesso

O Flask entrega o site e a API no mesmo endereço. As páginas HTML são renderizadas pelo servidor. Cadastro, login, perfil, contato e progresso usam o SQLite; não dependem de uma sessão simulada no navegador.

Na pasta que contém `app.py`, crie o ambiente virtual:

```bash
python -m venv .venv
```

Ative no Linux/macOS com Bash ou Zsh:

```bash
source .venv/bin/activate
```

No Fish, use `source .venv/bin/activate.fish`. No Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instale as dependências e inicie o site:

```bash
python -m pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000`. Também são aceitos `python backend/main.py`, `cd backend` seguido de `python main.py` e `python -m flask --app app run`.

O banco `backend/instance/nexadb.db` é criado na primeira execução. Não é necessário instalar MySQL. Uma chave local persistente é gerada se nenhuma chave for configurada. A aplicação inicia sem usuários e sem jornadas.

### Jornada de exemplo

Em outro terminal, com o mesmo ambiente virtual ativo:

```bash
python -m flask --app app seed-demo
```

Crie sua conta no site, abra Explorar e entre em “Primeiros passos em Python”. Inicie a missão, leia o conteúdo, responda `print` ao desafio e conclua a missão. O desafio concede 10 XP e a missão concede 90 XP. O total de 100 XP libera o nível Explorador e duas conquistas iniciais.

O comando de exemplo não cria usuários e não duplica a jornada quando executado novamente.

<!-- pagebreak -->

## 2. Estrutura Flask e configuração

A pasta `frontend/` foi incorporada ao pacote Flask. Templates e arquivos estáticos ficam junto da aplicação.

| Caminho | Função |
|---|---|
| `app.py` | Entrada local e aplicação WSGI chamada `app`. |
| `backend/__init__.py` | Exporta a fábrica `create_app`. |
| `backend/server.py` | Configuração, banco, JWT e registro das rotas. |
| `backend/web.py` | Páginas, formulários, sessão e CSRF. |
| `backend/api.py` | API JSON com autenticação JWT. |
| `backend/auth.py` | Validação e autenticação de contas. |
| `backend/game.py` | Progresso, correção de desafios, XP e conquistas. |
| `backend/commands.py` | Criação de administrador e jornada de exemplo. |
| `backend/database_manager.py` | Conexões, transações e migração SQLite. |
| `backend/database/nexadb.sql` | Esquema, índices, níveis e conquistas. |
| `backend/templates/` | Páginas Jinja; base, cabeçalho e rodapé compartilhados. |
| `backend/static/` | Subpastas css, js, images, fonts e licenses. |
| `backend/instance/` | Banco e chave local gerados em execução. |
| `docs/` e `tests/` | Documentação e testes de integração. |

Nos templates, use `url_for('static', filename='css/styles.css')` para recursos e `url_for('web.explorar')` para navegação. No CSS, as imagens e a fonte usam caminhos relativos a `static/css/`.

### Variáveis opcionais

Copie `backend/.env.example` para `backend/.env` caso queira configurar o ambiente. Variáveis já definidas no sistema têm prioridade sobre o arquivo.

| Variável | Uso e padrão local |
|---|---|
| `HOST`, `PORT` | `127.0.0.1` e `5000` no comando `python app.py`. |
| `FLASK_DEBUG` | `0`; use `1` somente durante desenvolvimento. |
| `SECRET_KEY` | Chave para assinar a sessão do site. |
| `JWT_SECRET_KEY` | Chave para assinar tokens da API. |
| `JWT_ACCESS_TOKEN_EXPIRES` | Validade do JWT em horas; padrão: `2`. |
| `DATABASE` | Caminho do SQLite; relativo à pasta backend se não absoluto. |
| `COOKIE_SECURE` | `0` no HTTP local; `1` ao usar HTTPS em produção. |

Para gerar uma chave, execute `python -c "import secrets; print(secrets.token_hex(32))"`. Guarde as chaves no ambiente ou no `.env`, nunca no código. `.env` e `instance/` estão no `.gitignore`. A opção antiga `FRONTEND_DIR` foi removida.

<!-- pagebreak -->

## 3. Páginas, formulários e sessão

| Endereço | Método | Comportamento |
|---|---|---|
| `/` | GET | Início público ou resumo da conta conectada. |
| `/explorar` | GET | Exibe as jornadas publicadas e o conteúdo visual original. |
| `/sobre-nos` | GET | Apresentação da marca. |
| `/nexa-quest` | GET | Convite ao login ou painel real de XP, nível e conquistas. |
| `/login` | GET, POST | Login com e-mail e senha. |
| `/cadastro` | GET, POST | Criação de conta e entrada automática. |
| `/personalizar` | GET, POST | Conta conectada pode atualizar nome e e-mail. |
| `/fale-com-a-gente` | GET, POST | Valida e grava a mensagem no SQLite. |
| `/sair` | POST | Encerra a sessão do navegador. |
| `/jornadas/<id>` | GET | Conteúdos, missões e desafios de uma jornada publicada. |
| `/missoes/<id>/iniciar` | POST | Conta conectada inicia uma missão. |
| `/missoes/<id>/concluir` | POST | Conta conectada conclui uma missão elegível. |
| `/desafios/<id>/responder` | POST | Envia resposta de um desafio da missão iniciada. |

Links antigos como `/explorar.html` redirecionam para a rota Flask correspondente. Isso mantém a navegação antiga utilizável. O acesso direto aos arquivos em `templates/` não renderiza Jinja.

### Regras dos formulários

O nome aceita até 100 caracteres e o e-mail, até 150. A senha precisa ter de 8 a 128 caracteres. O e-mail é normalizado para letras minúsculas e não pode ser repetido. A senha é armazenada como hash pelo Werkzeug.

O contato exige nome, e-mail válido, assunto de até 150 caracteres e mensagem de até 5000 caracteres. A confirmação aparece depois da gravação em `mensagens_contato`. Não existe integração com envio de e-mail nesta versão.

A sessão usa um cookie assinado, HttpOnly e SameSite=Lax, com duração de duas horas. O cookie não contém senha nem JWT. Todos os POSTs das páginas exigem o campo oculto `csrf_token`, gerado pelo Flask. A API utiliza autenticação separada por Bearer JWT.

O servidor consulta a conta a cada acesso autenticado. Contas removidas, inativas ou bloqueadas perdem acesso. O parâmetro `next` aceita apenas destinos internos previstos, para impedir redirecionamento para outro site.

O tema fica salvo no navegador. A personalização do mascote aparece como “Em breve”. Eventos, oficinas e redes sociais preservam o material visual original, sem gestão própria. A interface não oferece painel administrativo.

<!-- pagebreak -->

## 4. Autenticação e exemplos da API

A URL base local é `http://127.0.0.1:5000`. Requisições com corpo usam um objeto JSON e `Content-Type: application/json`. Nas rotas protegidas, envie `Authorization: Bearer SEU_TOKEN`.

### Verificar o servidor

```bash
curl http://127.0.0.1:5000/api/health
```

Resposta: `{"banco":"conectado","status":"ok"}`. Quando o banco não está disponível, a rota responde com status 503.

### Criar conta

```bash
curl -X POST http://127.0.0.1:5000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"nome":"Usuario","email":"user@example.com","senha":"SenhaForte123"}'
```

Retorna status 201 com `mensagem`, `token` e `usuario`. O cadastro público sempre cria uma conta comum. Campos enviados para obter permissão de administrador são ignorados.

### Entrar e consultar o perfil

```bash
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","senha":"SenhaForte123"}'
```

Copie o valor de `token` para as próximas chamadas:

```bash
curl http://127.0.0.1:5000/api/usuarios/me \
  -H 'Authorization: Bearer SEU_TOKEN'
```

O perfil não expõe o hash da senha. Para atualizar nome ou e-mail:

```bash
curl -X PATCH http://127.0.0.1:5000/api/usuarios/me \
  -H 'Authorization: Bearer SEU_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"nome":"Novo nome"}'
```

Essa rota não altera senha, status ou permissão administrativa. O JWT expira em duas horas por padrão; faça login novamente para obter outro. Não há endpoint de renovação ou de revogação individual nesta versão. Sair do site encerra apenas a sessão do navegador, sem revogar tokens JWT já emitidos.

Os comandos cURL desta página usam a sintaxe Bash, Zsh, Fish ou Git Bash. No Windows PowerShell, prefira `curl.exe` com argumentos equivalentes ou use o Postman.

<!-- pagebreak -->

## 5. Rotas de consulta e progresso

### Consultas públicas

| Método e rota | Resultado |
|---|---|
| `GET /api/jornadas` | Jornadas publicadas. |
| `GET /api/jornadas/<id>/missoes` | Missões publicadas, ordenadas pelo campo ordem. |
| `GET /api/missoes/<id>/desafios` | Desafios publicados, sem a resposta correta. |
| `GET /api/conteudos` | Conteúdos publicados e campo `desbloqueado`. |
| `GET /api/conquistas` | Catálogo de conquistas ativas, não apenas as já obtidas. |
| `GET /api/ranking` | Até 20 contas ativas, ordenadas por XP; sem e-mail. |

As consultas não expõem rascunhos nem missões de jornadas não publicadas. O esquema atual não define nível mínimo para conteúdos; por isso os materiais publicados retornam `desbloqueado: true`.

### Rotas que exigem JWT

| Método e rota | Corpo ou resultado |
|---|---|
| `GET /api/usuarios/me` | Dados da própria conta. |
| `PATCH /api/usuarios/me` | Nome e/ou e-mail. |
| `GET /api/usuarios/me/progresso` | Objetos `missoes`, `tentativas` e total em `pontos`. |
| `POST /api/missoes/<id>/iniciar` | Sem corpo; cria ou recupera o progresso. |
| `POST /api/desafios/<id>/tentativas` | Corpo: `{"resposta":"print"}`. |
| `POST /api/missoes/<id>/concluir` | Sem corpo; conclui a missão e concede a recompensa. |
| `POST /api/conquistas/<id>/compartilhar` | Corpo opcional: `{"plataforma":"link"}`. |

O primeiro início de missão retorna 201; iniciar novamente retorna 200, sem criar outro progresso. Uma resposta avaliada retorna 201, com `correto`, `pontos_ganhos`, `pontos_totais` e `conquistas_desbloqueadas`.

Para concluir, primeiro inicie a missão e obtenha aprovação em todos os desafios publicados. Missões sem desafios publicados podem ser concluídas após o início. A conclusão retorna 200 com a recompensa e o total atualizado.

A resposta é comparada ao campo `resposta_correta`, ignorando maiúsculas, minúsculas e espaços nas extremidades. Se esse campo não estiver configurado, a tentativa retorna 409. Não há revisão manual de atividades nesta versão.

Respostas aprovadas e missões concluídas não podem gerar pontos novamente: chamadas repetidas retornam 409. A gravação da tentativa, do progresso, dos pontos e das conquistas usa transações SQLite. Chamadas simultâneas também não duplicam a recompensa.

O compartilhamento verifica se a conquista pertence à conta e grava plataforma, data e URL em `compartilhamentos`. A URL aponta para `/nexa-quest`; não publica em redes sociais e não cria uma página pública de conquista individual.

<!-- pagebreak -->

## 6. Administração e publicação de conteúdos

Crie um administrador localmente, sem definir uma senha padrão no projeto:

```bash
python -m flask --app app create-admin
```

Informe nome, e-mail e senha quando o terminal solicitar. Depois use `/api/auth/login` para obter o JWT desse administrador. As rotas administrativas verificam a permissão atual no banco.

| Método e rota | Operação |
|---|---|
| `GET /api/admin/<recurso>` | Lista registros do recurso. |
| `POST /api/admin/<recurso>` | Cria um registro com os campos JSON válidos. |
| `GET /api/admin/<recurso>/<id>` | Consulta um registro. |
| `PUT` ou `PATCH /api/admin/<recurso>/<id>` | Atualiza os campos informados. |
| `DELETE /api/admin/<recurso>/<id>` | Exclui, respeitando os relacionamentos do banco. |

Recursos permitidos: `usuarios`, `niveis`, `jornadas`, `missoes`, `desafios`, `conteudos`, `conquistas` e `compartilhamentos`. Contas comuns recebem 403. Não é possível excluir a própria conta administrativa por essas rotas.

### Sequência de cadastro

1. Crie uma jornada e guarde o `id_jornada` retornado.
2. Crie uma missão vinculada à jornada e guarde o `id_missao`.
3. Cadastre conteúdos e desafios da missão.
4. Publique os registros com os status corretos. O público verá apenas registros publicados.

Exemplo de corpo para `POST /api/admin/jornadas`:

```json
{"titulo":"Python básico","descricao":"Primeiros passos","status":"publicada"}
```

Exemplo de missão, substituindo o ID pelo da jornada criada:

```json
{"id_jornada":1,"titulo":"Primeira missão","ordem":1,
 "pontos_recompensa":90,"status":"publicada"}
```

Exemplo de desafio:

```json
{"id_missao":1,"titulo":"Função de saída","tipo":"pergunta",
 "descricao":"Qual função exibe uma mensagem em Python?",
 "resposta_correta":"print","pontos_recompensa":10,"status":"publicado"}
```

Jornadas e missões usam `publicada`; desafios e conteúdos usam `publicado`. O SQL define os demais valores permitidos. O campo `ordem` de missão não pode se repetir na mesma jornada. Conquistas usam os critérios `missoes_concluidas`, `pontos_acumulados`, `jornadas_concluidas` ou `desafios_aprovados`.

O administrador pode ler a resposta correta nas rotas administrativas. As rotas públicas removem esse campo. Campos de senha e permissão de usuários são protegidos; use o comando local para criar administradores.

<!-- pagebreak -->

## 7. Banco, migração e verificação

O projeto usa SQLite com chaves estrangeiras ativadas em cada conexão. O SQL inclui usuários, níveis, jornadas, missões, desafios, conteúdos, progresso, tentativas, conquistas, histórico de pontos, compartilhamentos e mensagens de contato.

### Atualizar um projeto existente

1. Faça uma cópia do banco atual antes de substituir o projeto.
2. Preserve o arquivo `backend/instance/nexadb.db` e as chaves locais existentes.
3. Use os novos arquivos e instale `requirements.txt`.
4. Inicie `python app.py`; a inicialização cria os objetos ausentes.

A migração adiciona `desafios.resposta_correta` quando o banco antigo ainda não tem esse campo. A tabela `mensagens_contato` é criada sem apagar tabelas existentes. Usuários, jornadas e progresso existentes são preservados. Níveis e conquistas iniciais têm seus dados atualizados pelo SQL original do projeto.

Desafios antigos ficam sem resposta até que um administrador configure `resposta_correta`. Esta migração cobre o esquema incluído no projeto; bancos com outras alterações precisam de análise própria. Preserve a pasta `backend/instance/` ao atualizar seu projeto. Ela contém os dados e a chave local da sua instalação.

### Testes de integração

```bash
python -m unittest discover -s tests -v
```

Os testes criam bancos temporários. Cobrem páginas e recursos locais; cadastro, login, saída e perfil; CSRF; contato; JSON inválido; permissões; ocultação de rascunhos; correção de desafios; pontuação; conquistas; repetição e concorrência; migração de banco antigo; comandos locais e compatibilidade dos links.

### Códigos de resposta

| Código | Significado |
|---|---|
| 200 / 201 | Operação concluída / registro criado. |
| 302 | Redirecionamento nas páginas e links antigos. |
| 400 | Dados inválidos, JSON incorreto ou CSRF ausente. |
| 401 / 403 | Falta autenticação válida / falta permissão. |
| 404 / 405 | Recurso ausente / método não permitido. |
| 409 | E-mail duplicado, ação repetida ou etapa pendente. |
| 413 | Corpo maior que o limite de 1 MiB. |
| 422 | JWT inválido, conforme o Flask-JWT-Extended. |
| 500 / 503 | Erro interno / banco indisponível no health check. |

Para publicar o projeto, configure chaves próprias, HTTPS, `COOKIE_SECURE=1`, backup do SQLite e um servidor WSGI. A aplicação WSGI é `app:app`. O servidor embutido do Flask é destinado ao uso local. Trocar a chave da sessão invalida os cookies; trocar a chave JWT invalida os tokens emitidos.
