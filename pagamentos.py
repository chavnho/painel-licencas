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


@pagamentos_bp.route("/consultar_pagamento/<int:payment_id>", methods=["GET"])
def consultar_pagamento(payment_id):
    try:
        result = sdk.payment().get(payment_id)
        pagamento = result.get("response", {})

        status = pagamento.get("status")
        valor = pagamento.get("transaction_amount")
        email = pagamento.get("metadata", {}).get("email")

        if status == "approved":
            mensagem = "Licença renovada com sucesso!"
        else:
            mensagem = f"Pagamento ainda não confirmado. Status: {status}"

        return f"""
        <h2>Status do Pagamento</h2>
        <p>ID: {payment_id}</p>
        <p>Email: {email}</p>
        <p>Valor: R${valor:.2f}</p>
        <p>Status atual: {status}</p>
        <p>{mensagem}</p>
        """
    except Exception as e:
        return f"<h2>Erro ao consultar pagamento</h2><p>{str(e)}</p>", 500


@pagamentos_bp.route("/confirmar", methods=["POST"])
def confirmar():
    data = request.get_json(force=True) or {}
    pagamento_id = data.get("data", {}).get("id")

    if not pagamento_id:
        return jsonify({"error": "Pagamento ID não encontrado"}), 400

    # consulta o pagamento no Mercado Pago
    pagamento = sdk.payment().get(pagamento_id)
    info = pagamento.get("response", {})

    # extrai os 3 parâmetros necessários
    valor_pago = info.get("transaction_amount")
    metadata = info.get("metadata", {})
    email = metadata.get("email")
    id_maquina = metadata.get("id_maquina")
    status = info.get("status")

    # valida dados
    if not all([valor_pago, email, id_maquina]):
        app.logger.error(f"Dados incompletos no pagamento {pagamento_id}: {info}")
        return jsonify({"error": "Dados incompletos"}), 400

    # lógica principal
    if status == "approved":
        sucesso, mensagem = processar_pagamento(email, id_maquina, valor_pago)
        if sucesso:
            app.logger.info(f"✅ Pagamento aprovado e processado: {mensagem}")
            return jsonify({"status": "ok", "validade": mensagem}), 200
        else:
            app.logger.warning(f"⚠️ Pagamento aprovado mas não processado: {mensagem}")
            return jsonify({"status": "erro", "mensagem": mensagem}), 400

    elif status == "pending":
        app.logger.info(f"⏳ Pagamento pendente: ID={pagamento_id}, Email={email}, Máquina={id_maquina}")
        return jsonify({"status": "pendente"}), 200

    elif status == "rejected":
        app.logger.info(f"❌ Pagamento rejeitado: ID={pagamento_id}, Email={email}, Máquina={id_maquina}")
        return jsonify({"status": "rejeitado"}), 200

    else:
        app.logger.info(f"ℹ️ Status desconhecido: {status}")
        return jsonify({"status": status}), 200


# def simular_webhook():
#     pagamento_id = 145204842448  # ID fixo para teste

#     pagamento = sdk.payment().get(pagamento_id)
#     info = pagamento.get("response", {})

#     valor_pago = 15 # info.get("transaction_amount")
#     # metadata = info.get("metadata", {})
#     email = "chavnho@gmail.com" # metadata.get("email")
#     id_maquina = "5BBF9E7D-4BA3-466E-9405-EA43568F1060"

#     return email, id_maquina, valor_pago


# @pagamentos_bp.route("/simular", methods=["GET"])
# def simular():
#     email, id_maquina, valor_pago = simular_webhook()
#     processar_pagamento(email, id_maquina, valor_pago)
#     return jsonify({
#         "status": "simulado",
#         "email": email,
#         "id_maquina": id_maquina,
#         "valor_pago": valor_pago
#     }), 200



# @pagamentos_bp.route("/criar_pagamento_teste", methods=["GET"])
# def criar_pagamento_teste():
#     pagamento_data = {
#         "transaction_amount": 1.00,
#         "description": "Teste Webhook Pix",
#         "payment_method_id": "pix",
#         "payer": {
#             "email": "teste@exemplo.com"
#         },
#         "metadata": {
#             "email": "teste@exemplo.com",
#             "id_maquina": "TESTE123"
#         }
#     }

#     pagamento = sdk.payment().create(pagamento_data)
#     info = pagamento.get("response", {})

#     # loga os detalhes do pagamento criado
#     app.logger.info(f"[CRIAR PAGAMENTO TESTE] {info}")

#     return jsonify(info), 200

