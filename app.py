from banco_dados import app
from usuario import usuario_bp
from admin import admin_bp
from pagamentos import pagamentos_bp


# registra os blueprints
app.register_blueprint(usuario_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(pagamentos_bp)

if __name__ == "__main__":
    app.run(debug=True)
