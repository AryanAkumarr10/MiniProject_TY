from flask import Flask
from flask_cors import CORS
from config import Config
from models import db
from routes.auth import auth_bp
from routes.vessels import vessels_bp
from routes.cargo import cargo_bp
from routes.billing import billing_bp
from routes.customs import customs_bp
from routes.reports import reports_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5500", "http://localhost:5500"])
    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(vessels_bp)
    app.register_blueprint(cargo_bp) 
    app.register_blueprint(billing_bp)
    app.register_blueprint(customs_bp)
    app.register_blueprint(reports_bp)

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
