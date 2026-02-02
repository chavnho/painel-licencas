from flask import Flask, request, render_template_string, redirect, url_for
import hashlib, datetime, os

app = Flask(__name__)
chave_secreta = "suaChaveSecreta"
caminho_licencas = "licencas.txt"

def codificar_data(data):
    grupoA = ''.join(data[i] for i in range(len(data)) if (i+1) % 2 == 1)
    grupoB = ''.join(data[i] for i in range(len(data)) if (i+1) % 2 == 0)
    return grupoA + grupoB

def gerar_hash(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()[:12]

def calcular_validade_por_valor(valor_pago):
    if valor_pago < 10:
        return None
    dias = 7 + (valor_pago - 10)
    validade = (datetime.datetime.now() + datetime.timedelta(days=dias)).strftime("%Y%m%d")
    return validade

def salvar_licenca(email, id_maquina, validade_codificada, hash_gerado):
    licencas = {}
    if os.path.exists(caminho_licencas):
        with open(caminho_licencas, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
            for linha in linhas[1:]:
                if '=' in linha:
                    partes = linha.strip().split('=')
                    licencas[partes[0]] = partes[1]
    licencas[email] = f"{id_maquina}|{validade_codificada}|{hash_gerado}"
    with open(caminho_licencas, 'w', encoding='utf-8') as f:
        f.write("[Licencas]\n")
        for email, dados in licencas.items():
            f.write(f"{email}={dados}\n")

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



html_layout = """
<!DOCTYPE html>
<html>
<head>
    <title>Gerador de Licenças</title>
    <style>
        body { background:#303030; color:#AAAAAA; font-family:Segoe UI, sans-serif; }
        h2 { color:#fff; }
        .container { display:flex; align-items:flex-start; gap:20px; }
        .left {
            flex:none;
            width:280px;
            padding:20px;
            background:#2b2b2b;
            border-radius:8px;
        }
        .right {
            flex: 1;
            padding: 0px 20px 20px 20px; /* top=5px, right=20px, bottom=20px, left=20px */
            background: #2b2b2b;
            border-radius: 8px;
            overflow-x: auto;
        }

        label { display:block; margin-top:10px; }
        input {
            width:250px;
            padding:5px;
            margin-top:5px;
            background:#444;
            border:1px solid #666;
            color:#fff;
        }
        button {
            background:#2980B9;
            color:white;
            padding:10px 20px;
            margin-top:15px;
            border:none;
            cursor:pointer;
            border-radius:5px;
        }
        button:hover { background:#2ECC71; }
        table { width:100%; border-collapse:collapse; margin-top:20px; }
        th, td { border:1px solid #555; padding:8px; text-align:left; }
        th { background:#444; color:#fff; }
        tbody tr:nth-child(even) { background-color:#3a3a3a; }
        tbody tr:hover { background-color:#505050; cursor:pointer; }
    </style>
</head>
<body>
    <h2>Gerador de Chave de Ativação</h2>
    <div class="container">
        <div class="left">
            <form method="POST" action="/gerar">
                <label>Email do Usuário:</label>
                <input type="text" id="email" name="email" onblur="buscarPorEmail()">
                <label>ID da Máquina:</label>
                <input type="text" id="id" name="id">
                <label>Valor Pago (R$):</label>
                <input type="number" id="valor" name="valor">
                <button type="submit">Gerar Chave</button>

                {% if mensagem %}
                    <div style="margin-top:10px; color:#ff8080;">
                        {{ mensagem }}
                    </div>
                {% endif %}

            </form>
        </div>
        <div class="right">
            <h3>Licenças</h3>
                <table id="tabelaLicencas">
                    <thead>
                        <tr>
                            <th>Email</th>
                            <th>ID</th>
                            <th>Validade</th>
                            <th>Chave</th>
                            <th>Dias Restantes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for lic in licencas %}
                        <tr>
                            <td>{{ lic.email }}</td>
                            <td>{{ lic.id }}</td>
                            <td>{{ lic.validade }}</td>
                            <td>{{ lic.hash }}</td>
                            <td>{{ lic.dias }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>

        </div>
    </div>

    <script>
    function preencherCampos(email, id, validade) {
        document.getElementById("email").value = email;
        document.getElementById("id").value = id;
        // validade não precisa ser editada, mas pode ser mostrada
    }

    // Clique na linha da tabela
    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll("#tabelaLicencas tbody tr").forEach(row => {
            row.addEventListener("click", () => {
                const cells = row.querySelectorAll("td");
                preencherCampos(cells[0].innerText, cells[1].innerText, cells[2].innerText);
            });
        });
    });

    // Buscar por email digitado
    function buscarPorEmail() {
        const emailDigitado = document.getElementById("email").value;
        document.querySelectorAll("#tabelaLicencas tbody tr").forEach(row => {
            const cells = row.querySelectorAll("td");
            if (cells[0].innerText === emailDigitado) {
                preencherCampos(cells[0].innerText, cells[1].innerText, cells[2].innerText);
            }
        });
    }
    </script>
</body>
</html>
"""

# @app.route("/")
# def index():
#     licencas = {}
#     if os.path.exists(caminho_licencas):
#         with open(caminho_licencas, 'r', encoding='utf-8') as f:
#             linhas = f.readlines()[1:]
#             for linha in linhas:
#                 if '=' in linha:
#                     partes = linha.strip().split('=')
#                     licencas[partes[0]] = partes[1]
#     return render_template_string(html_layout, licencas=licencas)

@app.route("/")
def index():
    licencas = []
    if os.path.exists(caminho_licencas):
        with open(caminho_licencas, 'r', encoding='utf-8') as f:
            linhas = f.readlines()[1:]
            for linha in linhas:
                if '=' in linha:
                    email, dados = linha.strip().split('=')
                    partes = dados.split('|')
                    id_maquina = partes[0]
                    data_codificada = partes[1]
                    hash_final = partes[2]

                    data_real = decodificar_data(data_codificada)
                    validade_formatada = formatar_data(data_real)
                    dias = dias_restantes(data_real)

                    licencas.append({
                        "email": email,
                        "id": id_maquina,
                        "validade": validade_formatada,
                        "hash": hash_final,
                        "dias": dias
                    })
    return render_template_string(html_layout, licencas=licencas)


@app.route("/gerar", methods=["POST"])
def gerar():
    email = request.form.get("email")
    id_maquina = request.form.get("id")
    valor_str = request.form.get("valor", "")
    valor_pago = int(valor_str) if valor_str.isdigit() else 0

    validade = calcular_validade_por_valor(valor_pago)
    if not validade:
        licencas = {}
        if os.path.exists(caminho_licencas):
            with open(caminho_licencas, 'r', encoding='utf-8') as f:
                linhas = f.readlines()[1:]
                for linha in linhas:
                    if '=' in linha:
                        partes = linha.strip().split('=')
                        licencas[partes[0]] = partes[1]
        return render_template_string(html_layout, licencas=licencas, mensagem="Valor insuficiente (mínimo R$10)")


    data_codificada = codificar_data(validade)
    base = id_maquina + data_codificada + chave_secreta
    hash_final = gerar_hash(base)

    salvar_licenca(email, id_maquina, data_codificada, hash_final)

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
