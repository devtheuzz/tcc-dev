import secrets
import sqlite3
from functools import wraps
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from .auth import authenticate, create_user, validate_profile
from .game import GameError, complete_mission, start_mission, submit_challenge, summary

web = Blueprint('web', __name__)
PAGES = {'index.html': 'home', 'explorar.html': 'explorar', 'sobre-nos.html': 'sobre', 'personalizar.html': 'personalizar', 'nexa-quest.html': 'quest', 'fale-com-a-gente.html': 'contato', 'login.html': 'login', 'cadastro.html': 'cadastro'}


def database():
    return current_app.extensions['db']


def csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


def safe_next(value):
    if value in PAGES:
        return url_for('web.' + PAGES[value])
    # Somente URLs produzidas pelas páginas internas, sem domínio ou barras duplas.
    allowed = {'/', '/explorar', '/sobre-nos', '/personalizar', '/nexa-quest'}
    if value in allowed:
        return value
    if value and value.startswith('/jornadas/') and value.removeprefix('/jornadas/').isdigit():
        return value
    return url_for('web.home')


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for('web.login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


@web.before_app_request
def load_user():
    g.user = None
    if session.get('user_id'):
        g.user = database().fetch_one('SELECT id_usuario, nome, email FROM usuarios WHERE id_usuario = ? AND status = ?', (session['user_id'], 'ativo'))
        if not g.user:
            session.clear()
    if request.blueprint == 'web' and request.method == 'POST':
        token = request.form.get('csrf_token', '')
        if not token or not secrets.compare_digest(token, session.get('csrf_token', '')):
            abort(400)


@web.app_context_processor
def context():
    user = g.get('user')
    return {'user': user, 'stats': summary(database(), user['id_usuario'] if user else None), 'csrf_token': csrf_token}


@web.get('/')
def home():
    return render_template('index.html', title='Início', page='inicio')


@web.get('/explorar')
def explorar():
    journeys = database().fetch_all("SELECT * FROM jornadas WHERE status = 'publicada' ORDER BY id_jornada")
    return render_template('explorar.html', title='Explorar', page='explorar', journeys=journeys)


@web.get('/sobre-nos')
def sobre():
    return render_template('sobre-nos.html', title='Sobre nós', page='sobre')


@web.get('/nexa-quest')
def quest():
    return render_template('nexa-quest.html', title='Nexa Quest', page='nexa-quest')


@web.route('/personalizar', methods=['GET', 'POST'])
@login_required
def personalizar():
    if request.method == 'POST':
        try:
            name, email = validate_profile(request.form.get('name', ''), request.form.get('email', ''))
            database().execute('UPDATE usuarios SET nome = ?, email = ? WHERE id_usuario = ?', (name, email, g.user['id_usuario']))
        except ValueError as error:
            flash(str(error), 'error')
        except sqlite3.IntegrityError:
            flash('Este e-mail já está em uso.', 'error')
        else:
            flash('Perfil atualizado.', 'success')
        return redirect(url_for('web.personalizar'))
    return render_template('personalizar.html', title='Personalizar', page='personalizar')


def auth_page(register=False):
    template = 'cadastro.html' if register else 'login.html'
    next_url = safe_next(request.form.get('next') or request.args.get('next') or request.args.get('redirect'))
    if g.user:
        return redirect(next_url)
    error = None
    status = 200
    if request.method == 'POST':
        try:
            if register:
                user = create_user(database(), request.form.get('name', ''), request.form.get('email', ''), request.form.get('password', ''))
            else:
                user = authenticate(database(), request.form.get('email', ''), request.form.get('password', ''))
                if not user:
                    raise ValueError('E-mail ou senha inválidos, ou conta inativa.')
        except ValueError as exc:
            error, status = str(exc), 400 if register else 401
        except sqlite3.IntegrityError:
            error, status = 'Este e-mail já está cadastrado.', 409
        else:
            session.clear()
            session['user_id'] = user['id_usuario']
            session.permanent = True
            return redirect(next_url)
    return render_template(template, title='Criar conta' if register else 'Entrar', layout='auth', next_url=next_url, error=error), status


@web.route('/login', methods=['GET', 'POST'])
def login():
    return auth_page()


@web.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    return auth_page(register=True)


@web.post('/sair')
def logout():
    session.clear()
    return redirect(url_for('web.home'))


@web.route('/fale-com-a-gente', methods=['GET', 'POST'])
def contato():
    error = None
    if request.method == 'POST':
        try:
            name, email = validate_profile(request.form.get('name', ''), request.form.get('email', ''))
            subject, message = request.form.get('subject', '').strip(), request.form.get('message', '').strip()
            if not 1 <= len(subject) <= 150 or not 1 <= len(message) <= 5000:
                raise ValueError('Informe um assunto com até 150 caracteres e uma mensagem com até 5000 caracteres.')
            database().execute('INSERT INTO mensagens_contato (nome, email, assunto, mensagem) VALUES (?, ?, ?, ?)', (name, email, subject, message))
        except ValueError as exc:
            error = str(exc)
        else:
            flash('Mensagem registrada com sucesso. Obrigado pelo contato!', 'success')
            return redirect(url_for('web.contato'))
    return render_template('fale-com-a-gente.html', title='Fale com a gente', layout='contact', error=error), 400 if error else 200


@web.get('/jornadas/<int:journey_id>')
def journey(journey_id):
    db = database()
    journey = db.fetch_one("SELECT * FROM jornadas WHERE id_jornada = ? AND status = 'publicada'", (journey_id,))
    if not journey:
        abort(404)
    missions = db.fetch_all("SELECT * FROM missoes WHERE id_jornada = ? AND status = 'publicada' ORDER BY ordem", (journey_id,))
    for mission in missions:
        mission['challenges'] = db.fetch_all("SELECT id_desafio, titulo, descricao, pontos_recompensa FROM desafios WHERE id_missao = ? AND status = 'publicado'", (mission['id_missao'],))
        mission['contents'] = db.fetch_all("SELECT * FROM conteudos WHERE id_missao = ? AND status = 'publicado'", (mission['id_missao'],))
        mission['progress'] = db.fetch_one('SELECT * FROM progresso_missoes WHERE id_usuario = ? AND id_missao = ?', (g.user['id_usuario'], mission['id_missao'])) if g.user else None
    return render_template('jornada.html', title=journey['titulo'], page='explorar', journey=journey, missions=missions)


@web.post('/missoes/<int:mission_id>/<action>')
@login_required
def mission_action(mission_id, action):
    try:
        if action == 'iniciar':
            result, _status = start_mission(database(), g.user['id_usuario'], mission_id)
        elif action == 'concluir':
            result = complete_mission(database(), g.user['id_usuario'], mission_id)
        else:
            abort(404)
        flash(result['mensagem'], 'success')
    except GameError as error:
        flash(str(error), 'error')
    mission = database().fetch_one('SELECT id_jornada FROM missoes WHERE id_missao = ?', (mission_id,))
    return redirect(url_for('web.journey', journey_id=mission['id_jornada']) if mission else url_for('web.explorar'))


@web.post('/desafios/<int:challenge_id>/responder')
@login_required
def challenge_action(challenge_id):
    try:
        result = submit_challenge(database(), g.user['id_usuario'], challenge_id, request.form.get('answer', ''))
        flash(f"Resposta correta! +{result['pontos_ganhos']} XP" if result['correto'] else 'Ainda não. Tente novamente.', 'success' if result['correto'] else 'error')
    except GameError as error:
        flash(str(error), 'error')
    challenge = database().fetch_one('SELECT m.id_jornada FROM desafios d JOIN missoes m USING (id_missao) WHERE d.id_desafio = ?', (challenge_id,))
    return redirect(url_for('web.journey', journey_id=challenge['id_jornada']) if challenge else url_for('web.explorar'))


@web.get('/<page>.html')
def legacy(page):
    endpoint = PAGES.get(page + '.html')
    if not endpoint:
        abort(404)
    target = url_for('web.' + endpoint)
    if endpoint in ('login', 'cadastro'):
        target = url_for('web.' + endpoint, next=safe_next(request.args.get('redirect') or request.args.get('next')))
    return redirect(target, code=302)
