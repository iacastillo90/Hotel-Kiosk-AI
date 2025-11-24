import os
import time
import asyncio
from typing import Optional, AsyncGenerator

import google.generativeai as genai

from app.ports.output.llm_port import LLMPort, LLMRequest


class GeminiAdapter(LLMPort):
    """
    Adaptador para Google Gemini 2.5 Flash con Streaming.
    
    Implementa el contrato LLMPort usando la API de Google Generative AI.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Constructor.
        
        Args:
            api_key: Google API Key (opcional, usa env var si no se provee)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY no configurada. Configura en .env o pasa como argumento.")
        
        # Configurar SDK de Google
        genai.configure(api_key=self.api_key)
        
        # Modelo: gemini-2.5-flash (rápido y disponible)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        print("✓ Gemini Adapter inicializado (Puro - Sin CircuitBreaker)")
        print("✓ Gemini Adapter inicializado (Streaming habilitado)")
    
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """
        Genera una respuesta en streaming usando Gemini (Soporta Function Calling).
        
        Yields:
            Chunks de texto O JSON de llamada a función (prefijado con __FUNCTION_CALL__:)
        """
        # Construir prompt (Dinámico o Default)
        if request.system_prompt:
             system_prompt = request.system_prompt
        else:
             # Fallback por si acaso (aunque PromptFactory debería proveerlo)
             system_prompt = "Eres un asistente útil."
        
        full_prompt = f"""{system_prompt}

CONTEXTO DEL HOTEL:
{request.hotel_context or "No hay contexto específico disponible."}

HISTORIAL DE CONVERSACIÓN:
{request.conversation_history}

USUARIO: {request.user_message}

ASISTENTE:"""
        
        try:
            # Configuración de seguridad
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
            
            # Configurar herramientas si existen
            tools_config = request.tools if request.tools else None
            
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=request.max_tokens,
                temperature=0.7,
                top_p=0.9,
                top_k=40,
            )
            
            # Llamada de streaming
            loop = asyncio.get_event_loop()
            
            
            def _call_gemini_stream():
                """Wrapper que previene StopIteration de escapar"""
                try:
                    return self.model.generate_content(
                        full_prompt,
                        generation_config=generation_config,
                        safety_settings=safety_settings,
                        stream=True,
                        tools=tools_config
                    )
                except StopIteration:
                    # Esto NO debería pasar, pero si pasa, retornar generador vacío
                    return iter([])

            response_stream = await loop.run_in_executor(None, _call_gemini_stream)
            
            iterator = iter(response_stream)
            
            def safe_next():
                """Wrapper para evitar que StopIteration escape a asyncio"""
                try:
                    return next(iterator)
                except StopIteration:
                    return None
            
            try:
                while True:
                    try:
                        # Obtener siguiente chunk en thread
                        chunk = await loop.run_in_executor(None, safe_next)
                        if chunk is None:
                            break
                        
                        # Verificar si es una llamada a función
                        if not chunk.candidates:
                            continue
                            
                        candidate = chunk.candidates[0]
                        # Verificar si fue bloqueado por seguridad
                        if candidate.finish_reason != 0 and candidate.finish_reason != 1: # 0=Unspecified, 1=Stop
                             print(f"⚠️ Chunk bloqueado/finalizado: {candidate.finish_reason}")
                             continue

                        if not candidate.content or not candidate.content.parts:
                            continue

                        part = candidate.content.parts[0]
                        
                        if part.function_call:
                            fc = part.function_call
                            import json
                            fc_data = {
                                "name": fc.name,
                                "args": dict(fc.args)
                            }
                            yield f"__FUNCTION_CALL__:{json.dumps(fc_data)}"
                        else:
                            if part.text:
                                yield part.text
                                
                    except Exception as e:
                        print(f"⚠️ Error en chunk de Gemini: {e}")
                        raise e # Re-raise para que el Bus lo capture
                        
            except asyncio.CancelledError:
                # Manejar cancelación limpiamente sin StopIteration
                print("⚠️ Gemini stream cancelado")
                raise
            except StopIteration:
                # Esto NO debería pasar, pero si pasa, terminar limpiamente
                print("⚠️ StopIteration capturado en Gemini generate_stream")
                pass
            
        except Exception as e:
            print(f"🔥 Error Crítico Gemini: {e}")
            raise e # Re-raise para activar Fallover en el Bus

    async def health_check(self) -> bool:
        """Verifica disponibilidad de Gemini."""
        try:
            # Prueba simple síncrona en executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content("ok")
            )
            return response.text is not None
        except:
            return False
