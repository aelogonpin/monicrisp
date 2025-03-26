from flask import Blueprint, jsonify, request, current_app
from storage.database import get_db_connection
import sqlite3
import json
import time

zones_api = Blueprint('zones_api', __name__, url_prefix='/api/zones')

@zones_api.route('', methods=['GET'])
def get_zones():
    """Obtener todas las zonas configuradas"""
    try:
        conn = get_db_connection()
        cursor = conn.execute('SELECT id, name, slug, description, urls, is_public, created_at FROM zones ORDER BY name')
        zones = []
        
        for row in cursor:
            # Convertir la cadena JSON de URLs a lista
            urls = json.loads(row[4])
            
            zones.append({
                'id': row[0],
                'name': row[1],
                'slug': row[2],
                'description': row[3],
                'urls': urls,
                'is_public': bool(row[5]),
                'created_at': row[6]
            })
        
        conn.close()
        return jsonify({'success': True, 'zones': zones})
    
    except Exception as e:
        current_app.logger.error(f"Error al obtener zonas: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@zones_api.route('/<string:slug>', methods=['GET'])
def get_zone_by_slug(slug):
    """Obtener una zona específica por su slug"""
    try:
        conn = get_db_connection()
        cursor = conn.execute('SELECT id, name, slug, description, urls, is_public FROM zones WHERE slug = ?', (slug,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({'success': False, 'message': 'Zona no encontrada'}), 404
        
        # Convertir la cadena JSON de URLs a lista
        urls = json.loads(row[4])
        
        zone = {
            'id': row[0],
            'name': row[1],
            'slug': row[2],
            'description': row[3],
            'urls': urls,
            'is_public': bool(row[5])
        }
        
        conn.close()
        return jsonify({'success': True, 'zone': zone})
    
    except Exception as e:
        current_app.logger.error(f"Error al obtener zona {slug}: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@zones_api.route('', methods=['POST'])
def create_zone():
    """Crear una nueva zona"""
    data = request.json
    name = data.get('name')
    slug = data.get('slug')
    description = data.get('description', '')
    urls = data.get('urls', [])
    is_public = data.get('is_public', True)
    
    if not name or not slug:
        return jsonify({'success': False, 'message': 'Nombre y slug son obligatorios'}), 400
    
    # Validar que el slug solo contiene caracteres válidos
    if not slug.isalnum() and not all(c.isalnum() or c == '-' for c in slug):
        return jsonify({'success': False, 'message': 'El slug solo puede contener letras, números y guiones'}), 400
    
    try:
        conn = get_db_connection()
        
        # Verificar si ya existe una zona con el mismo slug
        cursor = conn.execute('SELECT id FROM zones WHERE slug = ?', (slug,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Ya existe una zona con esa ruta de acceso'}), 400
        
        # Convertir lista de URLs a formato JSON
        urls_json = json.dumps(urls)
        
        # Insertar nueva zona
        conn.execute(
            'INSERT INTO zones (name, slug, description, urls, is_public, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (name, slug, description, urls_json, 1 if is_public else 0, int(time.time()))
        )
        conn.commit()
        
        # Obtener el ID de la zona recién creada
        cursor = conn.execute('SELECT last_insert_rowid()')
        zone_id = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Zona creada correctamente',
            'id': zone_id,
            'slug': slug
        })
    
    except Exception as e:
        current_app.logger.error(f"Error al crear zona: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@zones_api.route('/<int:zone_id>', methods=['DELETE'])
def delete_zone(zone_id):
    """Eliminar una zona"""
    try:
        conn = get_db_connection()
        
        # Verificar si la zona existe
        cursor = conn.execute('SELECT id FROM zones WHERE id = ?', (zone_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Zona no encontrada'}), 404
        
        # Eliminar zona
        conn.execute('DELETE FROM zones WHERE id = ?', (zone_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Zona eliminada correctamente'
        })
    
    except Exception as e:
        current_app.logger.error(f"Error al eliminar zona {zone_id}: {str(e)}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500