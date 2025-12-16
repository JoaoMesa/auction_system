# app/__init__.py
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import threading
import time

def create_app(config_class='config.Config'):
    app = Flask(__name__, static_folder='static')
    CORS(app)
    
    # Configuração
    app.config.from_object(config_class)
    
    # Inicializa Redis
    from .redis_client import redis_client
    redis_client.init_app(app)
    
    # Registra rotas
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    # Rota de saúde
    @app.route('/api/health')
    def health_check():
        try:
            redis_connected = redis_client.get_connection().ping()
        except:
            redis_connected = False
            
        return jsonify({
            'status': 'healthy' if redis_connected else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'redis_connected': redis_connected
        })
    
    # Rota principal para servir o frontend
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    # Rota para servir arquivos estáticos
    @app.route('/static/<path:path>')
    def serve_static(path):
        return app.send_static_file(path)
    
    return app