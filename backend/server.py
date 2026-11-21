import os
import secrets
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .database_manager import SQLManager
from .api import register_api
from .web import web
from .commands import register_commands
from .game_api import api as game_api

BASE_DIR = Path(__file__).resolve().parent

def create_app(test_config=None):
    load_dotenv(BASE_DIR / '.env')
    app = Flask(__name__, instance_path=str(BASE_DIR / 'instance'))
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY') or os.getenv('JWT_SECRET_KEY'),
        JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY') or os.getenv('SECRET_KEY'),
        DATABASE=os.getenv('DATABASE', str(BASE_DIR / 'instance' / 'nexadb.db')),
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=float(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '2'))),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE', '0') == '1',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        methods=['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allow_headers='*',
        send_wildcard=True,
        supports_credentials=False,
        max_age=600,
    )
    if not app.config['SECRET_KEY']:
        secret_path = BASE_DIR / 'instance' / 'secret_key'
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(secret_path, 'x', encoding='utf-8', opener=lambda path, flags: os.open(path, flags, 0o600)) as file:
                file.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        app.config['SECRET_KEY'] = secret_path.read_text().strip()
    app.config['JWT_SECRET_KEY'] = app.config['JWT_SECRET_KEY'] or app.config['SECRET_KEY']
    db_path = Path(app.config['DATABASE'])
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path
    db = SQLManager(db_path)
    db.init()
    app.extensions['db'] = db
    jwt = JWTManager(app)

    @jwt.token_in_blocklist_loader
    def inactive_user(_header, payload):
        user = db.fetch_one('SELECT status FROM usuarios WHERE id_usuario = ?', (payload['sub'],))
        return not user or user['status'] != 'ativo'

    @app.before_request
    def validate_json():
        # O preflight não tem corpo JSON nem precisa de autenticação.
        if request.method == 'OPTIONS':
            return None
        if request.path.startswith('/api/') and request.is_json:
            if not isinstance(request.get_json(silent=True), dict):
                return jsonify(erro='Envie um objeto JSON válido.'), 400

    register_api(app, db)
    app.register_blueprint(game_api)
    app.register_blueprint(web)
    register_commands(app)

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    @app.errorhandler(500)
    def handle_error(error):
        status = error.code
        messages = {400: 'Solicitação inválida. Atualize a página e tente novamente.', 404: 'Página ou recurso não encontrado.', 405: 'Método não permitido.', 413: 'O conteúdo enviado é muito grande.', 500: 'Erro interno do servidor.'}
        if request.path.startswith('/api/'):
            return jsonify(erro=messages[status]), status
        return render_template('erro.html', title=f'Erro {status}', status=status, message=messages[status]), status

    @app.after_request
    def private_pages(response):
        if request.path.startswith('/api/') or (request.endpoint and request.endpoint.startswith('web.')):
            response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    return app
