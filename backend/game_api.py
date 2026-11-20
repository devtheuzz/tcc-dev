import json
import re
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

api = Blueprint('game_api', __name__, url_prefix='/api/jogo')
MAX_XP = 2_147_483_647
MAX_LEVEL = 100_000
MAX_ACHIEVEMENTS = 200
CODE = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}')

def validate_payload(data):
    if not isinstance(data, dict):
        raise ValueError('Envie um objeto JSON válido.')
    unknown = set(data) - {'nivel', 'xp', 'conquistas', 'versao'}
    if unknown:
        raise ValueError('Campos desconhecidos: ' + ', '.join(sorted(unknown)) + '.')
    for field, minimum, maximum in [('nivel', 1, MAX_LEVEL), ('xp', 0, MAX_XP), ('versao', 1, MAX_XP)]:
        value = data.get(field)
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f'{field} precisa ser um inteiro entre {minimum} e {maximum}.')
    achievements = data.get('conquistas')
    if not isinstance(achievements, list) or len(achievements) > MAX_ACHIEVEMENTS:
        raise ValueError(f'conquistas precisa ser uma lista com até {MAX_ACHIEVEMENTS} itens.')
    normalized, seen = [], set()
    for achievement in achievements:
        if not isinstance(achievement, dict) or set(achievement) - {'codigo', 'nome', 'descricao'}:
            raise ValueError('Cada conquista deve ter codigo, nome e descricao opcional.')
        code = achievement.get('codigo')
        name = achievement.get('nome')
        description = achievement.get('descricao', '')
        if not isinstance(code, str) or not CODE.fullmatch(code):
            raise ValueError('codigo deve ter de 1 a 80 letras, números, pontos, hífens ou sublinhados, iniciando com letra ou número.')
        if code in seen:
            raise ValueError('Não repita o codigo de uma conquista no mesmo envio.')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise ValueError('O nome da conquista precisa ter de 1 a 100 caracteres.')
        if not isinstance(description, str) or len(description.strip()) > 500:
            raise ValueError('A descricao da conquista precisa ter até 500 caracteres.')
        seen.add(code)
        normalized.append({'codigo': code, 'nome': name.strip(), 'descricao': description.strip()})
    normalized.sort(key=lambda item: item['codigo'])
    return {'nivel': data['nivel'], 'xp': data['xp'], 'versao': data['versao'], 'conquistas': normalized}


def read_progress(db, user_id):
    row = db.fetch_one('SELECT nivel, xp, versao, atualizado_em FROM progresso_jogo WHERE id_usuario = ?', (user_id,))
    if not row:
        return {'usuario_id': user_id, 'sincronizado': False, 'nivel': 1, 'xp': 0, 'versao': 0, 'conquistas': [], 'atualizado_em': None}
    achievements = db.fetch_all('SELECT codigo, nome, descricao FROM conquistas_jogo WHERE id_usuario = ? ORDER BY codigo', (user_id,))
    return {'usuario_id': user_id, 'sincronizado': True, **row, 'conquistas': achievements}


@api.get('/progresso')
@jwt_required()
def get_progress():
    """Consulta o último estado enviado para a conta autenticada."""
    return jsonify(read_progress(current_app.extensions['db'], int(get_jwt_identity())))


@api.post('/progresso')
@jwt_required()
def sync_progress():
    """Substitui o estado completo. Versões antigas são rejeitadas."""
    if not request.is_json:
        return jsonify(erro='Envie Content-Type: application/json.'), 415
    try:
        progress = validate_payload(request.get_json(silent=True))
    except ValueError as error:
        return jsonify(erro=str(error)), 400
    user_id = int(get_jwt_identity())
    db = current_app.extensions['db']
    with db.transaction() as connection:
        connection.execute('BEGIN IMMEDIATE')
        previous = connection.execute('SELECT nivel, xp, versao FROM progresso_jogo WHERE id_usuario = ?', (user_id,)).fetchone()
        repeated = False
        if previous:
            if progress['versao'] < previous['versao']:
                return jsonify(erro='Versão antiga. Consulte o progresso e envie uma versão maior.', versao_atual=previous['versao']), 409
            if progress['versao'] == previous['versao']:
                achievements = [dict(row) for row in connection.execute('SELECT codigo, nome, descricao FROM conquistas_jogo WHERE id_usuario = ? ORDER BY codigo', (user_id,)).fetchall()]
                if previous['nivel'] != progress['nivel'] or previous['xp'] != progress['xp'] or achievements != progress['conquistas']:
                    return jsonify(erro='Esta versão já foi usada com outros dados.', versao_atual=previous['versao']), 409
                repeated = True
        if not repeated:
            connection.execute('''INSERT INTO progresso_jogo (id_usuario, nivel, xp, versao)
                VALUES (?, ?, ?, ?) ON CONFLICT(id_usuario) DO UPDATE SET
                nivel = excluded.nivel, xp = excluded.xp, versao = excluded.versao,
                atualizado_em = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')''',
                (user_id, progress['nivel'], progress['xp'], progress['versao']))
            connection.execute('DELETE FROM conquistas_jogo WHERE id_usuario = ?', (user_id,))
            connection.executemany('INSERT INTO conquistas_jogo (id_usuario, codigo, nome, descricao) VALUES (?, ?, ?, ?)',
                [(user_id, item['codigo'], item['nome'], item['descricao']) for item in progress['conquistas']])
        # A resposta é montada sob o mesmo bloqueio para refletir esta gravação.
        saved = dict(connection.execute('SELECT nivel, xp, versao, atualizado_em FROM progresso_jogo WHERE id_usuario = ?', (user_id,)).fetchone())
        saved.update(usuario_id=user_id, sincronizado=True, conquistas=progress['conquistas'])
    response = jsonify(mensagem='Progresso já recebido.' if repeated else 'Progresso sincronizado.', repetido=repeated, progresso=saved)
    return response, 200
