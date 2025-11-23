import mysql.connector
import time
import logging
import asyncio
from typing import Dict, Any
from app.ports.output.repository_port import RepositoryPort

logger = logging.getLogger(__name__)

class MySQLAdapter(RepositoryPort):
    def __init__(self, host, user, password, database, port=3306):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'port': port
        }
        self.conn = None
        # La conexión inicial puede ser bloqueante (se hace al inicio una sola vez)
        self._connect_with_retry()

    def _connect_with_retry(self, max_retries=5, delay=5):
        """Espera a que el contenedor de MySQL esté listo"""
        for i in range(max_retries):
            try:
                self.conn = mysql.connector.connect(**self.config)
                # Crear tabla si no existe (Booking log)
                cursor = self.conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bookings (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255),
                        date VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Crear tabla de logs de interacciones
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS interaction_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_text TEXT,
                        intent VARCHAR(50),
                        response TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self.conn.commit()
                cursor.close()
                
                logger.info("✅ Conectado a MySQL exitosamente")
                return
            except mysql.connector.Error as err:
                logger.warning(f"⏳ MySQL no listo (Intento {i+1}/{max_retries}). Esperando... Error: {err}")
                time.sleep(delay)
        
        logger.error("❌ No se pudo conectar a MySQL después de varios intentos. La persistencia no funcionará.")

    async def save_booking(self, booking_data: Dict[str, Any]) -> bool:
        """Wrapper asíncrono para la operación bloqueante"""
        loop = asyncio.get_running_loop()
        # Ejecutamos la función síncrona en un hilo aparte
        return await loop.run_in_executor(None, self._save_booking_sync, booking_data)

    def _save_booking_sync(self, booking_data: Dict[str, Any]) -> bool:
        """Lógica síncrona interna"""
        if not self.conn or not self.conn.is_connected():
            # Intentar reconectar si se perdió
            try:
                self.conn.reconnect(attempts=1, delay=0)
            except:
                logger.error("No hay conexión a BD")
                return False
            
        try:
            cursor = self.conn.cursor()
            sql = "INSERT INTO bookings (name, date) VALUES (%s, %s)"
            val = (booking_data.get('name', 'Anon'), booking_data.get('date', 'Hoy'))
            cursor.execute(sql, val)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Error guardando reserva: {e}")
            return False

    async def log_interaction(self, user_text: str, intent: str, response: str) -> None:
        """Wrapper asíncrono"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._log_interaction_sync, user_text, intent, response)

    def _log_interaction_sync(self, user_text: str, intent: str, response: str) -> None:
        """Lógica síncrona interna"""
        if not self.conn or not self.conn.is_connected():
            try: 
                self.conn.reconnect(attempts=1, delay=0)
            except: return

        try:
            cursor = self.conn.cursor()
            sql = "INSERT INTO interaction_logs (user_text, intent, response) VALUES (%s, %s, %s)"
            val = (user_text, intent, response)
            cursor.execute(sql, val)
            self.conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Error guardando log: {e}")
