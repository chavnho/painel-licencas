import hashlib, datetime
from banco_dados import app, db, Usuario, Licenca


chave_secreta = "suaChaveSecreta"

def carregar_licencas():
    licencas = []
    with app.app_context():
        registros = Licenca.query.all()
        for licenca in registros:
            # A licença no banco está armazenada como "data_codificada|hash_final"
            partes = licenca.licenca_codificada.split("|")
            data_codificada = partes[0]
            hash_final = partes[1]

            data_real = decodificar_data(data_codificada)
            validade_formatada = formatar_data(data_real)
            dias = dias_restantes(data_real)

            licencas.append({
                "email": licenca.usuario.email,
                "id": licenca.maquina_id,
                "validade": validade_formatada,
                "hash": hash_final,
                "dias": dias
            })
    return licencas


def decodificar_data(data_codificada):
    # desfaz o embaralhamento: metade inicial = ímpares, metade final = pares
    tamanho = len(data_codificada)
    metade = tamanho // 2
    grupoA = data_codificada[:metade]
    grupoB = data_codificada[metade:]
    resultado = []
    for i in range(metade):
        resultado.append(grupoA[i])
        if i < len(grupoB):
            resultado.append(grupoB[i])
    return ''.join(resultado)


def formatar_data(data_str):
    # transforma YYYYMMDD em DD/MM/YYYY
    return f"{data_str[6:8]}/{data_str[4:6]}/{data_str[0:4]}"


def dias_restantes(data_str):
    validade = datetime.datetime.strptime(data_str, "%Y%m%d")
    hoje = datetime.datetime.now()
    dias = (validade - hoje).days
    return dias if dias > 0 else 0


def codificar_data(data):
    grupoA = ''.join(data[i] for i in range(len(data)) if (i+1) % 2 == 1)
    grupoB = ''.join(data[i] for i in range(len(data)) if (i+1) % 2 == 0)
    return grupoA + grupoB


def gerar_hash(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()[:12]


def salvar_licenca(email, id_maquina, data_codificada, hash_final):
    if not email or not id_maquina or not data_codificada or not hash_final:
        print("❌ Dados inválidos: não é possível salvar licença com campos vazios.")
        return "erro"

    with app.app_context():
        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            usuario = Usuario(email=email, nome="Desconhecido")
            db.session.add(usuario)
            db.session.commit()

        licenca = Licenca.query.filter_by(usuario_id=usuario.id).first()

        if licenca:
            if licenca.maquina_id != id_maquina:
                print(f"⚠️ O email {email} já possui licença vinculada à máquina {licenca.maquina_id}.")
                return "duplicado"
            else:
                licenca.licenca_codificada = f"{data_codificada}|{hash_final}"
                licenca.status = "ativa"
                db.session.commit()
                print(f"🔄 Licença atualizada para {email}/{id_maquina}")
                return "ok"
        else:
            licenca = Licenca(
                maquina_id=id_maquina,
                usuario_id=usuario.id,
                licenca_codificada=f"{data_codificada}|{hash_final}",
                status="ativa"
            )
            db.session.add(licenca)
            db.session.commit()
            print(f"✅ Nova licença adicionada: {email}/{id_maquina}")
            return "ok"
        

def calcular_validade_por_valor(valor_pago):
    if valor_pago == 0:
        # gera licença com validade no dia atual (0 dias)
        validade = datetime.datetime.now().strftime("%Y%m%d")
        return validade
    if valor_pago < 10:
        return None
    dias = 7 + (valor_pago - 10)
    validade = (datetime.datetime.now() + datetime.timedelta(days=dias)).strftime("%Y%m%d")
    return validade


def processar_pagamento(email: str, id_maquina: str, valor_pago: int):
    validade = calcular_validade_por_valor(valor_pago)
    if not validade:
        return False, "Valor insuficiente (mínimo R$10)"

    data_codificada = codificar_data(validade)
    base = id_maquina + data_codificada + chave_secreta
    hash_final = gerar_hash(base)

    with app.app_context():
        # 1️⃣ Verifica se já existe licença para essa máquina
        licenca_por_maquina = Licenca.query.filter_by(maquina_id=id_maquina).first()
        if licenca_por_maquina:
            if licenca_por_maquina.usuario.email != email:
                return False, f"⚠️ Máquina {id_maquina} já vinculada ao email {licenca_por_maquina.usuario.email}"
            else:
                licenca_por_maquina.licenca_codificada = f"{data_codificada}|{hash_final}"
                licenca_por_maquina.status = "ativa"
                db.session.commit()
                app.logger.info(f"🔄 Licença atualizada para {email}/{id_maquina}")
                return True, validade

        # 2️⃣ Se não existe licença para essa máquina, verifica pelo email
        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            usuario = Usuario(email=email, nome="Desconhecido")
            db.session.add(usuario)
            db.session.commit()

        licenca_por_email = Licenca.query.filter_by(usuario_id=usuario.id).first()
        if licenca_por_email:
            licenca_por_email.maquina_id = id_maquina
            licenca_por_email.licenca_codificada = f"{data_codificada}|{hash_final}"
            licenca_por_email.status = "ativa"
            db.session.commit()
            app.logger.info(f"🔄 Máquina atualizada para {email} → {id_maquina}")
        else:
            nova_licenca = Licenca(
                maquina_id=id_maquina,
                usuario_id=usuario.id,
                licenca_codificada=f"{data_codificada}|{hash_final}",
                status="ativa"
            )
            db.session.add(nova_licenca)
            db.session.commit()
            app.logger.info(f"✅ Nova licença adicionada: {email}/{id_maquina}")

    return True, validade



# def processar_pagamento(email, id_maquina, valor_pago):
#     validade = calcular_validade_por_valor(valor_pago)
#     if not validade:
#         return False, "Valor insuficiente (mínimo R$10)"

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
#             licenca.maquina_id = id_maquina
#             licenca.licenca_codificada = f"{data_codificada}|{hash_final}"
#             licenca.status = "ativa"
#             print(f"🔄 Licença atualizada para {email}/{id_maquina}")
#         else:
#             nova_licenca = Licenca(
#                 maquina_id=id_maquina,
#                 usuario_id=usuario.id,
#                 licenca_codificada=f"{data_codificada}|{hash_final}",
#                 status="ativa"
#             )
#             db.session.add(nova_licenca)
#             print(f"✅ Nova licença adicionada: {email}/{id_maquina}")

#         db.session.commit()

#     return True, validade