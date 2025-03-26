from flask import Blueprint, jsonify, request, current_app
from monitor.checker import UptimeChecker
from storage.database import save_result, get_results
from datetime import datetime

api = Blueprint('api', __name__, url_prefix='/api')
uptime_checker = None

def init_routes(checker):
    global uptime_checker
    uptime_checker = checker

@api.route('/urls', methods=['GET'])
def get_urls():
    if uptime_checker:
        urls_with_data = []
        for url, interval in uptime_checker.urls.items():
            # Obtener los últimos 10 resultados para cada URL
            results = get_results(url, limit=10)
            history = []
            
            # Calcular el porcentaje de disponibilidad
            total_checks = len(results)
            successful_checks = 0
            
            for result in results:
                if result.is_up:
                    history.append('up')
                    successful_checks += 1
                elif result.status_code == 0:
                    history.append('unknown')
                else:
                    history.append('down')
            
            # Calcular porcentaje (evitar división por cero)
            uptime_percentage = 0
            if total_checks > 0:
                uptime_percentage = round((successful_checks / total_checks) * 100)
            
            urls_with_data.append({
                'url': url,
                'interval': interval,
                'history': history,
                'uptime_percentage': uptime_percentage,
                'status': history[0] if history else 'unknown'
            })
        return jsonify({'urls': urls_with_data})
    return jsonify({'urls': []})

@api.route('/urls', methods=['POST'])
def add_url():
    data = request.json
    if not data or 'url' not in data:
        return jsonify({'success': False, 'message': 'URL no proporcionada'}), 400
    
    url = data['url']
    interval = data.get('interval', 30)  # Intervalo predeterminado si no se proporciona
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    if uptime_checker:
        try:
            # Si la URL ya existe, simplemente actualiza el intervalo
            existing = url in uptime_checker.urls
            uptime_checker.add_url(url, interval)
            
            # Si es una URL nueva, realizar un primer chequeo inmediato
            if not existing:
                result = uptime_checker.check_url(url)
            
            return jsonify({'success': True, 'message': 'URL añadida correctamente'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    
    return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500

@api.route('/urls', methods=['DELETE'])
def remove_url():
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'message': 'URL no proporcionada'}), 400
    
    try:
        if uptime_checker and uptime_checker.remove_url(url):
            return jsonify({'success': True, 'message': 'URL eliminada correctamente'})
        return jsonify({'success': False, 'message': 'URL no encontrada'}), 404
    except Exception as e:
        current_app.logger.error(f"Error al eliminar URL {url}: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@api.route('/results', methods=['GET'])
def get_monitoring_results():
    url = request.args.get('url')
    limit = int(request.args.get('limit', 100))
    
    results = get_results(url, limit)
    
    # Convertir resultados a formato JSON
    results_json = []
    for result in results:
        results_json.append({
            'url': result.url,
            'status_code': result.status_code,
            'response_time': result.response_time,
            'is_up': result.is_up,
            'checked_at': result.checked_at.isoformat() if result.checked_at else None
        })
    
    return jsonify({'results': results_json})

@api.route('/url-details', methods=['GET'])
def get_url_details():
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'message': 'URL no proporcionada'}), 400
    
    # Obtener el intervalo real desde uptime_checker
    interval = uptime_checker.urls.get(url, 30) if uptime_checker else 30
    
    # Obtener hasta 100 resultados para la URL
    results = get_results(url, limit=100)
    
    # Convertir resultados a formato JSON
    details = {
        'url': url,
        'interval': interval,  # Usar el valor real del intervalo
        'history': []
    }
    
    for result in results:
        details['history'].append({
            'status_code': result.status_code,
            'response_time': result.response_time,
            'is_up': result.is_up,
            'checked_at': result.checked_at.isoformat() if result.checked_at else None
        })
    
    # Calcular disponibilidad
    total = len(details['history'])
    up = sum(1 for item in details['history'] if item['is_up'])
    uptime_percentage = round((up / total) * 100) if total > 0 else 0
    details['uptime_percentage'] = uptime_percentage
    
    return jsonify(details)