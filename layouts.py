#  Menu de Contexto
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
            padding: 0px 20px 20px 20px;
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
            padding:6px 12px;
            margin-top:5px;
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
        .mensagem { margin-top:10px; font-weight:bold; }
        .erro { color:#ff8080; }
        .sucesso { color:#80ff80; }

        /* estilo do menu de contexto */
        #contextMenu {
            display: none;
            position: absolute;
            background: #2b2b2b;
            border: 1px solid #666;
            border-radius: 5px;
            z-index: 1000;
        }
        #contextMenu ul {
            list-style: none;
            margin: 0;
            padding: 5px;
        }
        #contextMenu li {
            padding: 5px 10px;
            cursor: pointer;
            color: #fff;
        }
        #contextMenu li:hover {
            background: #505050;
        }
    </style>
</head>
<body>
    <h2>Gerador de Chave de Ativação</h2>
    <div class="container">
        <div class="left">
            <form method="POST" action="/admin/gerar">
                <label>Email do Usuário:</label>
                <input type="text" id="email" name="email" onblur="buscarPorEmail()">
                <label>ID da Máquina:</label>
                <input type="text" id="id" name="id">
                <label>Valor Pago (R$):</label>
                <input type="number" id="valor" name="valor">
                <button type="submit">Gerar Chave</button>

                {% if mensagem %}
                    <div class="mensagem {% if 'insuficiente' in mensagem or 'erro' in mensagem %}erro{% else %}sucesso{% endif %}">
                        {{ mensagem|safe }}
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
                    <tr data-id="{{ lic.id }}">
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

    <!-- menu de contexto -->
    <div id="contextMenu">
        <ul>
            <li id="excluirOpcao">Excluir</li>
        </ul>
    </div>

    <script>
    let linhaSelecionada = null;
    const menu = document.getElementById("contextMenu");

    // clique com botão direito
    document.querySelectorAll("#tabelaLicencas tbody tr").forEach(row => {
        row.addEventListener("contextmenu", function(e) {
            e.preventDefault();
            linhaSelecionada = this.getAttribute("data-id");
            menu.style.top = e.pageY + "px";
            menu.style.left = e.pageX + "px";
            menu.style.display = "block";
        });
    });

    // fechar menu ao clicar fora
    document.addEventListener("click", function() {
        menu.style.display = "none";
    });

    // ação de excluir
    document.getElementById("excluirOpcao").addEventListener("click", function() {
        if (linhaSelecionada) {
            fetch("/admin/excluir", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: "id=" + encodeURIComponent(linhaSelecionada)
            }).then(() => location.reload());
        }
    });

    // preencher campos ao clicar na linha
    function preencherCampos(email, id, validade) {
        document.getElementById("email").value = email;
        document.getElementById("id").value = id;
    }
    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll("#tabelaLicencas tbody tr").forEach(row => {
            row.addEventListener("click", () => {
                const cells = row.querySelectorAll("td");
                preencherCampos(cells[0].innerText, cells[1].innerText, cells[2].innerText);
            });
        });
    });

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

html_layout_usuario = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Painel do Usuário - Renovar Licença</title>
    <style>
        body { background:#1e1e1e; color:#e0e0e0; font-family:Segoe UI, sans-serif; }
        h2 { color:#fff; text-align:center; margin-bottom:20px; }
        .container {
            max-width:420px;
            margin:50px auto;
            padding:25px;
            background:#2b2b2b;
            border-radius:12px;
            box-shadow:0 0 15px rgba(0,0,0,0.6);
        }
        label { display:block; margin-top:15px; font-weight:bold; color:#ccc; }
        input {
            padding:10px;
            background:#3a3a3a;
            border:1px solid #555;
            color:#fff;
            border-radius:6px;
            text-align:center;
            font-size:16px;
        }
        .linha {
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:10px;
            margin-top:10px;
        }
        .linha input {
            flex:1;
        }
        button.enviar {
            background:#27ae60;
            color:white;
            padding:12px 20px;
            margin-top:25px;
            border:none;
            cursor:pointer;
            border-radius:8px;
            width:100%;
            font-size:16px;
            font-weight:bold;
            transition:0.2s;
        }
        button.enviar:hover { background:#2ecc71; transform:scale(1.02); }
        .mensagem { margin-top:20px; font-weight:bold; text-align:center; padding:10px; border-radius:6px; }
        .sucesso { background:#2ecc71; color:#fff; }
        .erro { background:#e74c3c; color:#fff; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Renovar Licença</h2>
        <form method="POST" action="/pagamentos/pagar">
            <label>Email:</label>
            <input type="email" name="email" placeholder="Digite seu email" required style="width:100%;">

            <label>Valor e Dias:</label>
            <div class="linha">
                <input type="text" id="valor" name="valor" readonly value="R$10,00">
                <input type="number" id="dias" name="dias" value="7" min="7" step="1" onchange="calcularValor()">
            </div>

            <button type="submit" class="enviar">Solicitar Renovação</button>
        </form>
        {% if mensagem %}
            <div class="mensagem {% if 'erro' in mensagem %}erro{% else %}sucesso{% endif %}">
                {{ mensagem|safe }}
            </div>
            <form action="/" method="GET" style="text-align:center; margin-top:15px;">
                <button type="submit" style="
                    background:#3498db;
                    color:white;
                    padding:10px 18px;
                    border:none;
                    border-radius:6px;
                    cursor:pointer;
                    font-size:14px;
                    font-weight:bold;
                ">
                    Voltar
                </button>
            </form>
        {% endif %}

        {% if qr_code_base64 %}
            <div style="text-align:center; margin-top:20px;">
                <p>Escaneie o QR Code para pagar:</p>
                <img src="data:image/png;base64,{{ qr_code_base64 }}" alt="QR Code Pix">
                <p><strong>Código Pix (copia e cola):</strong></p>
                <textarea readonly style="width:100%; height:80px;">{{ qr_code }}</textarea>
            </div>
            {% endif %}
    </div>

    <script>
    function calcularValor() {
        let dias = parseInt(document.getElementById("dias").value);
        if (dias < 7) dias = 7; // mínimo 7 dias
        document.getElementById("dias").value = dias;

        // regra: R$10 por 7 dias + R$1 por cada dia extra
        let preco = 10 + (dias - 7);
        document.getElementById("valor").value = "R$" + preco.toFixed(2).replace(".", ",");
    }
    </script>
</body>
</html>
"""

# Botao Excluir remover _botao_excluir
html_layout_botao_excluir = """
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
            padding: 0px 20px 20px 20px;
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
            padding:6px 12px;
            margin-top:5px;
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
        .mensagem { margin-top:10px; font-weight:bold; }
        .erro { color:#ff8080; }
        .sucesso { color:#80ff80; }
    </style>
</head>
<body>
    <h2>Gerador de Chave de Ativação</h2>
    <div class="container">
        <div class="left">
            <form method="POST" action="/admin/gerar">
                <label>Email do Usuário:</label>
                <input type="text" id="email" name="email" onblur="buscarPorEmail()">
                <label>ID da Máquina:</label>
                <input type="text" id="id" name="id">
                <label>Valor Pago (R$):</label>
                <input type="number" id="valor" name="valor">
                <button type="submit">Gerar Chave</button>

                {% if mensagem %}
                    <div class="mensagem {% if 'insuficiente' in mensagem or 'erro' in mensagem %}erro{% else %}sucesso{% endif %}">
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
                        <th>Ações</th>
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
                        <td>
                            <form method="POST" action="/admin/excluir" style="display:inline;">
                                <input type="hidden" name="id" value="{{ lic.id }}">
                                <button type="submit">Excluir</button>
                            </form>
                        </td>
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
    }

    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll("#tabelaLicencas tbody tr").forEach(row => {
            row.addEventListener("click", () => {
                const cells = row.querySelectorAll("td");
                preencherCampos(cells[0].innerText, cells[1].innerText, cells[2].innerText);
            });
        });
    });

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
