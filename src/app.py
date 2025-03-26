# IMPORTANTE: eventlet debe importarse y aplicar monkey_patch ANTES de cualquier otra importación
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import os
import argparse
import logging
import json  # Añade esta importación para usar json.loads()
from storage.database import init_db, get_db_connection  # Añade get_db_connection aquí

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
from api.zones import zones_api
from datetime import datetime

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
app.register_blueprint(zones_api)

@app.route('/')
def index():
    return render_template('index.html')

# Añade esta función para inicializar la tabla de zonas
def init_zones_table():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        description TEXT,
        urls TEXT NOT NULL,  -- JSON array as string
        is_public INTEGER DEFAULT 1,
        created_at INTEGER
    )
    ''')
    conn.commit()
    conn.close()

# Añade esta ruta para las páginas de estado personalizadas
@app.route('/status/<string:slug>')
def status_zone(slug):
    """Renderiza una página de estado para una zona específica"""
    try:
        # Obtener datos de la zona
        conn = get_db_connection()
        cursor = conn.execute('SELECT id, name, slug, description, urls, is_public FROM zones WHERE slug = ?', (slug,))
        row = cursor.fetchone()
        
        if not row:
            return render_template('error.html', message='Zona no encontrada'), 404
        
        # Verificar si la zona es pública
        is_public = bool(row[5])
        if not is_public:
            # Aquí podrías implementar autenticación si lo deseas
            pass
        
        # Preparar datos para la plantilla
        zone = {
            'id': row[0],
            'name': row[1],
            'slug': row[2],
            'description': row[3],
            'urls': json.loads(row[4])  # Convertir la cadena JSON a lista
        }
        
        # Obtener datos de los servicios en esta zona
        services = []
        overall_status = 'operational'  # Por defecto todo operativo
        some_down = False
        
        for url in zone['urls']:
            # Obtener los últimos resultados para esta URL
            try:
                cursor = conn.execute('''
                    SELECT id, url, status_code, response_time, is_up, checked_at 
                    FROM results 
                    WHERE url = ? 
                    ORDER BY checked_at DESC 
                    LIMIT 10
                ''', (url,))
                
                results = cursor.fetchall()
                
                # Determinar el estado actual
                current_status = None
                last_checked = None
                
                if results:
                    # El primer resultado es el más reciente
                    current_status = bool(results[0][4])
                    try:
                        last_checked = datetime.fromisoformat(results[0][5])
                    except (ValueError, TypeError):
                        # Manejar formatos de fecha no válidos
                        last_checked = None
                
                # Construir historial para la visualización
                history = []
                for result in reversed(results):
                    if result[4]:  # is_up
                        history.append('up')
                    else:
                        history.append('down')
                        some_down = True
                        if result == results[0]:  # Si el más reciente está caído
                            overall_status = 'down'
                
                # Añadir este servicio a la lista
                services.append({
                    'url': url,
                    'is_up': current_status,
                    'last_checked': last_checked.strftime('%H:%M:%S') if last_checked else 'Desconocido',
                    'history': history
                })
            except Exception as e:
                app.logger.error(f"Error al procesar URL {url}: {str(e)}")
                services.append({
                    'url': url,
                    'is_up': None,
                    'last_checked': 'Error',
                    'history': []
                })
        
        # Ajustar estado general si hay algunos caídos pero no todos
        if some_down and overall_status != 'down':
            overall_status = 'partial'
        
        conn.close()
        
        # Determinar la clase CSS para el indicador de estado
        overall_status_class = 'operational'
        if overall_status == 'partial':
            overall_status_class = 'partial'
        elif overall_status == 'down':
            overall_status_class = 'down'
        
        return render_template(
            'status_zone.html',
            zone=zone,
            services=services,
            overall_status=overall_status,
            overall_status_class=overall_status_class,
            last_updated=datetime.now().strftime('%H:%M:%S')
        )
    except Exception as e:
        app.logger.error(f"Error al renderizar zona {slug}: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return render_template('error.html', message=f'Error interno: {str(e)}'), 500

if __name__ == '__main__':
    # Inicializar base de datos
    init_db()
    # Inicializar tabla de zonas
    init_zones_table()
    
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