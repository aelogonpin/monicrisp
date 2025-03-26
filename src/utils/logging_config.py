import logging
import os
import json
from pathlib import Path

# Definir los niveles de logging disponibles
LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

# Ruta para el archivo de configuración
CONFIG_PATH = Path(__file__).parent.parent.parent / 'data' / 'logging_config.json'

class LoggingManager:
    def __init__(self):
        self.default_level = 'info'
        self.current_level = self.default_level
        self.root_logger = logging.getLogger()
        self.loggers = {}
        
        # Asegurarse de que exista el directorio de configuración
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        
        # Cargar configuración existente o crear una nueva
        self.load_config()
        
        # Configurar el logging inicialmente
        self.apply_config()
    
    def load_config(self):
        """Carga la configuración de logging desde el archivo."""
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    self.current_level = config.get('level', self.default_level)
                    self.loggers = config.get('loggers', {})
        except Exception as e:
            print(f"Error al cargar configuración de logging: {e}")
            # En caso de error, usar valores predeterminados
            self.current_level = self.default_level
            self.loggers = {}
        
        # Validar el nivel cargado
        if self.current_level not in LOG_LEVELS:
            print(f"Nivel de logging inválido: {self.current_level}, usando {self.default_level}")
            self.current_level = self.default_level
    
    def save_config(self):
        """Guarda la configuración de logging en el archivo."""
        try:
            config = {
                'level': self.current_level,
                'loggers': self.loggers
            }
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error al guardar configuración de logging: {e}")
    
    def apply_config(self):
        """Aplica la configuración de logging actual."""
        # Configurar el logger raíz
        self.root_logger.setLevel(LOG_LEVELS[self.current_level])
        
        # Configurar loggers específicos
        for logger_name, level in self.loggers.items():
            if level in LOG_LEVELS:
                logger = logging.getLogger(logger_name)
                logger.setLevel(LOG_LEVELS[level])
    
    def set_level(self, level, logger_name=None):
        """Cambia el nivel de logging global o para un logger específico."""
        if level not in LOG_LEVELS:
            return False
        
        if logger_name:
            # Configurar un logger específico
            self.loggers[logger_name] = level
            logger = logging.getLogger(logger_name)
            logger.setLevel(LOG_LEVELS[level])
        else:
            # Configurar el nivel global
            self.current_level = level
            self.root_logger.setLevel(LOG_LEVELS[level])
        
        self.save_config()
        return True
    
    def get_current_config(self):
        """Devuelve la configuración actual."""
        return {
            'global_level': self.current_level,
            'loggers': self.loggers
        }

# Instancia global para usar en toda la aplicación
logging_manager = LoggingManager()