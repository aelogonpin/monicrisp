# IMPORTANTE: eventlet debe importarse y aplicar monkey_patch ANTES de cualquier otra importación
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import os
import argparse
import logging

# Configurar el parser de argumentos de línea de comandos
parser = argparse.ArgumentParser(description='Servidor de monitoreo de URLs')
parser.add_argument('--log-level', '-l', 
                    choices=['debug', 'info', 'warning', 'error', 'critical'],
                    default='info',
                    help='Nivel de logging (default: info)')
args = parser.parse_args()

# Configurar logging según el parámetro recibido
log_level = getattr(logging, args.log_level.upper())
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

# Imprimir información sobre el nivel de logging
print(f"Nivel de logging establecido a: {args.log_level.upper()}")

# En las importaciones, añade:
from utils.logging_config import logging_manager
from api.log_config import log_api

# Establecer el nivel de logging seleccionado
logging_manager.set_level(args.log_level)

# Crear directorio para la base de datos si no existe
os.makedirs(os.path.dirname(os.path.abspath(__file__)) + '/../data', exist_ok=True)

# Inicializar aplicación Flask
app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'your-secret-key'

CORS(app)  # Habilita CORS para todas las rutas

# Inicializar SocketIO con parámetros mejorados - ajustar loggers según nivel seleccionado
socketio = SocketIO(
    app, 
    async_mode='eventlet',
    cors_allowed_origins="*",
    ping_timeout=20,
    ping_interval=10,
    logger=log_level <= logging.DEBUG,      # Solo activar si estamos en DEBUG
    engineio_logger=log_level <= logging.DEBUG,  # Solo activar si estamos en DEBUG
    max_http_buffer_size=10e6
)

# Añade estos decoradores para registro y manejo de errores
@app.before_request
def log_request_info():
    app.logger.debug('Request: %s %s', request.method, request.path)

@app.after_request
def log_response_info(response):
    app.logger.debug('Response: %s', response.status)
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error('Unhandled exception: %s', str(e), exc_info=e)
    return jsonify({"error": "Internal Server Error"}), 500

# Importaciones después de configurar Flask y SocketIO
from storage.database import init_db
from monitor.checker import UptimeChecker
from api.routes import api, init_routes

# Inicializar base de datos
with app.app_context():
    init_db()

# Inicializar checker
uptime_checker = UptimeChecker(socketio)

# Configurar rutas API
init_routes(uptime_checker)
app.register_blueprint(api)

# Y luego registra el blueprint:
app.register_blueprint(log_api)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Iniciar monitoreo en segundo plano
    uptime_checker.start_monitoring()
    
    print(f"Servidor iniciado en http://localhost:5000 (Nivel de log: {args.log_level})")
    # Iniciar servidor web
    socketio.run(
        app, 
        debug=log_level <= logging.DEBUG,  # Solo activar debug si estamos en nivel DEBUG
        host='0.0.0.0', 
        port=5000,
        log_output=True,
        use_reloader=False  # Desactiva el recargador para evitar problemas con hilos
    )