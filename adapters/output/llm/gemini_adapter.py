import os
import time
import asyncio
from typing import Optional

import google.generativeai as genai

from app.ports.output.llm_port import LLMPort, LLMRequest, LLMResponse
from adapters.utils.resilience import CircuitBreaker, retry_async


class GeminiAdapter(LLMPort):
    """
    Adaptador para Google Gemini 2.5 Flash.
    
    Implementa el contrato LLMPort usando la API de Google Generative AI.
    Incluye protección con Circuit Breaker y Retry Logic para red 4G inestable.
    
    Características:
    - Circuit Breaker: Protege contra cascadas de fallos
    - Retry con backoff exponencial: 3 intentos con delays crecientes
    - Timeout agresivo: 3 segundos (crítico para 4G)
    - Prompt engineering: Sistema optimizado para concierge
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Constructor.
        
        Args:
            api_key: Google API Key (opcional, usa env var si no se provee)
            
        Raises:
            ValueError: Si no se encuentra API key
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY no configurada. Configura en .env o pasa como argumento.")
        
        # Configurar SDK de Google
        genai.configure(api_key=self.api_key)
        
        # Modelo: gemini-2.5-flash (rápido y disponible)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Circuit Breaker: 3 fallos → abre, 30s timeout
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout_s=30
        )
        
        print("✓ Gemini Adapter inicializado")
    
    @retry_async(max_retries=2, initial_delay_s=0.3)
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Genera una respuesta usando Gemini.
        
        Implementación con:
        - Circuit Breaker para fail-fast
        - Retry automático (3 intentos)
        - Timeout de 3 segundos
        
        Args:
            request: Solicitud con contexto y mensaje del usuario
            
        Returns:
            Respuesta del LLM con texto y metadatos
            
        Raises:
            RuntimeError: Si circuit breaker está abierto
            asyncio.TimeoutError: Si excede 3 segundos
            Exception: Para otros errores de API
        """
        # Verificar circuit breaker
        if self.circuit_breaker.is_open():
            raise RuntimeError("Circuit breaker abierto para Gemini. Esperando recuperación...")
        
        start_time = time.time()
        
        # ======================================================================
        # Construir prompt con ingeniería de prompts
        # ======================================================================
        system_prompt = """Eres un Concierge Virtual de hotel.

Reglas:
- Sé amable, conciso y profesional
- Responde siempre en español
- Si se te pregunta algo fuera del contexto del hotel, amablemente redirige la conversación
- Máximo 2-3 oraciones por respuesta (conciso para audio)
- Si no tienes información, admítelo y sugiere contactar recepción"""
        
        # Contexto completo
        full_prompt = f"""{system_prompt}

CONTEXTO DEL HOTEL:
{request.hotel_context or "No hay contexto específico disponible."}

HISTORIAL DE CONVERSACIÓN:
{request.conversation_history}

USUARIO: {request.user_message}

ASISTENTE:"""
        
        try:
            # ==================================================================
            # Llamada a Gemini con TIMEOUT de 5 segundos
            # ==================================================================
            # Aumentado de 3s a 5s para mayor estabilidad
            response = await asyncio.wait_for(
                self._call_gemini(full_prompt, request.max_tokens),
                timeout=5.0
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Registrar éxito en circuit breaker
            self.circuit_breaker.record_success()
            
            return LLMResponse(
                text=response.strip(),
                model="gemini-2.5-flash",
                tokens_used=0,  # Gemini no expone tokens directamente en la respuesta
                latency_ms=latency_ms
            )
            
        except asyncio.TimeoutError:
            # Timeout: red lenta o API sobrecargada
            print(f"✗ Timeout en Gemini (>5s)")
            self.circuit_breaker.record_failure()
            raise
            
        except Exception as e:
            # Otro error (API key inválida, rate limit, etc)
            print(f"✗ Error Gemini: {e}")
            self.circuit_breaker.record_failure()
            raise
    
    async def _call_gemini(self, prompt: str, max_tokens: int) -> str:
        """
        Llamada real a Gemini en executor (para no bloquear event loop).
        
        La API de Gemini es síncrona, por lo que la ejecutamos en un
        thread separado usando run_in_executor.
        
        Args:
            prompt: Prompt completo construido
            max_tokens: Máximo de tokens a generar
            
        Returns:
            Texto generado por Gemini
        """
        loop = asyncio.get_event_loop()
        
        # Configuración de seguridad permisiva para evitar bloqueos falsos
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
        
        def _generate_safe():
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=max_tokens,
                        temperature=0.7,
                        top_p=0.9,
                        top_k=40,
                    ),
                    safety_settings=safety_settings
                )
                
                # Intentar acceder al texto
                try:
                    return response.text
                except ValueError:
                    # Si falla, inspeccionar por qué
                    if response.candidates:
                        finish_reason = response.candidates[0].finish_reason
                        print(f"⚠️ Gemini Finish Reason: {finish_reason}")
                        # Si es SAFETY (3), devolver mensaje amigable
                        if finish_reason == 3:
                            return "Lo siento, no puedo responder a eso por motivos de seguridad."
                        # Si es MAX_TOKENS (2) y no hay texto, devolver error
                        return f"Error generando respuesta (Reason: {finish_reason})"
                    return "Error: Respuesta vacía de Gemini"
                    
            except Exception as e:
                print(f"✗ Error interno Gemini: {e}")
                raise
        
        return await loop.run_in_executor(None, _generate_safe)
    
    async def health_check(self) -> bool:
        """
        Verifica disponibilidad de Gemini.
        
        Envía un prompt trivial para confirmar conectividad.
        
        Returns:
            True si el servicio está disponible
        """
        try:
            response = await asyncio.wait_for(
                self._call_gemini("Responde solo 'ok'", 10),
                timeout=2.0
            )
            return response.strip().lower() == "ok"
        except:
            return False
