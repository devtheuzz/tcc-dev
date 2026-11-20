# Integração do jogo com a Nexa Play

Esta API recebe **nível, XP total e conquistas** e exibe esses dados no site para a mesma conta do jogador. O jogo calcula o progresso; o site recebe e salva.

Não é necessário acessar o SQLite, criar tabelas no jogo nem enviar nome ou e-mail junto do progresso.

## 1. Endereços

Use a URL do site publicado como endereço base da API:

```text
https://nexaplay.vercel.app
```

Para testes com Flask rodando no mesmo computador, também é possível usar:

```text
http://127.0.0.1:5000
```

Se a integração local não funcionar, **pode tentar usar `https://nexaplay.vercel.app`**, desde que as rotas da API estejam publicadas e funcionando nesse endereço. Basta trocar a URL base no Unity. O site abrir no navegador, sozinho, não confirma que a API esteja disponível.

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

## 6. Exemplo em C# para Unity 6

Compatível com Unity 6, usando `UnityWebRequest` para as requisições HTTP e `JsonUtility` para converter o JSON. Não exige pacotes externos. Crie um script chamado `NexaPlayApi.cs` em `Assets/Scripts`, anexe-o a um GameObject e configure a URL base. O exemplo já aponta para o site publicado. Para testes locais, troque para `http://127.0.0.1:5000` no Inspector da Unity.

```csharp
using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

public class NexaPlayApi : MonoBehaviour
{
    [SerializeField] private string apiBase = "https://nexaplay.vercel.app";
    private string token;

    [Serializable]
    public class LoginDados
    {
        public string email;
        public string senha;
    }

    [Serializable]
    public class LoginResposta
    {
        public string token;
    }

    [Serializable]
    public class Conquista
    {
        public string codigo;
        public string nome;
        public string descricao;
    }

    [Serializable]
    public class Progresso
    {
        public int usuario_id;
        public bool sincronizado;
        public int nivel;
        public int xp;
        public int versao;
        public Conquista[] conquistas;
        public string atualizado_em;
    }

    [Serializable]
    public class EstadoCompleto
    {
        public int nivel;
        public int xp;
        public int versao;
        public Conquista[] conquistas;
    }

    [Serializable]
    public class EnvioResposta
    {
        public string mensagem;
        public bool repetido;
        public Progresso progresso;
    }

    [Serializable]
    public class ErroApi
    {
        public string erro;
        public string msg;
        public int versao_atual;
    }

    private IEnumerator ChamarApi<T>(
        string rota, string metodo, string corpo,
        Action<T> sucesso, Action<int, string> falha) where T : class
    {
        using (var requisicao = new UnityWebRequest(apiBase.TrimEnd('/') + rota, metodo))
        {
            requisicao.downloadHandler = new DownloadHandlerBuffer();

            if (corpo != null)
            {
                requisicao.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(corpo));
                requisicao.SetRequestHeader("Content-Type", "application/json");
            }

            if (!string.IsNullOrEmpty(token) && rota != "/api/auth/login")
                requisicao.SetRequestHeader("Authorization", "Bearer " + token);

            yield return requisicao.SendWebRequest();

            if (requisicao.result != UnityWebRequest.Result.Success)
            {
                string mensagem = requisicao.downloadHandler.text;
                try
                {
                    var erro = JsonUtility.FromJson<ErroApi>(mensagem);
                    if (!string.IsNullOrEmpty(erro.erro)) mensagem = erro.erro;
                    else if (!string.IsNullOrEmpty(erro.msg)) mensagem = erro.msg;
                }
                catch (Exception) { }

                if (string.IsNullOrEmpty(mensagem)) mensagem = requisicao.error;
                falha?.Invoke((int)requisicao.responseCode, mensagem);
                yield break;
            }

            try
            {
                sucesso?.Invoke(JsonUtility.FromJson<T>(requisicao.downloadHandler.text));
            }
            catch (Exception e)
            {
                falha?.Invoke((int)requisicao.responseCode, "Resposta JSON inválida: " + e.Message);
            }
        }
    }

    // Receba email e senha pela tela de login, sem guardar a senha no código.
    public IEnumerator Entrar(string email, string senha,
        Action<string> sucesso, Action<int, string> falha)
    {
        string corpo = JsonUtility.ToJson(new LoginDados { email = email, senha = senha });
        yield return ChamarApi<LoginResposta>("/api/auth/login", "POST", corpo,
            resposta => { token = resposta.token; sucesso?.Invoke(token); }, falha);
    }

    public IEnumerator Consultar(Action<Progresso> sucesso, Action<int, string> falha)
    {
        yield return ChamarApi<Progresso>(
            "/api/jogo/progresso", "GET", null, sucesso, falha);
    }

    public IEnumerator EnviarEstado(EstadoCompleto estado,
        Action<EnvioResposta> sucesso, Action<int, string> falha)
    {
        string corpo = JsonUtility.ToJson(estado);
        yield return ChamarApi<EnvioResposta>(
            "/api/jogo/progresso", "POST", corpo, sucesso, falha);
    }
}
```

Exemplo de uso em outro `MonoBehaviour`, com uma referência ao componente `NexaPlayApi`:

```csharp
// Receba email e senha do formulário de login do jogo.
StartCoroutine(api.Entrar(email, senha, token =>
{
    StartCoroutine(api.Consultar(atual =>
    {
        // Compare o progresso remoto com o save local antes de escolher o estado.
        // Estes valores são exemplos; use o nível, o XP total e as conquistas do save.
        var envio = new NexaPlayApi.EstadoCompleto
        {
            nivel = 4,
            xp = 1250,
            versao = atual.versao + 1,
            conquistas = new NexaPlayApi.Conquista[]
            {
                new NexaPlayApi.Conquista
                {
                    codigo = "primeira-vitoria",
                    nome = "Primeira vitória",
                    descricao = "Vença a primeira partida."
                }
            }
        };

        // Guarde 'envio' até a confirmação. Se a rede falhar, repita
        // exatamente o mesmo objeto, sem mudar a versão.
        StartCoroutine(api.EnviarEstado(envio,
            resposta => Debug.Log("Sincronizado: " + resposta.progresso.versao),
            (status, erro) => Debug.LogError($"Erro {status}: {erro}")));
    }, (status, erro) => Debug.LogError($"Consulta {status}: {erro}")));
}, (status, erro) => Debug.LogError($"Login {status}: {erro}")));
```

Ao receber 401 ou 422 por token inválido/expirado, peça login novamente. Em caso de 409, consulte o GET e resolva qual save deve prevalecer. Não aumente automaticamente a versão de um save antigo. O exemplo usa corrotinas, então não bloqueia a execução do jogo enquanto espera a resposta.

## 7. Teste rápido com cURL

Com uma conta criada no site publicado:

```bash
curl -X POST https://nexaplay.vercel.app/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"jogador@example.com","senha":"SenhaDoJogador123"}'
```

Copie o token recebido e substitua `SEU_TOKEN` abaixo:

```bash
curl -X POST https://nexaplay.vercel.app/api/jogo/progresso \
  -H 'Authorization: Bearer SEU_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"nivel":4,"xp":1250,"versao":1,"conquistas":[{"codigo":"primeira-vitoria","nome":"Primeira vitória"}]}'
```

Para conferir o que ficou salvo:

```bash
curl https://nexaplay.vercel.app/api/jogo/progresso \
  -H 'Authorization: Bearer SEU_TOKEN'
```

Para testar no Flask local, substitua `https://nexaplay.vercel.app` por `http://127.0.0.1:5000` nos comandos acima.

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

Use HTTPS fora do ambiente local. Em celular ou outro computador, `127.0.0.1` é o próprio dispositivo: use `https://nexaplay.vercel.app` se a API estiver publicada nele, ou outro endereço acessível do servidor Flask. Em builds nativas da Unity, CORS não se aplica; para Unity WebGL em outro domínio, o backend precisa permitir a origem do jogo.

**Atenção à hospedagem:** não foi possível confirmar daqui se as rotas da API respondem no endereço publicado. Se o site abrir, mas `/api/auth/login` ou `/api/jogo/progresso` retornarem `404` ou `500`, é preciso ajustar a publicação do backend. Em ambiente serverless como a Vercel, um banco SQLite gravado no disco local pode não manter os dados entre execuções; para persistência confiável, configure um banco externo.

O token autoriza apenas a conta do jogador. A API recebe os valores calculados pelo jogo e valida seu formato, mas não verifica se as partidas ocorreram. Se o projeto precisar impedir trapaças, o envio deve partir de um backend confiável que valide as partidas.

Envie ao salvar uma partida, subir de nível ou desbloquear uma conquista. Não é necessário enviar a cada quadro. Este endpoint guarda um resumo; ele não substitui um sistema completo de save com inventário, mapa ou posição do jogador.
