from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
import os

Base = declarative_base()

class MonitoringResult(Base):
    __tablename__ = 'monitoring_results'
    
    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    status_code = Column(Integer)
    response_time = Column(Integer)  # en milisegundos
    is_up = Column(Boolean, default=False)
    checked_at = Column(DateTime, default=datetime.utcnow)

class MonitoredURL(Base):
    __tablename__ = 'monitored_urls'
    
    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False, unique=True)
    interval = Column(Integer, default=30)  # intervalo en segundos
    created_at = Column(DateTime, default=datetime.utcnow)

# Ruta de la base de datos relativa al proyecto
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data/monitoring.db')
db_uri = f'sqlite:///{db_path}'

# Crear la conexión a la base de datos con thread safety
engine = create_engine(db_uri, connect_args={'check_same_thread': False})
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def init_db():
    Base.metadata.create_all(engine)

def save_result(url, status_code, response_time, is_up):
    """Guarda el resultado de un chequeo en la base de datos"""
    session = Session()
    try:
        result = MonitoringResult(
            url=url,
            status_code=status_code,
            response_time=response_time,
            is_up=is_up,
            checked_at=datetime.utcnow()
        )
        session.add(result)
        session.commit()
        return result
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_results(url=None, limit=100):
    """Obtiene los resultados de monitoreo de la base de datos"""
    session = Session()
    try:
        query = session.query(MonitoringResult)
        
        if url:
            query = query.filter(MonitoringResult.url == url)
        
        results = query.order_by(MonitoringResult.checked_at.desc()).limit(limit).all()
        return results
    finally:
        session.close()

def save_url(url, interval):
    """Guarda o actualiza una URL monitoreada en la base de datos"""
    session = Session()
    try:
        existing = session.query(MonitoredURL).filter_by(url=url).first()
        if existing:
            existing.interval = interval
        else:
            url_obj = MonitoredURL(url=url, interval=interval)
            session.add(url_obj)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error al guardar URL: {e}")
        return False
    finally:
        session.close()

def delete_url(url):
    """Elimina una URL monitoreada de la base de datos"""
    session = Session()
    try:
        url_obj = session.query(MonitoredURL).filter_by(url=url).first()
        if url_obj:
            session.delete(url_obj)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"Error al eliminar URL: {e}")
        return False
    finally:
        session.close()

def get_all_urls():
    """Obtiene todas las URLs monitoreadas desde la base de datos"""
    session = Session()
    try:
        urls = session.query(MonitoredURL).all()
        return {url.url: url.interval for url in urls}
    finally:
        session.close()