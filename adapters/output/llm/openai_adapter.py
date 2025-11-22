import os
import time
import asyncio
from typing import Optional

from openai import AsyncOpenAI

from app.ports.output.llm_port import LLMPort, LLMRequest, LLMResponse
from adapters.utils.resilience import CircuitBreaker, retry_async


class OpenAIAdapter(LLMPort):
    """
    Adaptador para OpenAI GPT-4o-mini.
    
    Alternativa/Fallback para cuando Gemini no está disponible.
    Implementa el mismo contrato LLMPort.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Constructor.
        
        Args:
            api_key: OpenAI API Key
            
        Raises:
            ValueError: Si no se encuentra API key
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY no configurada")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        # Circuit Breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout_s=30
        )
        
        print("✓ OpenAI Adapter inicializado")
    
    @retry_async(max_retries=2, initial_delay_s=0.3)
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Genera respuesta con OpenAI GPT-4o-mini.
        
        Args:
            request: Solicitud con contexto
            
        Returns:
            Respuesta del LLM
        """
        if self.circuit_breaker.is_open():
            raise RuntimeError("Circuit breaker abierto para OpenAI")
        
        start_time = time.time()
        
        system_prompt = """Eres un Concierge Virtual de hotel.
Sé amable, conciso y profesional.
Responde en español.
Máximo 2-3 oraciones."""
        
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"{request.hotel_context}\n\n{request.user_message}"}
                    ],
                    max_tokens=request.max_tokens,
                    temperature=0.7,
                ),
                timeout=3.0
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            self.circuit_breaker.record_success()
            
            return LLMResponse(
                text=response.choices[0].message.content,
                model="gpt-4o-mini",
                tokens_used=response.usage.total_tokens,
                latency_ms=latency_ms
            )
            
        except asyncio.TimeoutError:
            self.circuit_breaker.record_failure()
            raise
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise
    
    async def health_check(self) -> bool:
        """Verifica disponibilidad de OpenAI"""
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "ok"}],
                    max_tokens=1,
                ),
                timeout=2.0
            )
            return True
        except:
            return False
