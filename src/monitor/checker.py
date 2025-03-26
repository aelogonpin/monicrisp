import requests
import threading
import time
from datetime import datetime, timedelta
import logging
from storage.database import save_result, save_url, delete_url, get_all_urls, save_result_to_sqlite
from storage.database import Session, MonitoringResult

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UptimeChecker:
    def __init__(self, socketio=None):
        self.urls = {}  # Cambiar a un diccionario: {url: intervalo}
        self.default_interval = 30
        self.running = False
        self.threads = {}  # Guardar threads por URL
        self.last_check_times = {}  # Rastrear la última vez que se verificó cada URL
        self.socketio = socketio
        self._lock = threading.Lock()  # Para operaciones thread-safe
        
        # Cargar URLs existentes desde la base de datos
        self.load_urls_from_db()
    
    def load_urls_from_db(self):
        """Carga las URLs monitoreadas desde la base de datos"""
        try:
            self.urls = get_all_urls()
            logger.info(f"Cargadas {len(self.urls)} URLs desde la base de datos")
        except Exception as e:
            logger.error(f"Error al cargar URLs desde la base de datos: {e}")
            self.urls = {}

    def add_url(self, url, interval=None):
        """Añade una URL con un intervalo de monitoreo personalizado"""
        if interval is None:
            interval = self.default_interval
        
        interval = max(5, int(interval))  # Mínimo 5 segundos
        
        with self._lock:
            # Verificar si la URL ya existe
            url_exists = url in self.urls
            current_interval = self.urls.get(url)
            
            # Si la URL existe y el intervalo ha cambiado, detener el monitoreo actual
            if url_exists and current_interval != interval:
                logger.info(f"Cambiando intervalo para {url}: {current_interval}s -> {interval}s")
                self._stop_monitoring_url(url)
                url_exists = False  # Forzar reinicio del monitoreo
            
            # Actualizar intervalo
            self.urls[url] = interval
            
            # Guardar en la base de datos
            save_url(url, interval)
            
            # Si estamos monitorizando y es una URL nueva o ha cambiado el intervalo, iniciar nuevo hilo
            if self.running and not url_exists:
                # Iniciar el monitoreo en un hilo separado para no bloquear la respuesta API
                init_thread = threading.Thread(
                    target=self._initialize_monitoring_for_url,
                    args=(url,),
                    daemon=True
                )
                init_thread.start()
            
            return True

    def _initialize_monitoring_for_url(self, url):
        """Inicializa el monitoreo para una URL (función segura para ejecutar en un hilo)"""
        try:
            # Iniciar el monitoreo
            self._start_monitoring_url(url)
            
            # Dar tiempo al hilo para inicializarse
            time.sleep(0.5)
            
            # Forzar una primera verificación inmediata
            self.check_url(url)
        except Exception as e:
            logger.error(f"Error al inicializar monitoreo para {url}: {str(e)}")

    def remove_url(self, url):
        """Elimina una URL del monitoreo"""
        with self._lock:
            if url in self.urls:
                logger.info(f"Eliminando URL {url} del monitoreo")
                # Detener y eliminar el hilo si existe
                self._stop_monitoring_url(url)
                # Eliminar la URL del diccionario
                del self.urls[url]
                # Eliminar cualquier tiempo de última verificación
                if url in self.last_check_times:
                    del self.last_check_times[url]
                # Eliminar de la base de datos
                delete_url(url)
                return True
            return False
    
    def _stop_monitoring_url(self, url):
        """Detiene el monitoreo para una URL específica"""
        if url in self.threads:
            logger.debug(f"Deteniendo hilo de monitoreo para {url}")
            # El hilo se detendrá solo cuando vea que la URL ya no está en self.urls
            # o cuando detecte el flag thread_should_stop
            if hasattr(self.threads[url], 'thread_should_stop'):
                self.threads[url].thread_should_stop = True
            # Eliminar la referencia al hilo
            del self.threads[url]

    def check_url(self, url):
        """Verifica el estado de una URL"""
        # Verificar si ya hemos comprobado esta URL en los últimos N segundos
        current_time = time.time()
        min_interval_between_checks = 3  # segundos
        
        if url in self.last_check_times:
            time_since_last_check = current_time - self.last_check_times[url]
            if time_since_last_check < min_interval_between_checks:
                logger.warning(f"Ignorando verificación para {url}: demasiado pronto (último: hace {time_since_last_check:.1f}s)")
                return None
        
        # Actualizar el tiempo de la última verificación antes de comenzar
        self.last_check_times[url] = current_time
        
        start_time = time.time()
        try:
            logger.info(f"Verificando URL: {url} (intervalo configurado: {self.urls.get(url, 'desconocido')}s)")
            response = requests.get(url, timeout=10)
            response_time = int((time.time() - start_time) * 1000)
            status_code = response.status_code
            is_up = status_code == 200
            logger.info(f"Resultado para {url}: status_code={status_code}, is_up={is_up}, tiempo={response_time}ms")
        except requests.RequestException as e:
            logger.warning(f"Error al verificar {url}: {str(e)}")
            response_time = 0
            status_code = 0
            is_up = False

        # Guardar resultado en la base de datos
        try:
            check_id = int(time.time() * 1000)
            save_result(url, status_code, response_time, is_up)
            save_result_to_sqlite(url, status_code, response_time, is_up)
            
            # Emitir evento en tiempo real si socketio está configurado
            if self.socketio:
                logger.info(f"Emitiendo evento para {url}: status_code={status_code}, is_up={is_up}, check_id={check_id}")
                self.socketio.emit('status_update', {
                    'url': url,
                    'status_code': status_code,
                    'response_time': response_time,
                    'is_up': is_up,
                    'checked_at': datetime.utcnow().isoformat(),
                    'check_id': check_id
                }, namespace='/')  # Asegúrate de emitir en el namespace correcto
                
                # Añadir una verificación de que el evento se emitió correctamente
                logger.info(f"Evento emitido correctamente para {url}")
        except Exception as e:
            logger.error(f"Error al procesar resultado para {url}: {str(e)}")
        
        return {
            'url': url,
            'status_code': status_code,
            'response_time': response_time,
            'is_up': is_up
        }

    def _monitor_url_thread_func(self, url):
        """Función que se ejecuta en un hilo separado para monitorear una URL"""
        thread = threading.current_thread()
        thread.thread_should_stop = False
        thread.thread_id = f"monitor-{url}-{int(time.time())}"
        
        interval = self.urls.get(url, self.default_interval)
        logger.info(f"[{thread.thread_id}] Iniciando monitoreo para {url} con intervalo {interval} segundos")
        
        # Primera verificación inmediata solo si no se ha verificado recientemente
        if url not in self.last_check_times or time.time() - self.last_check_times.get(url, 0) > 5:
            self.check_url(url)
        
        while self.running and url in self.urls and not thread.thread_should_stop:
            try:
                # Obtener el intervalo actualizado
                interval = self.urls.get(url, self.default_interval)
                
                # Esperar exactamente el intervalo configurado
                logger.debug(f"[{thread.thread_id}] Esperando {interval}s antes de la próxima verificación de {url}")
                
                # Dividir el tiempo de espera en pequeños bloques
                sleep_start = time.time()
                while time.time() - sleep_start < interval:
                    if not self.running or url not in self.urls or thread.thread_should_stop:
                        break
                    time.sleep(min(0.5, interval - (time.time() - sleep_start)))
                
                # Verificar si debemos continuar
                if self.running and url in self.urls and not thread.thread_should_stop:
                    logger.debug(f"[{thread.thread_id}] Verificando {url} después de esperar {interval}s")
                    self.check_url(url)
                
            except Exception as e:
                logger.error(f"[{thread.thread_id}] Error en hilo de monitoreo para {url}: {str(e)}")
                time.sleep(5)  # Esperar antes de reintentar en caso de error
        
        logger.info(f"[{thread.thread_id}] Finalizando monitoreo para {url}")

    def _start_monitoring_url(self, url):
        """Inicia un hilo de monitoreo para una URL específica"""
        with self._lock:
            # Verificar si ya hay un hilo activo para esta URL
            if url in self.threads and self.threads[url].is_alive():
                logger.warning(f"Ya existe un hilo activo para {url}. Deteniendo primero.")
                self._stop_monitoring_url(url)
            
            # Asegurar que la URL todavía está en nuestra lista
            if url not in self.urls:
                logger.warning(f"La URL {url} ya no está en la lista de monitoreo. No se iniciará el hilo.")
                return
            
            logger.info(f"Creando nuevo hilo para {url} con intervalo {self.urls.get(url)}s")
            thread = threading.Thread(
                target=self._monitor_url_thread_func, 
                args=(url,),
                name=f"monitor-{url}-{int(time.time())}"
            )
            thread.daemon = True
            thread.thread_should_stop = False
            self.threads[url] = thread
            thread.start()

    def start_monitoring(self):
        """Inicia el monitoreo en hilos separados para cada URL"""
        if not self.running:
            self.running = True
            logger.info("Iniciando sistema de monitoreo")
            
            # Detener cualquier hilo existente por si acaso
            for url in list(self.threads.keys()):
                self._stop_monitoring_url(url)
            
            # Iniciar un hilo para cada URL
            for url in list(self.urls.keys()):
                self._start_monitoring_url(url)

    def stop_monitoring(self):
        """Detiene el monitoreo"""
        if self.running:
            logger.info("Deteniendo sistema de monitoreo")
            self.running = False
            
            # Esperar a que todos los hilos terminen
            for url, thread in list(self.threads.items()):
                logger.debug(f"Esperando a que termine el hilo para {url}")
                if hasattr(thread, 'thread_should_stop'):
                    thread.thread_should_stop = True
            
            self.threads = {}