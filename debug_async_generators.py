"""
Wrapper para debugging de async generators.
Añade logging detallado para rastrear StopIteration.
"""
import functools
import logging
import traceback
from typing import AsyncGenerator, Any

logger = logging.getLogger("AsyncGenDebug")
logger.setLevel(logging.DEBUG)

def debug_async_generator(func):
    """
    Decorator para async generators que añade logging detallado.
    Captura y logea cualquier StopIteration que ocurra.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__qualname__}"
        logger.debug(f"🟢 START async generator: {func_name}")
        
        try:
            gen = func(*args, **kwargs)
            
            # Verificar que realmente es un async generator
            if not hasattr(gen, '__anext__'):
                logger.error(f"❌ {func_name} no es un async generator!")
                yield gen
                return
            
            count = 0
            async for item in gen:
                count += 1
                logger.debug(f"  ↪️ {func_name} yield #{count}: {type(item).__name__}")
                yield item
                
            logger.debug(f"🟢 END async generator: {func_name} (yielded {count} items)")
            
        except StopIteration as e:
            logger.error(f"❌ StopIteration in {func_name}!")
            logger.error(f"   Traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise
            
        except StopAsyncIteration:
            logger.debug(f"✓ StopAsyncIteration (normal) in {func_name}")
            
        except Exception as e:
            logger.error(f"❌ Exception in {func_name}: {type(e).__name__}: {e}")
            logger.error(f"   Traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise
    
    return wrapper
