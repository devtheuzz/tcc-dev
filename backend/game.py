from datetime import datetime, timezone

class GameError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

def unlock_achievements(connection, user_id):
    points = connection.execute('SELECT COALESCE(SUM(quantidade), 0) FROM historico_pontos WHERE id_usuario = ?', (user_id,)).fetchone()[0]
    missions = connection.execute("SELECT COUNT(*) FROM progresso_missoes WHERE id_usuario = ? AND status = 'concluida'", (user_id,)).fetchone()[0]
    challenges = connection.execute("SELECT COUNT(DISTINCT id_desafio) FROM tentativas_desafios WHERE id_usuario = ? AND resultado = 'aprovada'", (user_id,)).fetchone()[0]
    journeys = connection.execute("""SELECT COUNT(*) FROM jornadas j WHERE j.status = 'publicada'
        AND EXISTS (SELECT 1 FROM missoes m WHERE m.id_jornada = j.id_jornada AND m.status = 'publicada')
        AND NOT EXISTS (SELECT 1 FROM missoes m WHERE m.id_jornada = j.id_jornada AND m.status = 'publicada'
            AND NOT EXISTS (SELECT 1 FROM progresso_missoes p WHERE p.id_usuario = ? AND p.id_missao = m.id_missao AND p.status = 'concluida'))""", (user_id,)).fetchone()[0]
    values = {'pontos_acumulados': points, 'missoes_concluidas': missions, 'desafios_aprovados': challenges, 'jornadas_concluidas': journeys}
    unlocked = []
    for row in connection.execute("SELECT * FROM conquistas WHERE status = 'ativa'").fetchall():
        if row['criterio'] in values and values[row['criterio']] >= row['valor_criterio']:
            cursor = connection.execute('INSERT OR IGNORE INTO usuarios_conquistas (id_usuario, id_conquista) VALUES (?, ?)', (user_id, row['id_conquista']))
            if cursor.rowcount:
                unlocked.append(dict(row))
    return points, unlocked


def published_mission(connection, mission_id):
    mission = connection.execute("""SELECT m.* FROM missoes m JOIN jornadas j USING (id_jornada)
        WHERE m.id_missao = ? AND m.status = 'publicada' AND j.status = 'publicada'""", (mission_id,)).fetchone()
    if not mission:
        raise GameError('Missão não encontrada.', 404)
    return mission


def start_mission(db, user_id, mission_id):
    with db.transaction() as connection:
        connection.execute('BEGIN IMMEDIATE')
        published_mission(connection, mission_id)
        cursor = connection.execute('INSERT OR IGNORE INTO progresso_missoes (id_usuario, id_missao) VALUES (?, ?)', (user_id, mission_id))
        created = bool(cursor.rowcount)
        progress = dict(connection.execute('SELECT * FROM progresso_missoes WHERE id_usuario = ? AND id_missao = ?', (user_id, mission_id)).fetchone())
    return {'mensagem': 'Missão iniciada.' if created else 'A missão já foi iniciada.', 'progresso': progress}, 201 if created else 200


def complete_mission(db, user_id, mission_id):
    with db.transaction() as connection:
        connection.execute('BEGIN IMMEDIATE')
        mission = published_mission(connection, mission_id)
        progress = connection.execute('SELECT * FROM progresso_missoes WHERE id_usuario = ? AND id_missao = ?', (user_id, mission_id)).fetchone()
        if not progress:
            raise GameError('Inicie a missão antes de concluir.')
        if progress['status'] == 'concluida':
            raise GameError('Esta missão já foi concluída.', 409)
        pending = connection.execute("""SELECT 1 FROM desafios d WHERE d.id_missao = ? AND d.status = 'publicado'
            AND NOT EXISTS (SELECT 1 FROM tentativas_desafios t WHERE t.id_desafio = d.id_desafio AND t.id_usuario = ? AND t.resultado = 'aprovada') LIMIT 1""", (mission_id, user_id)).fetchone()
        if pending:
            raise GameError('Conclua os desafios publicados antes de finalizar a missão.', 409)
        connection.execute("UPDATE progresso_missoes SET status = 'concluida', data_conclusao = ? WHERE id_progresso = ?", (datetime.now(timezone.utc).isoformat(), progress['id_progresso']))
        points = mission['pontos_recompensa']
        if points:
            connection.execute('INSERT INTO historico_pontos (id_usuario, quantidade, motivo) VALUES (?, ?, ?)', (user_id, points, f'Conclusão da missão {mission_id}'))
        total, unlocked = unlock_achievements(connection, user_id)
    return {'mensagem': 'Missão concluída.', 'pontos_ganhos': points, 'pontos_totais': total, 'conquistas_desbloqueadas': unlocked}


def submit_challenge(db, user_id, challenge_id, answer):
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 10000:
        raise GameError('Informe uma resposta com até 10000 caracteres.')
    with db.transaction() as connection:
        connection.execute('BEGIN IMMEDIATE')
        challenge = connection.execute("SELECT * FROM desafios WHERE id_desafio = ? AND status = 'publicado'", (challenge_id,)).fetchone()
        if not challenge:
            raise GameError('Desafio não encontrado.', 404)
        published_mission(connection, challenge['id_missao'])
        if not connection.execute('SELECT 1 FROM progresso_missoes WHERE id_usuario = ? AND id_missao = ?', (user_id, challenge['id_missao'])).fetchone():
            raise GameError('Inicie a missão antes de responder.')
        if connection.execute("SELECT 1 FROM tentativas_desafios WHERE id_usuario = ? AND id_desafio = ? AND resultado = 'aprovada'", (user_id, challenge_id)).fetchone():
            raise GameError('Você já concluiu este desafio corretamente.', 409)
        expected = challenge['resposta_correta']
        if expected is None or not expected.strip():
            raise GameError('Este desafio ainda não possui correção automática configurada.', 409)
        correct = answer.strip().casefold() == expected.strip().casefold()
        points = challenge['pontos_recompensa'] if correct else 0
        cursor = connection.execute('''INSERT INTO tentativas_desafios
            (id_usuario, id_desafio, resposta, resultado, pontos_obtidos, validada_por_sistema)
            VALUES (?, ?, ?, ?, ?, 1)''', (user_id, challenge_id, answer, 'aprovada' if correct else 'reprovada', points))
        if points:
            connection.execute('INSERT INTO historico_pontos (id_usuario, id_tentativa, quantidade, motivo) VALUES (?, ?, ?, ?)', (user_id, cursor.lastrowid, points, f'Conclusão do desafio {challenge_id}'))
        total, unlocked = unlock_achievements(connection, user_id)
    return {'correto': correct, 'pontos_ganhos': points, 'pontos_totais': total, 'conquistas_desbloqueadas': unlocked}


def summary(db, user_id):
    if user_id:
        from .game_api import read_progress
        remote = read_progress(db, user_id)
        if remote['sincronizado']:
            return {'points': remote['xp'], 'level': f"Nível {remote['nivel']}",
                    'level_number': remote['nivel'], 'next_level': None, 'percent': None,
                    'achievements': remote['conquistas'], 'source': 'jogo',
                    'updated_at': remote['atualizado_em']}
    points = db.fetch_one('SELECT COALESCE(SUM(quantidade), 0) AS total FROM historico_pontos WHERE id_usuario = ?', (user_id,))['total'] if user_id else 0
    levels = db.fetch_all('SELECT * FROM niveis ORDER BY pontos_minimos')
    eligible = [level for level in levels if level['pontos_minimos'] <= points]
    current = eligible[-1] if eligible else {'nome': 'Iniciante', 'pontos_minimos': 0}
    next_level = next((level for level in levels if level['pontos_minimos'] > points), None)
    achievements = db.fetch_all('SELECT c.* FROM conquistas c JOIN usuarios_conquistas uc USING (id_conquista) WHERE uc.id_usuario = ? ORDER BY uc.data_desbloqueio', (user_id,)) if user_id else []
    progress = round(100 * (points-current['pontos_minimos']) / (next_level['pontos_minimos']-current['pontos_minimos'])) if next_level else 100
    return {'points': points, 'level': current['nome'], 'level_number': max(1, len(eligible)), 'next_level': next_level, 'percent': max(0, min(100, progress)), 'achievements': achievements, 'source': 'site', 'updated_at': None}
