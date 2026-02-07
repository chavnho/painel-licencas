from flask import Blueprint, request, render_template_string, redirect, url_for, send_file, jsonify
from banco_dados import app, db, Usuario, Licenca
from layouts import html_layout
from utils import carregar_licencas, processar_pagamento, calcular_validade_por_valor, codificar_data, gerar_hash, chave_secreta
from datetime import datetime

caminho_licencas = "licencas.txt"

pendentes_alteracao = {}

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/")
def admin_index():
    licencas = carregar_licencas()
    return render_template_string(html_layout, licencas=licencas, mensagem="")


@admin_bp.route("/gerar", methods=["POST"])
def gerar():
    email = request.form.get("email")
    id_maquina = request.form.get("id")
    valor_str = request.form.get("valor", "")
    valor_pago = int(valor_str) if valor_str.isdigit() else 0

    ok, resultado = processar_pagamento(email, id_maquina, valor_pago)
    if not ok:
        licencas = carregar_licencas()
        return render_template_string(html_layout, licencas=licencas, mensagem=resultado)

    return redirect(url_for("admin.admin_index"))


@admin_bp.route("/download")
def download_licenca():
    id_maquina = request.args.get("id")  # cliente envia ?id=ID_MAQUINA
    licenca = Licenca.query.filter_by(maquina_id=id_maquina).first()

    if not licenca:
        return jsonify({
            "status": "expirada",
            "validade": None,
            "dias_restantes": 0
        })

    validade = licenca.validade.strftime("%Y-%m-%d")
    dias_restantes = (licenca.validade - datetime.now().date()).days

    status = "ok" if dias_restantes > 0 else "expirada"
    if dias_restantes < 0:
        dias_restantes = 0

    return jsonify({
        "status": status,
        "validade": validade,
        "dias_restantes": dias_restantes
    })



@admin_bp.route("/registrar", methods=["POST"])
def registrar():
    email = request.form.get("email")
    id_maquina = request.form.get("id")

    with app.app_context():
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.licenca:
            if usuario.licenca.maquina_id != id_maquina:
                # 👉 Não atualiza automaticamente, retorna aviso
                return jsonify({
                    "status": "duplicado",
                    "mensagem": f"⚠️ O email {email} já possui licença vinculada à máquina {usuario.licenca.maquina_id}. Confirme alteração antes de atualizar."
                })

        # Se não existe → cria nova licença
        validade = calcular_validade_por_valor(0)
        data_codificada = codificar_data(validade)
        base = id_maquina + data_codificada + chave_secreta
        hash_final = gerar_hash(base)

        if not usuario:
            usuario = Usuario(email=email, nome="Desconhecido")
            db.session.add(usuario)
            db.session.commit()

        if not usuario.licenca:
            nova_licenca = Licenca(
                maquina_id=id_maquina,
                usuario_id=usuario.id,
                licenca_codificada=f"{data_codificada}|{hash_final}",
                status="ativa"
            )
            db.session.add(nova_licenca)
            db.session.commit()

    return jsonify({
        "status": "ok",
        "mensagem": "✅ Registro recebido. Aguarde liberação pelo painel.",
        "licenca": f"{data_codificada}|{hash_final}"
    })


@admin_bp.route("/excluir", methods=["POST"])
def excluir():
    id_maquina = request.form.get("id")

    if not id_maquina:
        return redirect(url_for("admin.admin_index"))

    with app.app_context():
        licenca = Licenca.query.filter_by(maquina_id=id_maquina).first()
        if licenca:
            db.session.delete(licenca)
            db.session.commit()
            print(f"🗑️ Licença {id_maquina} excluída com sucesso.")

    return redirect(url_for("admin.admin_index"))
