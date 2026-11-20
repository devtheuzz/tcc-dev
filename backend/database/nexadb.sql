PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL CHECK(length(nome) <= 100),
    email TEXT NOT NULL UNIQUE CHECK(length(email) <= 150),
    senha_hash TEXT NOT NULL,
    data_cadastro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'ativo'
        CHECK(status IN ('ativo', 'inativo', 'bloqueado')),
    is_admin INTEGER NOT NULL DEFAULT 0 CHECK(is_admin IN (0, 1))
);

CREATE TABLE IF NOT EXISTS niveis (
    id_nivel INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    pontos_minimos INTEGER NOT NULL UNIQUE CHECK(pontos_minimos >= 0)
);

CREATE TABLE IF NOT EXISTS jornadas (
    id_jornada INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descricao TEXT,
    status TEXT NOT NULL DEFAULT 'rascunho'
        CHECK(status IN ('rascunho', 'publicada', 'arquivada')),
    data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS missoes (
    id_missao INTEGER PRIMARY KEY AUTOINCREMENT,
    id_jornada INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    descricao TEXT,
    ordem INTEGER NOT NULL CHECK(ordem >= 0),
    pontos_recompensa INTEGER NOT NULL DEFAULT 0
        CHECK(pontos_recompensa >= 0),
    status TEXT NOT NULL DEFAULT 'rascunho'
        CHECK(status IN ('rascunho', 'publicada', 'arquivada')),
    FOREIGN KEY (id_jornada) REFERENCES jornadas(id_jornada)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (id_jornada, ordem)
);

CREATE TABLE IF NOT EXISTS desafios (
    id_desafio INTEGER PRIMARY KEY AUTOINCREMENT,
    id_missao INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    descricao TEXT,
    resposta_correta TEXT,
    tipo TEXT NOT NULL DEFAULT 'outro'
        CHECK(tipo IN ('quiz', 'pergunta', 'atividade', 'projeto', 'outro')),
    pontos_recompensa INTEGER NOT NULL DEFAULT 0
        CHECK(pontos_recompensa >= 0),
    status TEXT NOT NULL DEFAULT 'rascunho'
        CHECK(status IN ('rascunho', 'publicado', 'arquivado')),
    FOREIGN KEY (id_missao) REFERENCES missoes(id_missao)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS conteudos (
    id_conteudo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_missao INTEGER,
    titulo TEXT NOT NULL,
    descricao TEXT,
    tipo TEXT NOT NULL DEFAULT 'texto'
        CHECK(tipo IN ('texto', 'video', 'link', 'documento', 'outro')),
    url TEXT,
    status TEXT NOT NULL DEFAULT 'rascunho'
        CHECK(status IN ('rascunho', 'publicado', 'arquivado')),
    data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_missao) REFERENCES missoes(id_missao)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS progresso_missoes (
    id_progresso INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    id_missao INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'em_andamento'
        CHECK(status IN ('nao_iniciada', 'em_andamento', 'concluida')),
    data_inicio TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_conclusao TEXT,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (id_missao) REFERENCES missoes(id_missao)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (id_usuario, id_missao)
);

CREATE INDEX IF NOT EXISTS idx_progresso_usuario_status
ON progresso_missoes(id_usuario, status);

CREATE TABLE IF NOT EXISTS tentativas_desafios (
    id_tentativa INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    id_desafio INTEGER NOT NULL,
    resposta TEXT,
    resultado TEXT NOT NULL DEFAULT 'pendente'
        CHECK(resultado IN ('pendente', 'aprovada', 'reprovada')),
    pontos_obtidos INTEGER NOT NULL DEFAULT 0 CHECK(pontos_obtidos >= 0),
    data_tentativa TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    validada_por_sistema INTEGER NOT NULL DEFAULT 0
        CHECK(validada_por_sistema IN (0, 1)),
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (id_desafio) REFERENCES desafios(id_desafio)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_tentativas_usuario_desafio
ON tentativas_desafios(id_usuario, id_desafio);

CREATE INDEX IF NOT EXISTS idx_tentativas_resultado
ON tentativas_desafios(resultado);

CREATE TABLE IF NOT EXISTS conquistas (
    id_conquista INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    icone TEXT,
    criterio TEXT NOT NULL DEFAULT 'outro'
        CHECK(criterio IN (
            'missoes_concluidas',
            'pontos_acumulados',
            'jornadas_concluidas',
            'desafios_aprovados',
            'outro'
        )),
    valor_criterio INTEGER NOT NULL DEFAULT 1 CHECK(valor_criterio >= 0),
    status TEXT NOT NULL DEFAULT 'ativa'
        CHECK(status IN ('ativa', 'inativa'))
);

CREATE TABLE IF NOT EXISTS usuarios_conquistas (
    id_usuario INTEGER NOT NULL,
    id_conquista INTEGER NOT NULL,
    data_desbloqueio TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_usuario, id_conquista),
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (id_conquista) REFERENCES conquistas(id_conquista)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_uc_data
ON usuarios_conquistas(data_desbloqueio);

CREATE TABLE IF NOT EXISTS historico_pontos (
    id_historico INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    id_tentativa INTEGER,
    quantidade INTEGER NOT NULL,
    motivo TEXT NOT NULL,
    data_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (id_tentativa) REFERENCES tentativas_desafios(id_tentativa)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_hp_usuario_data
ON historico_pontos(id_usuario, data_registro);

CREATE INDEX IF NOT EXISTS idx_hp_tentativa
ON historico_pontos(id_tentativa);

CREATE TABLE IF NOT EXISTS compartilhamentos (
    id_compartilhamento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    id_conquista INTEGER NOT NULL,
    plataforma TEXT NOT NULL,
    url_compartilhada TEXT,
    data_compartilhamento TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (id_conquista) REFERENCES conquistas(id_conquista)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_comp_usuario_data
ON compartilhamentos(id_usuario, data_compartilhamento);

CREATE VIEW IF NOT EXISTS vw_pontuacao_usuarios AS
SELECT
    u.id_usuario,
    u.nome,
    u.email,
    COALESCE(SUM(hp.quantidade), 0) AS pontos_totais,
    (
        SELECT n.nome
        FROM niveis n
        WHERE n.pontos_minimos <= COALESCE(
            (
                SELECT SUM(hp2.quantidade)
                FROM historico_pontos hp2
                WHERE hp2.id_usuario = u.id_usuario
            ), 0
        )
        ORDER BY n.pontos_minimos DESC
        LIMIT 1
    ) AS nivel_atual
FROM usuarios u
LEFT JOIN historico_pontos hp ON hp.id_usuario = u.id_usuario
GROUP BY u.id_usuario, u.nome, u.email;

INSERT INTO niveis (nome, descricao, pontos_minimos)
VALUES
    ('Iniciante', 'Primeiros passos na plataforma', 0),
    ('Explorador', 'Já começou a completar atividades', 100),
    ('Especialista', 'Demonstra progresso consistente', 300),
    ('Mestre', 'Alcançou pontuação avançada', 700)
ON CONFLICT(nome) DO UPDATE SET
    descricao = excluded.descricao,
    pontos_minimos = excluded.pontos_minimos;

INSERT INTO conquistas (nome, descricao, criterio, valor_criterio, status)
VALUES
    ('Primeira Missão', 'Conclua sua primeira missão.', 'missoes_concluidas', 1, 'ativa'),
    ('Caçador de Pontos', 'Acumule 100 pontos.', 'pontos_acumulados', 100, 'ativa'),
    ('Desbravador', 'Conclua 5 missões.', 'missoes_concluidas', 5, 'ativa')
ON CONFLICT(nome) DO UPDATE SET
    descricao = excluded.descricao,
    criterio = excluded.criterio,
    valor_criterio = excluded.valor_criterio,
    status = excluded.status;

CREATE TABLE IF NOT EXISTS mensagens_contato (
    id_mensagem INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL CHECK(length(nome) BETWEEN 1 AND 100),
    email TEXT NOT NULL CHECK(length(email) <= 150),
    assunto TEXT NOT NULL CHECK(length(assunto) BETWEEN 1 AND 150),
    mensagem TEXT NOT NULL CHECK(length(mensagem) BETWEEN 1 AND 5000),
    data_envio TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Estado completo enviado pelo jogo. A conta é obtida do token JWT.
CREATE TABLE IF NOT EXISTS progresso_jogo (
    id_usuario INTEGER PRIMARY KEY,
    nivel INTEGER NOT NULL CHECK(nivel BETWEEN 1 AND 100000),
    xp INTEGER NOT NULL CHECK(xp BETWEEN 0 AND 2147483647),
    versao INTEGER NOT NULL CHECK(versao BETWEEN 1 AND 2147483647),
    atualizado_em TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conquistas_jogo (
    id_usuario INTEGER NOT NULL,
    codigo TEXT NOT NULL CHECK(length(codigo) BETWEEN 1 AND 80),
    nome TEXT NOT NULL CHECK(length(nome) BETWEEN 1 AND 100),
    descricao TEXT NOT NULL DEFAULT '' CHECK(length(descricao) <= 500),
    PRIMARY KEY (id_usuario, codigo),
    FOREIGN KEY (id_usuario) REFERENCES progresso_jogo(id_usuario) ON DELETE CASCADE
);
