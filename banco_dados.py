from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Configuração do banco (SQLite local, pode trocar por MySQL/Postgres)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///licencas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS ---
class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=True)

    licenca = db.relationship("Licenca", backref="usuario", uselist=False)


class Licenca(db.Model):
    __tablename__ = "licencas"
    id = db.Column(db.Integer, primary_key=True)
    maquina_id = db.Column(db.String(100), unique=True, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    licenca_codificada = db.Column(db.String(200), nullable=False)  # ex: "22000628|2b15946161e4"
    status = db.Column(db.String(20), default="ativa")


class Pagamento(db.Model):
    __tablename__ = "pagamentos"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    data_pagamento = db.Column(db.DateTime, default=datetime.now)


def importar_licenca_txt(caminho):
    with open(caminho, "r") as f:
        linhas = f.readlines()

    for linha in linhas:
        email, dados = linha.strip().split("=")
        maquina_id, parte1, parte2 = dados.split("|")
        licenca_codificada = f"{parte1}|{parte2}"

        # Verifica se já existe usuário com esse email
        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            usuario = Usuario(email=email, nome="Desconhecido")
            db.session.add(usuario)
            db.session.commit()

        # Verifica se já existe licença com esse maquina_id
        licenca = Licenca.query.filter_by(maquina_id=maquina_id).first()
        if not licenca:
            licenca = Licenca(
                maquina_id=maquina_id,
                usuario_id=usuario.id,
                licenca_codificada=licenca_codificada,
                status="ativa"
            )
            db.session.add(licenca)
        else:
            licenca.licenca_codificada = licenca_codificada
            licenca.status = "ativa"

        db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Banco de dados criado com sucesso!")
