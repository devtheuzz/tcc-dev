import sqlite3
import click
from flask import current_app
from .auth import create_user

def register_commands(app):
    @app.cli.command('create-admin')
    @click.option('--name', prompt='Nome')
    @click.option('--email', prompt='E-mail')
    @click.option('--password', prompt='Senha', hide_input=True, confirmation_prompt=True)
    def create_admin(name, email, password):
        """Cria uma conta administrativa com senha definida pelo responsável."""
        db = current_app.extensions['db']
        try:
            user = create_user(db, name, email, password)
        except (ValueError, sqlite3.IntegrityError) as error:
            raise click.ClickException(str(error)) from error
        db.execute('UPDATE usuarios SET is_admin = 1 WHERE id_usuario = ?', (user['id_usuario'],))
        click.echo('Administrador criado.')

    @app.cli.command('seed-demo')
    def seed_demo():
        """Adiciona uma jornada de exemplo para testar o fluxo de aprendizagem."""
        db = current_app.extensions['db']
        with db.transaction() as connection:
            connection.execute('BEGIN IMMEDIATE')
            if connection.execute("SELECT 1 FROM jornadas WHERE titulo = 'Primeiros passos em Python'").fetchone():
                click.echo('A jornada de exemplo já existe.')
                return
            journey_id = connection.execute("INSERT INTO jornadas (titulo, descricao, status) VALUES (?, ?, 'publicada')", ('Primeiros passos em Python', 'Jornada de exemplo para testar missões, XP e conquistas.')).lastrowid
            mission_id = connection.execute("INSERT INTO missoes (id_jornada, titulo, descricao, ordem, pontos_recompensa, status) VALUES (?, ?, ?, 1, 90, 'publicada')", (journey_id, 'Sua primeira saída de texto', 'Leia o material e resolva o desafio.')).lastrowid
            connection.execute("INSERT INTO conteudos (id_missao, titulo, descricao, status) VALUES (?, ?, ?, 'publicado')", (mission_id, 'Exibir uma mensagem', 'Em Python, a função print exibe uma mensagem. Exemplo: print("Olá, mundo!").'))
            connection.execute("INSERT INTO desafios (id_missao, titulo, descricao, tipo, resposta_correta, pontos_recompensa, status) VALUES (?, ?, ?, 'pergunta', 'print', 10, 'publicado')", (mission_id, 'Qual é a função?', 'Digite apenas o nome da função que exibe uma mensagem em Python.'))
        click.echo('Jornada de exemplo criada. Acesse /explorar.')
