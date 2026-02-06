from flask import Blueprint, render_template_string
from layouts import html_layout_usuario


usuario_bp = Blueprint("usuario", __name__)

@usuario_bp.route("/")
def usuario_index():
    return render_template_string(html_layout_usuario, mensagem="")
