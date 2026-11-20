import re
from werkzeug.security import check_password_hash, generate_password_hash

def validate_profile(name, email):
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise ValueError("Informe um nome com até 100 caracteres.")
    if not isinstance(email, str) or len(email.strip()) > 150 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()):
        raise ValueError("Informe um e-mail válido com até 150 caracteres.")
    return name.strip(), email.strip().lower()


def create_user(db, name, email, password):
    name, email = validate_profile(name, email)
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise ValueError("A senha precisa ter entre 8 e 128 caracteres.")
    result = db.execute(
        "INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    return db.fetch_one("SELECT * FROM usuarios WHERE id_usuario = ?", (result["last_insert_id"],))


def authenticate(db, email, password):
    if not isinstance(email, str) or not isinstance(password, str) or len(password) > 128:
        return None
    user = db.fetch_one("SELECT * FROM usuarios WHERE email = ?", (email.strip().lower(),))
    if user and user["status"] == "ativo" and check_password_hash(user["senha_hash"], password):
        return user
    return None
