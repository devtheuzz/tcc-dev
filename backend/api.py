import sqlite3
from flask import jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash
from .auth import create_user, validate_profile
from . import game

ADMIN_RESOURCES = {
    "usuarios": ("usuarios", "id_usuario"),
    "niveis": ("niveis", "id_nivel"),
    "jornadas": ("jornadas", "id_jornada"),
    "missoes": ("missoes", "id_missao"),
    "desafios": ("desafios", "id_desafio"),
    "conteudos": ("conteudos", "id_conteudo"),
    "conquistas": ("conquistas", "id_conquista"),
    "compartilhamentos": ("compartilhamentos", "id_compartilhamento")
}

def register_api(app, db):
    def columns(table):
        return db.fetch_all(f"PRAGMA table_info({table})")

    def column_names(table):
        return [col["name"] for col in columns(table)]

    def find_column(table, *names):
        available = column_names(table)
        return next((name for name in names if name in available), None)

    def add_field(data, table, candidates, value):
        field = find_column(table, *candidates)
        if field:
            data[field] = value

    def clean(record):
        if record is None:
            return None
        record = dict(record)
        record.pop("senha_hash", None)
        record.pop("password_hash", None)
        return record

    def clean_challenge(record):
        record = clean(record)
        if record:
            record.pop("resposta_correta", None)
        return record

    def current_user_id():
        try:
            return int(get_jwt_identity())
        except (TypeError, ValueError):
            return None

    def admin_error():
        user = db.fetch_one("SELECT is_admin FROM usuarios WHERE id_usuario = ?", (current_user_id(),))
        if not user or not user["is_admin"]:
            return jsonify({"erro": "Acesso restrito a administradores."}), 403
        return None

    def insert_row(table, data):
        info = columns(table)
        primary_keys = {col["name"] for col in info if col["pk"]}
        valid = {
            key: value for key, value in data.items()
            if key in column_names(table) and key not in primary_keys
        }
        if not valid:
            raise ValueError("Nenhum campo válido foi informado.")
        fields = list(valid.keys())
        sql = f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})"
        result = db.execute(sql, tuple(valid[field] for field in fields))
        return result["last_insert_id"]

    def update_row(table, id_field, record_id, data):
        info = columns(table)
        primary_keys = {col["name"] for col in info if col["pk"]}
        valid = {
            key: value for key, value in data.items()
            if key in column_names(table) and key not in primary_keys
        }
        if table == "usuarios":
            valid.pop("senha_hash", None)
            valid.pop("password_hash", None)
            valid.pop("is_admin", None)
        if not valid:
            return False
        fields = list(valid.keys())
        sql = f"UPDATE {table} SET {', '.join(field + ' = ?' for field in fields)} WHERE {id_field} = ?"
        db.execute(sql, tuple(valid[field] for field in fields) + (record_id,))
        return True

    def get_points(user_id):
        return game.summary(db, user_id)["points"]

    @app.get("/api/health")
    def health():
        if db.check_connection():
            return jsonify({"status": "ok", "banco": "conectado"})
        return jsonify({"status": "erro", "banco": "indisponivel"}), 503

    @app.post("/api/auth/register")
    def register():
        data = request.get_json(silent=True) or {}
        name = str(data.get("nome", data.get("name", ""))).strip()
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("senha", data.get("password", "")))

        if not name or not email or not password:
            return jsonify({"erro": "Nome, e-mail e senha são obrigatórios."}), 400
        if len(password) < 8:
            return jsonify({"erro": "A senha precisa ter pelo menos 8 caracteres."}), 400

        try:
            user = create_user(db, name, email, password)
        except ValueError as error:
            return jsonify({"erro": str(error)}), 400
        except sqlite3.IntegrityError:
            return jsonify({"erro": "Este e-mail já está cadastrado."}), 409
        user_id = user["id_usuario"]
        token = create_access_token(
            identity=str(user_id),
            additional_claims={"is_admin": bool(user.get("is_admin", 0))}
        )
        return jsonify({
            "mensagem": "Cadastro realizado com sucesso.",
            "token": token,
            "usuario": clean(user)
        }), 201

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("senha", data.get("password", "")))

        if not email or not password:
            return jsonify({"erro": "Informe e-mail e senha."}), 400

        user = db.fetch_one("SELECT * FROM usuarios WHERE email = ?", (email,))
        if not user or not check_password_hash(user["senha_hash"], password):
            return jsonify({"erro": "E-mail ou senha inválidos."}), 401
        if user.get("status") != "ativo":
            return jsonify({"erro": "Esta conta não está ativa."}), 403

        token = create_access_token(
            identity=str(user["id_usuario"]),
            additional_claims={"is_admin": bool(user.get("is_admin", 0))}
        )
        return jsonify({"token": token, "usuario": clean(user)})

    @app.get("/api/usuarios/me")
    @jwt_required()
    def profile():
        user_id = current_user_id()
        user = db.fetch_one("SELECT * FROM usuarios WHERE id_usuario = ?", (user_id,))
        if not user:
            return jsonify({"erro": "Usuário não encontrado."}), 404
        return jsonify(clean(user))

    @app.patch("/api/usuarios/me")
    @jwt_required()
    def update_profile():
        user_id = current_user_id()
        data = request.get_json(silent=True) or {}
        allowed = {
            key: value for key, value in data.items()
            if key in ("nome", "email")
        }
        if not allowed:
            return jsonify({"erro": "Informe nome ou e-mail para atualizar."}), 400
        if "email" in allowed:
            allowed["email"] = str(allowed["email"]).strip().lower()
        if "nome" in allowed:
            allowed["nome"] = str(allowed["nome"]).strip()
        user = db.fetch_one("SELECT * FROM usuarios WHERE id_usuario = ?", (user_id,))
        try:
            validate_profile(allowed.get("nome", user["nome"]), allowed.get("email", user["email"]))
        except ValueError as error:
            return jsonify({"erro": str(error)}), 400
        try:
            if not update_row("usuarios", "id_usuario", user_id, allowed):
                return jsonify({"erro": "Nenhum campo válido para atualização."}), 400
        except sqlite3.IntegrityError:
            return jsonify({"erro": "Este e-mail já está em uso."}), 409
        user = db.fetch_one("SELECT * FROM usuarios WHERE id_usuario = ?", (user_id,))
        return jsonify({"mensagem": "Perfil atualizado.", "usuario": clean(user)})

    @app.get("/api/usuarios/me/progresso")
    @jwt_required()
    def my_progress():
        user_id = current_user_id()
        missions = db.fetch_all(
            "SELECT * FROM progresso_missoes WHERE id_usuario = ?",
            (user_id,)
        )
        attempts = db.fetch_all(
            "SELECT * FROM tentativas_desafios WHERE id_usuario = ?",
            (user_id,)
        )
        return jsonify({
            "missoes": missions,
            "tentativas": attempts,
            "pontos": get_points(user_id)
        })

    @app.get("/api/jornadas")
    def list_journeys():
        return jsonify(db.fetch_all("SELECT * FROM jornadas WHERE status = 'publicada'"))

    @app.get("/api/jornadas/<int:jornada_id>/missoes")
    def list_journey_missions(jornada_id):
        journey = db.fetch_one(
            "SELECT * FROM jornadas WHERE id_jornada = ? AND status = 'publicada'", (jornada_id,)
        )
        if not journey:
            return jsonify({"erro": "Jornada não encontrada."}), 404
        missions = db.fetch_all(
            "SELECT * FROM missoes WHERE id_jornada = ? AND status = 'publicada' ORDER BY ordem", (jornada_id,)
        )
        return jsonify(missions)

    @app.get("/api/missoes/<int:mission_id>/desafios")
    def list_mission_challenges(mission_id):
        mission = db.fetch_one(
            "SELECT m.* FROM missoes m JOIN jornadas j USING (id_jornada) WHERE m.id_missao = ? AND m.status = 'publicada' AND j.status = 'publicada'", (mission_id,)
        )
        if not mission:
            return jsonify({"erro": "Missão não encontrada."}), 404
        challenges = db.fetch_all(
            "SELECT * FROM desafios WHERE id_missao = ? AND status = 'publicado'", (mission_id,)
        )
        return jsonify([clean_challenge(challenge) for challenge in challenges])

    @app.get("/api/conteudos")
    @jwt_required(optional=True)
    def list_content():
        contents = db.fetch_all("SELECT c.* FROM conteudos c LEFT JOIN missoes m USING (id_missao) LEFT JOIN jornadas j USING (id_jornada) WHERE c.status = 'publicado' AND (c.id_missao IS NULL OR (m.status = 'publicada' AND j.status = 'publicada'))")
        user_id = current_user_id() if get_jwt_identity() else None
        points = get_points(user_id)
        level_threshold = find_column("niveis", "pontos_minimos", "pontos_necessarios")
        current_level = 1
        if level_threshold:
            result = db.fetch_one(
                f"SELECT COUNT(*) AS total FROM niveis WHERE {level_threshold} <= ?",
                (points,)
            )
            current_level = max(1, int(result["total"]))

        for content in contents:
            required = content.get("nivel_requerido", content.get("nivel_minimo"))
            if required is None:
                required_id = content.get("id_nivel_requerido")
                required = required_id
            try:
                content["desbloqueado"] = required is None or current_level >= int(required)
            except (TypeError, ValueError):
                content["desbloqueado"] = True
            if not content["desbloqueado"]:
                for field in ("texto", "conteudo", "conteúdo", "corpo"):
                    content.pop(field, None)

        return jsonify(contents)

    @app.get("/api/conquistas")
    def list_achievements():
        return jsonify(db.fetch_all("SELECT * FROM conquistas WHERE status = 'ativa'"))

    @app.get("/api/ranking")
    def ranking():
        rows = db.fetch_all("SELECT v.id_usuario, v.nome, COALESCE(p.xp, v.pontos_totais) AS pontos_totais, CASE WHEN p.id_usuario IS NOT NULL THEN 'Nível ' || p.nivel ELSE v.nivel_atual END AS nivel_atual FROM vw_pontuacao_usuarios v JOIN usuarios u USING (id_usuario) LEFT JOIN progresso_jogo p USING (id_usuario) WHERE u.status = 'ativo'")
        possible_points = ("total_pontos", "pontos_totais", "pontuacao", "pontos")
        point_field = next(
            (field for field in possible_points if rows and field in rows[0]),
            None
        )
        if point_field:
            rows.sort(key=lambda row: row.get(point_field) or 0, reverse=True)
        return jsonify(rows[:20])

    @app.post("/api/missoes/<int:mission_id>/iniciar")
    @jwt_required()
    def start_mission(mission_id):
        try:
            result, status = game.start_mission(db, current_user_id(), mission_id)
            return jsonify(result), status
        except game.GameError as error:
            return jsonify(erro=str(error)), error.status

    @app.post("/api/missoes/<int:mission_id>/concluir")
    @jwt_required()
    def complete_mission(mission_id):
        try:
            return jsonify(game.complete_mission(db, current_user_id(), mission_id))
        except game.GameError as error:
            return jsonify(erro=str(error)), error.status

    @app.post("/api/desafios/<int:challenge_id>/tentativas")
    @jwt_required()
    def submit_challenge(challenge_id):
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(game.submit_challenge(db, current_user_id(), challenge_id, data.get("resposta", data.get("answer")))), 201
        except game.GameError as error:
            return jsonify(erro=str(error)), error.status

    @app.post("/api/conquistas/<int:achievement_id>/compartilhar")
    @jwt_required()
    def share_achievement(achievement_id):
        user_id = current_user_id()
        achievement = db.fetch_one(
            "SELECT * FROM conquistas WHERE id_conquista = ?", (achievement_id,)
        )
        if not achievement:
            return jsonify({"erro": "Conquista não encontrada."}), 404

        unlocked = db.fetch_one(
            "SELECT 1 AS encontrado FROM usuarios_conquistas "
            "WHERE id_usuario = ? AND id_conquista = ?",
            (user_id, achievement_id)
        )
        if not unlocked:
            return jsonify({"erro": "Você ainda não desbloqueou esta conquista."}), 403

        data = request.get_json(silent=True) or {}
        platform = str(data.get("plataforma", "link")).strip()
        if not platform or len(platform) > 100:
            return jsonify(erro="Informe uma plataforma com até 100 caracteres."), 400
        share_link = request.url_root.rstrip("/") + "/nexa-quest"
        share_data = {"id_usuario": user_id, "id_conquista": achievement_id,
                      "plataforma": platform, "url_compartilhada": share_link}

        try:
            share_id = insert_row("compartilhamentos", share_data)
        except (sqlite3.Error, ValueError) as error:
            return jsonify({"erro": "Não foi possível compartilhar a conquista.", "detalhe": str(error)}), 500

        return jsonify({
            "mensagem": "Conquista compartilhada.",
            "link": share_link,
            "id_compartilhamento": share_id
        }), 201

    @app.route("/api/admin/<string:resource>", methods=["GET", "POST"])
    @jwt_required()
    def admin_list_create(resource):
        error = admin_error()
        if error:
            return error
        if resource not in ADMIN_RESOURCES:
            return jsonify({"erro": "Recurso administrativo inválido."}), 404

        table, id_field = ADMIN_RESOURCES[resource]

        if request.method == "GET":
            records = db.fetch_all(f"SELECT * FROM {table}")
            return jsonify([clean(record) for record in records])

        data = request.get_json(silent=True) or {}
        if resource == "usuarios":
            password = str(data.get("senha", data.get("password", "")))
            name = str(data.get("nome", "")).strip()
            email = str(data.get("email", "")).strip().lower()
            if not name or not email or len(password) < 8:
                return jsonify({"erro": "Informe nome, e-mail e senha com pelo menos 8 caracteres."}), 400
            data = {
                "nome": name,
                "email": email,
                "senha_hash": generate_password_hash(password),
                "status": "ativo",
                "is_admin": 0
            }

        try:
            record_id = insert_row(table, data)
        except sqlite3.IntegrityError:
            return jsonify({"erro": "Já existe um registro com esses dados."}), 409
        except (sqlite3.Error, ValueError) as error:
            return jsonify({"erro": "Não foi possível criar o registro.", "detalhe": str(error)}), 400

        record = db.fetch_one(f"SELECT * FROM {table} WHERE {id_field} = ?", (record_id,))
        return jsonify(clean(record)), 201

    @app.route("/api/admin/<string:resource>/<int:record_id>", methods=["GET", "PUT", "PATCH", "DELETE"])
    @jwt_required()
    def admin_read_update_delete(resource, record_id):
        error = admin_error()
        if error:
            return error
        if resource not in ADMIN_RESOURCES:
            return jsonify({"erro": "Recurso administrativo inválido."}), 404

        table, id_field = ADMIN_RESOURCES[resource]
        record = db.fetch_one(
            f"SELECT * FROM {table} WHERE {id_field} = ?", (record_id,)
        )
        if not record:
            return jsonify({"erro": "Registro não encontrado."}), 404

        if request.method == "GET":
            return jsonify(clean(record))

        if request.method in ("PUT", "PATCH"):
            data = request.get_json(silent=True) or {}
            try:
                if resource == "usuarios":
                    data.pop("is_admin", None)
                    data.pop("senha_hash", None)
                    data.pop("password_hash", None)
                updated = update_row(table, id_field, record_id, data)
                if not updated:
                    return jsonify({"erro": "Nenhum campo válido para atualizar."}), 400
            except sqlite3.IntegrityError:
                return jsonify({"erro": "Já existe um registro com esses dados."}), 409
            updated_record = db.fetch_one(
                f"SELECT * FROM {table} WHERE {id_field} = ?", (record_id,)
            )
            return jsonify(clean(updated_record))

        if resource == "usuarios" and record_id == current_user_id():
            return jsonify({"erro": "Não é permitido excluir a própria conta administrativa por esta rota."}), 400

        try:
            db.execute(f"DELETE FROM {table} WHERE {id_field} = ?", (record_id,))
        except sqlite3.IntegrityError:
            return jsonify({"erro": "Não é possível excluir este registro porque há dados relacionados."}), 409
        return jsonify({"mensagem": "Registro excluído com sucesso."})