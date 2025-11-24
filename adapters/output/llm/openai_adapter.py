import os
import time
import asyncio
from typing import Optional, AsyncGenerator

from openai import AsyncOpenAI

from app.ports.output.llm_port import LLMPort, LLMRequest, LLMResponse


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
        
        print("✓ OpenAI Adapter inicializado (Puro - Sin CircuitBreaker)")
    
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """
        Genera respuesta en streaming con OpenAI GPT-4o-mini.
        
        Args:
            request: Solicitud con contexto
            
        Yields:
            Chunks de texto
        """
        # Construir prompt (Dinámico o Default)
        if request.system_prompt:
            system_prompt = request.system_prompt
        else:
            system_prompt = """Eres un Concierge Virtual de hotel.
Sé amable, conciso y profesional.
Responde en español.
Máximo 2-3 oraciones."""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Agregar contexto del hotel si existe
        if request.hotel_context:
            messages.append({
                "role": "system", 
                "content": f"CONTEXTO DEL HOTEL:\n{request.hotel_context}"
            })
        
        # Agregar historial si existe
        if request.conversation_history:
            messages.append({
                "role": "system",
                "content": f"HISTORIAL:\n{request.conversation_history}"
            })
        
        # Mensaje del usuario
        messages.append({
            "role": "user",
            "content": request.user_message
        })
        
        try:
            stream = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=0.7,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            print(f"🔥 Error Crítico OpenAI: {e}")
            raise e
    
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
