import asyncio
import logging
from typing import Any, Type, Callable, Dict, Awaitable, List

from app.ports.output.llm_port import LLMPort, LLMRequest
from app.ports.output.tts_port import TTSPort
from app.ports.output.knowledge_base_port import KnowledgeBasePort, KnowledgeBaseQuery
from app.ports.output.repository_port import RepositoryPort
from app.domain.commands import (
    GenerateLLMStreamCommand,
    SearchKnowledgeQuery,
    SynthesizeTTSCommand,
    SaveBookingCommand,
    LogInteractionCommand
)
from app.domain.services.prompt_factory import PromptFactory

class CommandBus:
    """
    Bus de Comandos (Micro-Kernel) con SELF-HEALING (Wauoo Nivel Dios).
    Implementa Chain-of-Responsibility para resiliencia automática.
    """
    
    def __init__(self,
                 llm_chain: List[LLMPort],
                 tts_chain: List[TTSPort],
                 kb_port: KnowledgeBasePort,
                 repository_port: RepositoryPort,
                 prompt_factory: PromptFactory): # Inyección PromptFactory
        
        self.llm_chain = llm_chain
        self.tts_chain = tts_chain
        self.kb_port = kb_port
        self.repository_port = repository_port
        self.prompt_factory = prompt_factory
        
        # Registro de Handlers
        self._handlers: Dict[Type, Callable[[Any], Awaitable[Any]]] = {
            GenerateLLMStreamCommand: self._handle_llm_stream,
            SearchKnowledgeQuery: self._handle_kb_search,
            SynthesizeTTSCommand: self._handle_tts_synthesize,
            SaveBookingCommand: self._handle_save_booking,
            LogInteractionCommand: self._handle_log_interaction
        }

    async def execute_command(self, command: Any) -> Any:
        """Ejecuta un comando."""
        handler = self._handlers.get(type(command))
        if not handler:
            raise ValueError(f"No handler registered for command: {type(command)}")
        
        try:
            return await handler(command)
        except Exception as e:
            print(f"🔥 Error ejecutando comando {type(command).__name__}: {e}")
            raise e

    async def execute_query(self, query: Any) -> Any:
        """Ejecuta una query (alias de execute_command por ahora)."""
        return await self.execute_command(query)

    async def _execute_with_fallback(self, chain: List[Any], operation: Callable[[Any], Awaitable[Any]]) -> Any:
        """
        Ejecuta una operación (no-streaming) sobre una cadena de adaptadores con lógica de Failover.
        """
        errors = []
        for i, adapter in enumerate(chain):
            try:
                return await operation(adapter)
            except Exception as e:
                print(f"⚠️ Fallo en adaptador {type(adapter).__name__}: {e}")
                errors.append(e)
                if i < len(chain) - 1:
                    print(f"🔄 Degradando al siguiente nivel de resiliencia...")
        
        raise Exception(f"❌ Error Crítico: Todos los adaptadores fallaron. Errores: {errors}")

    async def _execute_stream_with_fallback(self, chain: List[Any], operation: Callable[[Any], Awaitable[Any]]):
        """
        Ejecuta una operación de STREAMING sobre una cadena de adaptadores con lógica de Failover.
        """
        errors = []
        for i, adapter in enumerate(chain):
            try:
                # Obtenemos el generador
                stream = await operation(adapter)
                
                # Iteramos y hacemos yield. Si falla aquí, capturamos y pasamos al siguiente adaptador.
                async for item in stream:
                    yield item
                
                # Si terminamos el stream sin errores, salimos (sin return explícito)
                break
                
            except Exception as e:
                print(f"⚠️ Fallo en stream de {type(adapter).__name__}: {e}")
                errors.append(e)
                if i < len(chain) - 1:
                    print(f"🔄 Degradando al siguiente nivel de resiliencia...")
                    continue
        else:
            # Solo se ejecuta si el loop NO hizo break (todos fallaron)
            raise Exception(f"❌ Error Crítico: Todos los adaptadores fallaron. Errores: {errors}")

    # --- Handlers ---

    async def _handle_llm_stream(self, cmd: GenerateLLMStreamCommand):
        # Usar PromptFactory para generar el request optimizado
        request = self.prompt_factory.generate_llm_request(
            command=cmd,
            conversation=cmd.conversation,
            context=cmd.context
        )
        
        async def op(adapter: LLMPort):
            return adapter.generate_stream(request)
            
        return self._execute_stream_with_fallback(self.llm_chain, op)

    async def _handle_kb_search(self, query: SearchKnowledgeQuery):
        # KB no tiene cadena por ahora (solo Chroma), pero podría tenerla (ej. Chroma -> In-Memory)
        kb_results = await self.kb_port.search(
            KnowledgeBaseQuery(
                query_text=query.query_text,
                top_k=query.top_k,
                min_score=query.min_score
            )
        )
        return "\n".join([r.content for r in kb_results])

    async def _handle_tts_synthesize(self, cmd: SynthesizeTTSCommand):
        async def op(adapter: TTSPort):
            return adapter.synthesize_stream(cmd.text_stream)
            
        return self._execute_stream_with_fallback(self.tts_chain, op)

    async def _handle_save_booking(self, cmd: SaveBookingCommand):
        if self.repository_port:
            await self.repository_port.save_booking(cmd.booking_data)

    async def _handle_log_interaction(self, cmd: LogInteractionCommand):
        if self.repository_port:
            await self.repository_port.log_interaction(
                cmd.user_text, cmd.intent, cmd.response_text
            )
