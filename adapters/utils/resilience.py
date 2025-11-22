import asyncio
import time
from functools import wraps
from enum import Enum
from typing import Callable, TypeVar, Any

T = TypeVar('T')


class CircuitState(Enum):
    """Estados posibles del Circuit Breaker"""
    CLOSED = "closed"        # Funcionando normalmente
    OPEN = "open"            # En fallo, rechazar requests
    HALF_OPEN = "half_open"  # Intentando recuperarse


class CircuitBreaker:
    """
    Circuit Breaker para protección ante fallos de red.
    
    Implementa el patrón Circuit Breaker para prevenir cascadas de fallos:
    - CLOSED: Todo funciona, requests pasan normalmente
    - OPEN: Demasiados fallos, rechazar requests (fail fast)
    - HALF_OPEN: Después del timeout, intentar 1 request de prueba
    
    Ejemplo:
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_s=30)
        
        if breaker.is_open():
            raise RuntimeError("Circuit breaker abierto")
        
        try:
            result = await call_api()
            breaker.record_success()
        except Exception:
            breaker.record_failure()
    """
    
    def __init__(self,
                 failure_threshold: int = 3,
                 recovery_timeout_s: int = 30,
                 expected_exception: type = Exception):
        """
        Constructor.
        
        Args:
            failure_threshold: Número de fallos consecutivos para abrir circuit
            recovery_timeout_s: Segundos antes de intentar recuperación
            expected_exception: Tipo de excepción a capturar
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = CircuitState.CLOSED
    
    def is_open(self) -> bool:
        """
        Verifica si el circuit está abierto.
        
        Si está abierto y ha pasado el timeout de recuperación,
        automáticamente transiciona a HALF_OPEN.
        
        Returns:
            True si el circuit está abierto (rechazar requests)
        """
        if self.state == CircuitState.OPEN:
            # Intentar transición a HALF_OPEN después del timeout
            if self.last_failure_time is not None:
                elapsed = time.time() - self.last_failure_time
                if elapsed > self.recovery_timeout_s:
                    print(f"🔄 Circuit Breaker: OPEN → HALF_OPEN (timeout {self.recovery_timeout_s}s alcanzado)")
                    self.state = CircuitState.HALF_OPEN
                    self.failure_count = 0
                    return False
            return True
        
        return False
    
    def record_failure(self) -> None:
        """
        Registra un fallo.
        
        Si se alcanza el threshold, abre el circuit.
        """
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            print(f"⚠️ Circuit Breaker: {self.state.value} → OPEN ({self.failure_count} fallos)")
            self.state = CircuitState.OPEN
    
    def record_success(self) -> None:
        """
        Registra un éxito.
        
        Resetea el contador de fallos y cierra el circuit.
        """
        if self.state == CircuitState.HALF_OPEN:
            print(f"✓ Circuit Breaker: HALF_OPEN → CLOSED (recuperación exitosa)")
        
        self.failure_count = 0
        self.state = CircuitState.CLOSED


def retry_async(max_retries: int = 3,
                initial_delay_s: float = 0.5,
                max_delay_s: float = 5.0,
                backoff_factor: float = 2.0):
    """
    Decorador de retry con backoff exponencial para funciones async.
    
    Implementa reintentos automáticos con espera creciente entre intentos:
    - Intento 1: falla → espera 0.5s
    - Intento 2: falla → espera 1.0s (0.5 * 2)
    - Intento 3: falla → espera 2.0s (1.0 * 2)
    - Intento 4: falla → lanza excepción
    
    Args:
        max_retries: Número máximo de reintentos
        initial_delay_s: Delay inicial en segundos
        max_delay_s: Delay máximo en segundos (cap)
        backoff_factor: Factor de multiplicación para backoff exponencial
    
    Ejemplo:
        @retry_async(max_retries=3, initial_delay_s=0.3)
        async def call_api():
            response = await client.get("https://api.example.com")
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay_s
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Intentar ejecutar la función
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Aún tenemos intentos disponibles
                        print(f"⚠️ Intento {attempt + 1}/{max_retries + 1} falló: {e}")
                        print(f"   Esperando {delay:.1f}s antes de reintentar...")
                        
                        await asyncio.sleep(delay)
                        
                        # Backoff exponencial (con cap)
                        delay = min(delay * backoff_factor, max_delay_s)
                    else:
                        # Agotamos los reintentos
                        print(f"✗ Todos los intentos agotados: {e}")
            
            # Si llegamos aquí, todos los intentos fallaron
            raise last_exception
        
        return wrapper
    return decorator


class RateLimiter:
    """
    Rate Limiter simple para prevenir sobrecarga de APIs.
    
    Ejemplo:
        limiter = RateLimiter(max_calls=10, window_seconds=60)
        
        if not limiter.is_allowed():
            raise Exception("Rate limit excedido")
        
        await call_api()
    """
    
    def __init__(self, max_calls: int, window_seconds: float):
        """
        Constructor.
        
        Args:
            max_calls: Número máximo de llamadas permitidas
            window_seconds: Ventana de tiempo en segundos
        """
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls: list[float] = []
    
    def is_allowed(self) -> bool:
        """
        Verifica si una nueva llamada está permitida.
        
        Returns:
            True si está dentro del límite
        """
        now = time.time()
        
        # Limpiar llamadas antiguas fuera de la ventana
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < self.window_seconds]
        
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        
        return False
    
    def get_retry_after(self) -> float:
        """
        Calcula cuántos segundos esperar antes de la próxima llamada.
        
        Returns:
            Segundos a esperar
        """
        if not self.calls:
            return 0.0
        
        oldest_call = min(self.calls)
        time_since_oldest = time.time() - oldest_call
        
        return max(0.0, self.window_seconds - time_since_oldest)


# ==============================================================================
# Utilities para Timeout
# ==============================================================================

async def with_timeout(coro, timeout_seconds: float, error_message: str = "Timeout"):
    """
    Ejecuta una coroutine con timeout.
    
    Args:
        coro: Coroutine a ejecutar
        timeout_seconds: Timeout en segundos
        error_message: Mensaje de error si hay timeout
    
    Returns:
        Resultado de la coroutine
    
    Raises:
        asyncio.TimeoutError: Si se excede el timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise asyncio.TimeoutError(f"{error_message} (>{timeout_seconds}s)")
