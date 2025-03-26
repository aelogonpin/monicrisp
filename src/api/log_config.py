from flask import Blueprint, jsonify, request
from utils.logging_config import logging_manager, LOG_LEVELS

log_api = Blueprint('log_api', __name__, url_prefix='/api/logging')

@log_api.route('/levels', methods=['GET'])
def get_available_levels():
    """Devuelve los niveles de logging disponibles."""
    return jsonify({
        'success': True,
        'levels': list(LOG_LEVELS.keys())
    })

@log_api.route('/config', methods=['GET'])
def get_config():
    """Devuelve la configuración actual de logging."""
    return jsonify({
        'success': True,
        'config': logging_manager.get_current_config()
    })

@log_api.route('/set-level', methods=['POST'])
def set_level():
    """Cambia el nivel de logging."""
    data = request.json
    level = data.get('level')
    logger_name = data.get('logger')
    
    if not level:
        return jsonify({'success': False, 'message': 'Nivel no especificado'}), 400
    
    if level not in LOG_LEVELS:
        return jsonify({'success': False, 'message': f'Nivel inválido. Disponibles: {list(LOG_LEVELS.keys())}'}), 400
    
    result = logging_manager.set_level(level, logger_name)
    
    if result:
        return jsonify({
            'success': True,
            'message': f'Nivel de logging cambiado a {level} para {"logger " + logger_name if logger_name else "toda la aplicación"}',
            'config': logging_manager.get_current_config()
        })
    else:
        return jsonify({'success': False, 'message': 'Error al cambiar nivel de logging'}), 500