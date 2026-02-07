import os, mercadopago
from flask import Blueprint, request, redirect, jsonify
from banco_dados import app, Usuario, Licenca
from utils import processar_pagamento


# Tokens de acesso (use variáveis de ambiente para alternar entre teste/produção)
ACCESS_TOKEN_TESTE = "TEST-8496361248428422-020220-62ce45efe0178477500b6642aae6a3b8-50341309"
ACCESS_TOKEN_PRODUCAO = "APP_USR-8496361248428422-020220-7dad207785e3f9a6d8620182f4488e69-50341309"

ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", ACCESS_TOKEN_PRODUCAO)
sdk = mercadopago.SDK(ACCESS_TOKEN)

# 👉 Definição do Blueprint
pagamentos_bp = Blueprint("pagamentos", __name__, url_prefix="/pagamentos")


def gerar_pagamento_pix(email: str, id_maquina: str, valor: int ):

    payment_data = {
        "transaction_amount": valor,
        "description": f"Renovação de licença",
        "payment_method_id": "pix",
        "external_reference": f"{email}:{id_maquina}",
        "payer": {
            "email": email,
            "first_name": email.split("@")[0],
            "last_name": "Usuario",
            "identification": {
                "type": "CPF",
                "number": "19119119100"
            }
        },
        "metadata": {
            "email": email,
            "id_maquina": id_maquina
        }
    }

    result = sdk.payment().create(payment_data)
    pagamento = result["response"]

    return {
        "valor": valor,
        "pagamento": pagamento,
        "qr_code": pagamento.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code"),
        "qr_code_base64": pagamento.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code_base64"),
        "ticket_url": pagamento.get("transaction_details", {}).get("external_resource_url")
    }


@pagamentos_bp.route("/pagar", methods=["POST"])
def pagar():
    email = request.form.get("email")
    dias = request.form.get("dias")

    if not email or not dias:
        return "Dados inválidos: informe email e dias", 400

    try:
        dias = int(dias)
    except ValueError:
        return "O campo 'dias' deve ser um número inteiro", 400

    # busca id_maquina pelo email
    with app.app_context():
        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            return f"❌ Email {email} não encontrado. Digite um email válido.", 400

        licenca = Licenca.query.filter_by(usuario_id=usuario.id).first()
        if not licenca or not licenca.maquina_id:
            return f"❌ Nenhuma máquina vinculada ao email {email}.", 400

        id_maquina = licenca.maquina_id

    # Regra de cálculo do valor (mínimo R$10)
    valor = max(10, 10 + (dias - 7))

    # chama a função utilitária com email, id_maquina e valor
    dados = gerar_pagamento_pix(email, id_maquina, valor)

    # produção → redireciona para o link oficial
    if ACCESS_TOKEN == ACCESS_TOKEN_PRODUCAO and dados["ticket_url"]:
        return redirect(dados["ticket_url"])

    # sandbox → mostra QR Code e copia-e-cola
    return f"""
    <h2>Pagamento via Pix (Teste)</h2>
    <p>Valor: R${dados['valor']},00</p>
    <img src="data:image/png;base64,{dados['qr_code_base64']}" style="width:250px; height:250px;" />
    <p><strong>Código Pix (copia e cola):</strong></p>
    <textarea readonly style="width:100%; height:80px;">{dados['qr_code']}</textarea>
    <p>ID do pagamento: {dados['pagamento']['id']}</p>
    """


@pagamentos_bp.route("/consultar_pagamento/<payment_id>")
def consultar_pagamento(payment_id):
    result = sdk.payment().get(payment_id)
    pagamento = result["response"]

    status = pagamento.get("status")
    valor = pagamento.get("transaction_amount")
    email = pagamento.get("payer", {}).get("email")

    if status == "approved":
        mensagem = "Licença renovada com sucesso!"
    else:
        mensagem = f"Pagamento ainda não confirmado. Status: {status}"

    return f"""
    <h2>Status do Pagamento</h2>
    <p>ID: {payment_id}</p>
    <p>Email: {email}</p>
    <p>Valor: R${valor}</p>
    <p>Status atual: {status}</p>
    <p>{mensagem}</p>
    """

@pagamentos_bp.route("/confirmar", methods=["POST"])
def confirmar():
    data = request.get_json(force=True) or {} 
    print("Webhook recebido:", data) # log completo
    pagamento_id = data.get("data", {}).get("id")

    if not pagamento_id:
        return jsonify({"error": "Pagamento ID não encontrado"}), 400

    # consulta o pagamento no Mercado Pago
    pagamento = sdk.payment().get(pagamento_id)
    info = pagamento.get("response", {})

    # valor oficial processado
    valor_pago = info.get("transaction_amount")
    if valor_pago is None:
        # loga o payload para debug
        print("Pagamento sem transaction_amount:", info)
        return jsonify({"error": "Campo transaction_amount ausente"}), 400

    valor_pago = int(valor_pago)

    # pega email e id_maquina do metadata
    metadata = info.get("metadata", {})
    email = metadata.get("email")
    id_maquina = metadata.get("id_maquina")

    # fallback: external_reference
    if (not email or not id_maquina) and "external_reference" in info:
        try:
            email, id_maquina = info["external_reference"].split(":")
        except Exception:
            pass

    if not email or not id_maquina:
        return jsonify({"error": "Dados insuficientes no pagamento"}), 400

    # chama a função que faz a renovação
    ok, resultado = processar_pagamento(email, id_maquina, valor_pago)

    if ok:
        return jsonify({"status": "sucesso", "validade": resultado}), 200
    else:
        return jsonify({"status": "erro", "mensagem": resultado}), 400


# @pagamentos_bp.route("/confirmar", methods=["POST"])
# def confirmar():
#     data = request.json
#     pagamento_id = data.get("data", {}).get("id")

#     if not pagamento_id:
#         return jsonify({"error": "Pagamento ID não encontrado"}), 400

#     # consulta o pagamento no Mercado Pago
#     pagamento = sdk.payment().get(pagamento_id)
#     info = pagamento["response"]

#     # valor oficial processado
#     valor_pago = int(info["transaction_amount"])

#     # pega email e id_maquina do metadata
#     metadata = info.get("metadata", {})
#     email = metadata.get("email")
#     id_maquina = metadata.get("id_maquina")

#     # alternativa: se quiser usar external_reference
#     # email, id_maquina = info["external_reference"].split(":")

#     if not email or not id_maquina:
#         return jsonify({"error": "Dados insuficientes no pagamento"}), 400

#     # chama a função que faz a renovação
#     ok, resultado = processar_pagamento(email, id_maquina, valor_pago)

#     if ok:
#         return jsonify({"status": "sucesso", "validade": resultado}), 200
#     else:
#         return jsonify({"status": "erro", "mensagem": resultado}), 400


# @pagamentos_bp.route("/confirmar_teste", methods=["POST"])
# def confirmar_teste():
#     # O Mercado Pago envia data.id no webhook
#     data = request.json or request.args
#     pagamento_id = None

#     # Pode vir como querystring (?data.id=123&type=payment) ou no body
#     if "data" in data and isinstance(data["data"], dict):
#         pagamento_id = data["data"].get("id")
#     elif "id" in data:
#         pagamento_id = data.get("id")

#     if not pagamento_id:
#         return jsonify({"error": "Pagamento ID não encontrado"}), 400

#     # Consulta os detalhes completos do pagamento via SDK
#     pagamento = sdk.payment().get(pagamento_id)
#     info = pagamento["response"]

#     # Agora sim temos transaction_amount e metadata
#     valor_pago = int(info.get("transaction_amount", 0))
#     email = info.get("metadata", {}).get("email")
#     id_maquina = info.get("metadata", {}).get("id_maquina")

#     # Apenas log para teste
#     app.logger.info(f"[TESTE] Pagamento {pagamento_id} recebido: email={email}, maquina={id_maquina}, valor={valor_pago}")

#     return jsonify({
#         "pagamento_id": pagamento_id,
#         "email": email,
#         "id_maquina": id_maquina,
#         "valor_pago": valor_pago
#     }), 200


@pagamentos_bp.route("/confirmar_teste", methods=["POST"])
def confirmar_teste():
    data = request.json or request.args

    # tenta pegar o ID em diferentes formatos
    pagamento_id = None
    if isinstance(data, dict):
        # caso venha como querystring: ?data.id=123
        if "data.id" in data:
            pagamento_id = data.get("data.id")
        # caso venha como JSON: {"data": {"id": 123}}
        elif "data" in data and isinstance(data["data"], dict):
            pagamento_id = data["data"].get("id")
        elif "id" in data:
            pagamento_id = data.get("id")

    if not pagamento_id:
        return jsonify({"error": "Pagamento ID não encontrado"}), 400

    # consulta os detalhes completos do pagamento via SDK
    pagamento = sdk.payment().get(pagamento_id)
    info = pagamento["response"]

    valor_pago = int(info.get("transaction_amount", 0))
    email = info.get("metadata", {}).get("email")
    id_maquina = info.get("metadata", {}).get("id_maquina")

    app.logger.info(f"[TESTE] Pagamento {pagamento_id} recebido: email={email}, maquina={id_maquina}, valor={valor_pago}")

    return jsonify({
        "pagamento_id": pagamento_id,
        "email": email,
        "id_maquina": id_maquina,
        "valor_pago": valor_pago
    }), 200
