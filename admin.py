from flask import Blueprint, request, render_template_string, redirect, url_for, send_file, jsonify
from banco_dados import app, db, Usuario, Licenca
from html import html_layout
from utils import carregar_licencas, processar_pagamento, calcular_validade_por_valor, codificar_data, gerar_hash, chave_secreta


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
def download_licencas():
    with app.app_context():
        registros = Licenca.query.all()
        linhas = []
        for licenca in registros:
            partes = licenca.licenca_codificada.split("|")
            data_codificada = partes[0]
            hash_final = partes[1]
            linhas.append(f"{licenca.usuario.email}={licenca.maquina_id}|{data_codificada}|{hash_final}")

        caminho_saida = "licencas.txt"
        with open(caminho_saida, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas))

    return send_file(
        caminho_saida,
        as_attachment=True,
        download_name="licencas.txt",
        mimetype="text/plain"
    )


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








# Gerar Original sozinho ja faz tudo
# @admin_bp.route("/gerar", methods=["POST"])
# def gerar():
#     email = request.form.get("email")
#     id_maquina = request.form.get("id")
#     valor_str = request.form.get("valor", "")
#     valor_pago = int(valor_str) if valor_str.isdigit() else 0

#     validade = calcular_validade_por_valor(valor_pago)
#     if not validade:
#         licencas = carregar_licencas()
#         return render_template_string(
#             html_layout,
#             licencas=licencas,
#             mensagem="Valor insuficiente (mínimo R$10)"
#         )

#     data_codificada = codificar_data(validade)
#     base = id_maquina + data_codificada + chave_secreta
#     hash_final = gerar_hash(base)

#     with app.app_context():
#         usuario = Usuario.query.filter_by(email=email).first()
#         if not usuario:
#             usuario = Usuario(email=email, nome="Desconhecido")
#             db.session.add(usuario)
#             db.session.commit()

#         licenca = Licenca.query.filter_by(usuario_id=usuario.id).first()
#         if licenca:
#             # 👉 Atualiza direto
#             licenca.maquina_id = id_maquina
#             licenca.licenca_codificada = f"{data_codificada}|{hash_final}"
#             licenca.status = "ativa"
#             print(f"🔄 Licença atualizada para {email}/{id_maquina}")
#         else:
#             # 👉 Cria nova
#             nova_licenca = Licenca(
#                 maquina_id=id_maquina,
#                 usuario_id=usuario.id,
#                 licenca_codificada=f"{data_codificada}|{hash_final}",
#                 status="ativa"
#             )
#             db.session.add(nova_licenca)
#             print(f"✅ Nova licença adicionada: {email}/{id_maquina}")

#         db.session.commit()

#     return redirect(url_for("admin.admin_index"))