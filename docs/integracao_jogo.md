# Integração do jogo com a Nexa Play

Esta API recebe **nível, XP total e conquistas** e exibe esses dados no site para a mesma conta do jogador. O jogo calcula o progresso; o site recebe e salva.

Não é necessário acessar o SQLite, criar tabelas no jogo nem enviar nome ou e-mail junto do progresso.

## 1. Endereços

Com o Flask rodando localmente:

```text
http://127.0.0.1:5000
```

| Método | Rota | Para que serve |
|---|---|---|
| POST | `/api/auth/login` | Entrar com a conta Nexa e obter o token. |
| GET | `/api/jogo/progresso` | Ler o último progresso e a versão salva. |
| POST | `/api/jogo/progresso` | Enviar o estado completo do jogo. |

As duas rotas de progresso exigem `Authorization: Bearer TOKEN`. No POST, envie também `Content-Type: application/json`.

## 2. Login do jogador

A conta pode ser criada em `/cadastro` no site. Para usar a conta no jogo, envie:

```http
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "email": "jogador@example.com",
  "senha": "SenhaDoJogador123"
}
```

Resposta 200, com este formato:

```json
{
  "token": "TOKEN_JWT_RECEBIDO",
  "usuario": {
    "id_usuario": 1,
    "nome": "Jogador",
    "email": "jogador@example.com",
    "status": "ativo",
    "is_admin": 0,
    "data_cadastro": "2026-11-20 17:00:00"
  }
}
```

Use o token retornado, sem aspas extras, nos próximos pedidos. Ele expira em duas horas por padrão. Se receber 401 ou um erro de token expirado/inválido, solicite login novamente. Não guarde a senha no código do jogo.

O token identifica a conta. **Não envie `usuario_id`, nome ou e-mail no POST de progresso.** Não é necessário usar uma conta administradora.

## 3. Consultar o progresso antes de enviar

```http
GET /api/jogo/progresso
Authorization: Bearer TOKEN_JWT_RECEBIDO
```

Antes do primeiro envio:

```json
{
  "usuario_id": 1,
  "sincronizado": false,
  "nivel": 1,
  "xp": 0,
  "versao": 0,
  "conquistas": [],
  "atualizado_em": null
}
```

`sincronizado: false` significa que o jogo ainda não enviou dados. Esses valores iniciais não apagam o progresso local do jogador. Use a consulta para decidir qual save deve ser carregado e qual será a próxima versão.

## 4. Enviar nível, XP e conquistas

```http
POST /api/jogo/progresso
Authorization: Bearer TOKEN_JWT_RECEBIDO
Content-Type: application/json
```

```json
{
  "nivel": 4,
  "xp": 1250,
  "versao": 1,
  "conquistas": [
    {
      "codigo": "primeira-vitoria",
      "nome": "Primeira vitória",
      "descricao": "Vença a primeira partida."
    },
    {
      "codigo": "explorador",
      "nome": "Explorador",
      "descricao": "Explore todas as áreas iniciais."
    }
  ]
}
```

| Campo | Regra |
|---|---|
| `nivel` | Obrigatório. Inteiro de 1 a 100000. |
| `xp` | Obrigatório. Inteiro de 0 a 2147483647. Representa o XP total acumulado. |
| `versao` | Obrigatório. Inteiro de 1 a 2147483647, crescente por jogador. |
| `conquistas` | Obrigatório. Lista completa das conquistas desbloqueadas, com no máximo 200 itens. Pode ser `[]`. |
| `codigo` | Obrigatório em cada conquista. Identificador estável de 1 a 80 caracteres. Aceita letras sem acento, números, ponto, hífen e sublinhado; começa com letra ou número. |
| `nome` | Obrigatório em cada conquista. De 1 a 100 caracteres após remover espaços nas pontas. |
| `descricao` | Opcional. Até 500 caracteres. Se não enviada, fica vazia. |

Não use strings, números decimais, `true` ou `false` nos campos inteiros. Não repita um `codigo` na lista. Campos extras são rejeitados para apontar erros de integração.

Resposta 200:

```json
{
  "mensagem": "Progresso sincronizado.",
  "repetido": false,
  "progresso": {
    "usuario_id": 1,
    "sincronizado": true,
    "nivel": 4,
    "xp": 1250,
    "versao": 1,
    "atualizado_em": "2026-11-20T17:00:00.000Z",
    "conquistas": [
      {
        "codigo": "explorador",
        "nome": "Explorador",
        "descricao": "Explore todas as áreas iniciais."
      },
      {
        "codigo": "primeira-vitoria",
        "nome": "Primeira vitória",
        "descricao": "Vença a primeira partida."
      }
    ]
  }
}
```

A lista na resposta é ordenada por `codigo`. Os IDs, horários e token acima são apenas exemplos.

## 5. Como atualizar sem duplicar XP

Envie sempre o **estado completo**, e não apenas o que mudou:

- O jogador tinha 1250 XP e ganhou 50: envie `xp: 1300`.
- Desbloqueou outra conquista: envie as anteriores junto da nova.
- Enviou `conquistas: []`: a lista salva passa a ficar vazia.
- Um reset do jogo pode enviar nível/XP menores, desde que use uma versão maior.

A API substitui o estado anterior. Ela não soma os 1300 XP sobre o valor já salvo.

A `versao` impede que uma requisição atrasada sobrescreva um save mais novo:

1. Consulte o GET ao iniciar a integração e carregue a versão atual.
2. Para um estado novo, aumente a versão em 1.
3. Se a rede cair sem resposta, repita **o mesmo corpo e a mesma versão**.
4. A repetição idêntica retorna 200 com `repetido: true` e mantém o horário original.
5. A mesma versão com dados diferentes retorna 409. Uma versão menor também retorna 409.

Exemplo de conflito:

```json
{
  "erro": "Versão antiga. Consulte o progresso e envie uma versão maior.",
  "versao_atual": 3
}
```

Em caso de 409, consulte o GET e resolva qual save é o mais recente. Não aumente a versão de um save antigo automaticamente para forçar o envio. Isso importa principalmente se a mesma conta jogar em dois dispositivos.

## 6. Exemplo em JavaScript

Compatível com `fetch` em um jogo web servido na mesma origem do Flask ou em um ambiente com suporte a `fetch`, como Node.js. Troque a base pelo endereço real do servidor.

```javascript
const API_BASE = 'http://127.0.0.1:5000';

async function chamarAPI(caminho, { token, dados } = {}) {
  const resposta = await fetch(API_BASE + caminho, {
    method: dados === undefined ? 'GET' : 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(dados === undefined ? {} : { 'Content-Type': 'application/json' })
    },
    ...(dados === undefined ? {} : { body: JSON.stringify(dados) })
  });
  const json = await resposta.json();
  if (!resposta.ok) {
    const erro = new Error(json.erro || json.msg || 'Falha na API');
    erro.status = resposta.status;
    erro.dados = json;
    throw erro;
  }
  return json;
}

// Receba estes dados pela tela de login do jogo.
async function entrar(email, senha) {
  const login = await chamarAPI('/api/auth/login', {
    dados: { email, senha }
  });
  return login.token;
}

async function consultar(token) {
  return chamarAPI('/api/jogo/progresso', { token });
}

async function enviarEstado(token, estadoCompleto) {
  return chamarAPI('/api/jogo/progresso', {
    token,
    dados: estadoCompleto
  });
}

// Uso, depois que o jogador autenticou e o save foi carregado:
// const atual = await consultar(token);
// const envio = {
//   nivel: nivelDoSave,
//   xp: xpTotalDoSave,
//   versao: atual.versao + 1,
//   conquistas: conquistasDoSave
// };
// await enviarEstado(token, envio);
// Guarde o objeto envio até receber confirmação. Se necessário,
// tente novamente com esse mesmo objeto, sem mudar a versão.
```

No navegador, outra porta também conta como outra origem. Esta versão não habilita CORS para origens externas. Sirva o jogo pela mesma origem do Flask ou use um proxy no backend do jogo. Em Unity, Godot ou outro aplicativo nativo, CORS não se aplica; basta enviar as requisições HTTP com os mesmos cabeçalhos e o mesmo JSON.

## 7. Teste rápido com cURL

Com uma conta criada no site:

```bash
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"jogador@example.com","senha":"SenhaDoJogador123"}'
```

Copie o token recebido e substitua `SEU_TOKEN` abaixo:

```bash
curl -X POST http://127.0.0.1:5000/api/jogo/progresso \
  -H 'Authorization: Bearer SEU_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"nivel":4,"xp":1250,"versao":1,"conquistas":[{"codigo":"primeira-vitoria","nome":"Primeira vitória"}]}'
```

Para conferir o que ficou salvo:

```bash
curl http://127.0.0.1:5000/api/jogo/progresso \
  -H 'Authorization: Bearer SEU_TOKEN'
```

Abra o site com a mesma conta e atualize a página inicial ou o painel Nexa Quest. O nível, XP, número e lista de conquistas devem corresponder ao último envio. Antes da primeira sincronização, o site continua mostrando o progresso das missões locais. Depois dela, o painel e o ranking passam a usar os dados do jogo. Os registros das missões locais são preservados e não se somam ao XP recebido.

## 8. Erros e cuidados de implementação

| Status | O que fazer |
|---|---|
| 200 | Envio aceito, repetição confirmada ou consulta concluída. |
| 400 | Corrija os campos indicados em `erro`. Nenhuma parte do progresso é salva se houver erro de validação. |
| 401 / 422 | Confira o token; se inválido ou expirado, peça login novamente. |
| 409 | Consulte o estado atual e resolva o conflito de versão. |
| 413 | Reduza o tamanho do corpo; limite global: 1 MiB. |
| 415 | Envie `Content-Type: application/json`. |
| 500 | Erro inesperado; preserve o mesmo envio para tentar novamente depois. |

Use HTTPS fora do ambiente local. Em celular ou outro computador, `127.0.0.1` é o próprio dispositivo: use o endereço acessível do servidor Flask.

O token autoriza apenas a conta do jogador. A API recebe os valores calculados pelo jogo e valida seu formato, mas não verifica se as partidas ocorreram. Se o projeto precisar impedir trapaças, o envio deve partir de um backend confiável que valide as partidas.

Envie ao salvar uma partida, subir de nível ou desbloquear uma conquista. Não é necessário enviar a cada quadro. Este endpoint guarda um resumo; ele não substitui um sistema completo de save com inventário, mapa ou posição do jogador.
