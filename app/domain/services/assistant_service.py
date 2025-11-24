import time
import json
import asyncio
from typing import Optional, AsyncGenerator, List, Dict, Any

from app.ports.output.stt_port import STTPort
from app.ports.output.affect_port import AffectPort
from app.domain.entities.conversation import Conversation, Message, MessageRole
from app.domain.services.conversation_context import ConversationContext
from app.domain.services.command_bus import CommandBus
from app.domain.commands import (
    GenerateLLMStreamCommand,
    SearchKnowledgeQuery,
    SynthesizeTTSCommand,
    SaveBookingCommand,
    LogInteractionCommand
)

class AssistantService:
    """
    Orquestador principal del sistema CON WAUOO OMEGA (Command Bus).
    """
    
    def __init__(self,
                 stt_port: STTPort,
                 affect_port: AffectPort,
                 command_bus: CommandBus): # Inyección del Command Bus
        
        self.stt_port = stt_port
        self.affect_port = affect_port
        self.command_bus = command_bus
        
        # Estado y Contexto
        self.conversation: Optional[Conversation] = None
        self.context: Optional[ConversationContext] = None
        
        # Definición de Herramientas (Function Calling)
        self.tools = [
            {
                "function_declarations": [
                    {
                        "name": "make_booking",
                        "description": "Realizar una reserva de restaurante o servicio.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string", "description": "Fecha (DD/MM)"},
                                "time": {"type": "string", "description": "Hora (HH:MM)"},
                                "people": {"type": "integer", "description": "Número de personas"}
                            },
                            "required": ["date", "time"]
                        }
                    },
                    {
                        "name": "check_in_info",
                        "description": "Proveer información sobre check-in y horarios.",
                        "parameters": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "contact_support",
                        "description": "Proveer información de contacto o llamar a recepción.",
                        "parameters": {"type": "object", "properties": {}}
                    }
                ]
            }
        ]
    
    async def process_audio(self, audio_stream: AsyncGenerator[bytes, None]) -> tuple[str, AsyncGenerator[bytes, None]]:
        """
        Flujo Quantum Wauoo + Tiering Dinámico (Omega) + Command Bus.
        """
        start_time = time.time()
        
        # 1. Split Stream -> STT + Affect Analysis (Paralelo)
        stt_queue = asyncio.Queue()
        affect_queue = asyncio.Queue()
        
        # Lanzar distribuidor en background
        asyncio.create_task(self._stream_distributor(audio_stream, stt_queue, affect_queue))
        
        # 2. Iniciar Tareas Paralelas
        text_stream = self.stt_port.transcribe_stream(self._queue_gen(stt_queue))
        affect_task = asyncio.create_task(self.affect_port.analyze_stream(self._queue_gen(affect_queue)))
        
        # 3. Pipeline Proactivo (RAG via Command Bus)
        final_text, kb_context = await self._proactive_pipeline(text_stream)
        
        # Esperar resultado afectivo
        emotional_state = await affect_task
        system_latency = int((time.time() - start_time) * 1000)
        kb_confidence = 0.8 if kb_context else 0.0
        
        # Validaciones
        if not final_text.strip():
            fallback = "¿Hola? No te escuché."
            return fallback, self._quick_tts_stream(fallback)
            
        print(f"🎤 Usuario (Final): {final_text}")
        print(f"❤️ Estado: {emotional_state} | ⏱️ Latencia: {system_latency}ms")
        
        # Actualizar Historial
        if self.conversation:
            self.conversation.add_message(Message(final_text, MessageRole.USER))
        if self.context:
            self.context.last_activity = time.time()

        # 4. TIERING DINÁMICO (LLM Omega-1: Rápido, sin Tools)
        # Intentamos resolver con una llamada rápida (sin tools, sin historial pesado si se quisiera)
        quick_llm_command = GenerateLLMStreamCommand(
            user_message=final_text,
            hotel_context=kb_context, 
            emotional_state=emotional_state,
            kb_confidence=kb_confidence,
            system_latency_ms=system_latency,
            tools=None, # OMEGA-1 NO USA TOOLS
            conversation=self.conversation,
            context=self.context
        )
        
        # Ejecutar Comando LLM
        llm_quick_stream = await self.command_bus.execute_command(quick_llm_command)
        
        # Consumimos el stream para evaluar la respuesta
        quick_response_chunks = []
        async for chunk in llm_quick_stream:
            quick_response_chunks.append(chunk)
        quick_response_text = "".join(quick_response_chunks)
        
        # =================================================================
        # CORRECCIÓN CRÍTICA: Validar que la respuesta NO esté vacía
        # =================================================================
        word_count = len(quick_response_text.split())
        
        # Heurística Omega-1 (Solo si hay contenido real y es breve)
        if 0 < word_count <= 25:  # Aumentado a 25 palabras para ser más útil
            print(f"✅ Respuesta Omega-1 (Rápida): {quick_response_text}")
            return final_text, self._quick_tts_stream(quick_response_text)
            
        # 5. FALLBACK A OMEGA-2 (Cognitivo/Function Calling)
        # Si Omega-1 falló (vacío) o es muy largo, pasamos a Omega-2
        if word_count == 0:
            print("⚠️ Omega-1 devolvió vacío. Reintentando con Omega-2...")
        else:
            print("🧠 Respuesta larga o compleja. Escalando a Omega-2...")
        
        llm_command_full = GenerateLLMStreamCommand(
            user_message=final_text,
            hotel_context=kb_context,
            emotional_state=emotional_state,
            kb_confidence=kb_confidence,
            system_latency_ms=system_latency,
            tools=self.tools, # Activamos las herramientas
            conversation=self.conversation,
            context=self.context
        )
        
        llm_stream = await self.command_bus.execute_command(llm_command_full)
        
        # 6. Procesar Stream (Function Calling)
        processed_text_stream = self._process_llm_stream(llm_stream, final_text)
        
        # 7. TTS Stream (Via Command Bus)
        # Nota: synthesize_stream espera un generador, processed_text_stream lo es.
        # Pero execute_command es awaitable.
        tts_command = SynthesizeTTSCommand(text_stream=processed_text_stream)
        audio_stream = await self.command_bus.execute_command(tts_command)
        
        return final_text, audio_stream

    async def _stream_distributor(self, audio_stream, stt_queue, affect_queue):
         """Distribuidor de chunks a colas para paralelismo"""
         try:
             async for chunk in audio_stream:
                 await stt_queue.put(chunk)
                 await affect_queue.put(chunk)
             await stt_queue.put(None)
             await affect_queue.put(None)
         except Exception as e:
             print(f"Error en stream distributor: {e}")
             await stt_queue.put(None)
             await affect_queue.put(None)

    async def _queue_gen(self, q: asyncio.Queue) -> AsyncGenerator:
        """Convierte cola en generador asíncrono"""
        while True:
            item = await q.get()
            if item is None: break
            yield item

    async def _proactive_pipeline(self, text_stream: AsyncGenerator[str, None]) -> tuple[str, str]:
        """
        Consume el stream de texto, detecta intención temprana y lanza búsqueda RAG.
        Devuelve el texto final y el contexto recuperado.
        """
        final_text = ""
        rag_task = None
        rag_triggered = False
        
        print("⚡ Iniciando Pipeline Proactivo...")
        
        async for text_chunk in text_stream:
            final_text = text_chunk
            
            # Heurística simple: Si tenemos más de 4 palabras y no hemos lanzado RAG, hazlo.
            words = final_text.split()
            if len(words) >= 4 and not rag_triggered:
                print(f"🚀 Trigger Proactivo RAG con: '{final_text}'")
                rag_triggered = True
                # Lanzar Query Bus en background
                query = SearchKnowledgeQuery(query_text=final_text)
                rag_task = asyncio.create_task(self.command_bus.execute_query(query))
        
        # Esperar resultado de RAG si se lanzó
        kb_context = ""
        if rag_task:
            print("⏳ Esperando RAG (si no terminó ya)...")
            kb_context = await rag_task
            print("✓ Contexto RAG listo")
        elif final_text:
            # Si fue muy corto y no disparó trigger, buscar ahora
            query = SearchKnowledgeQuery(query_text=final_text)
            kb_context = await self.command_bus.execute_query(query)
            
        return final_text, kb_context

    async def _process_llm_stream(self, llm_stream: AsyncGenerator[str, None], user_text: str) -> AsyncGenerator[str, None]:
        """
        Consume el stream del LLM. Si detecta una llamada a función, la ejecuta
        y genera la respuesta textual del resultado. Si es texto, lo pasa.
        """
        full_response_text = []
        function_call_detected = False
        
        async for chunk in llm_stream:
            if chunk.startswith("__FUNCTION_CALL__:"):
                function_call_detected = True
                json_str = chunk.replace("__FUNCTION_CALL__:", "")
                
                try:
                    fc_data = json.loads(json_str)
                    print(f"⚡ Ejecutando Herramienta: {fc_data['name']}")
                    
                    # Ejecutar lógica de negocio
                    result_text = await self._execute_tool(fc_data['name'], fc_data['args'])
                    
                    # Yield del resultado para que el TTS lo diga
                    yield result_text
                    full_response_text.append(result_text)
                    
                except Exception as e:
                    print(f"✗ Error ejecutando herramienta: {e}")
                    err_msg = "Tuve un problema técnico al procesar tu solicitud."
                    yield err_msg
                    full_response_text.append(err_msg)
            else:
                # Texto normal
                yield chunk
                full_response_text.append(chunk)
        
        # Guardar en historial DESPUÉS del loop (no en finally con await)
        complete_text = "".join(full_response_text)
        if complete_text and self.conversation:
            self.conversation.add_message(Message(complete_text, MessageRole.ASSISTANT))
        
        # Log Interaction via Command Bus (sin await en generator)
        # Usamos create_task para fire-and-forget sin bloquear
        if complete_text:
            intent = "FUNCTION_CALL" if function_call_detected else "INFO"
            cmd = LogInteractionCommand(user_text=user_text, intent=intent, response_text=complete_text)
            asyncio.create_task(self.command_bus.execute_command(cmd))

    async def _execute_tool(self, name: str, args: dict) -> str:
        """Dispatcher de herramientas"""
        if name == "make_booking":
            return await self._tool_make_booking(args)
        elif name == "check_in_info":
            return "El check-in es a partir de las 15:00 horas. Necesitarás tu documento de identidad."
        elif name == "contact_support":
            return "Puedes marcar el 9 desde tu habitación para hablar con recepción."
        else:
            return "No puedo realizar esa acción por el momento."

    async def _tool_make_booking(self, args: dict) -> str:
        """Lógica de reserva"""
        date = args.get("date", "hoy")
        time_val = args.get("time", "20:00")
        people = args.get("people", 2)
        
        # Persistencia via Command Bus
        cmd = SaveBookingCommand(booking_data={
            "name": "Usuario Voz (Context)",
            "date": f"{date} {time_val}",
            "people": people
        })
        await self.command_bus.execute_command(cmd)
            
        # Guardar en Contexto (Memoria a Largo Plazo)
        if self.context:
            self.context.set_state("last_booking", {"date": date, "time": time_val})
            
        return f"¡Listo! He reservado mesa para {people} personas el {date} a las {time_val}."

    async def _quick_tts_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """Helper para respuestas rápidas"""
        cmd = SynthesizeTTSCommand(text_stream=self._async_iter([text]))
        tts_resp = await self.command_bus.execute_command(cmd)
        async for chunk in tts_resp:
            yield chunk

    async def _async_iter(self, items: list) -> AsyncGenerator[str, None]:
        for item in items:
            yield item

    def set_conversation(self, conversation: Conversation) -> None:
        self.conversation = conversation
        # Inicializar contexto si no existe
        if conversation and not self.context:
            self.context = ConversationContext(conversation.session_id)
    
    def get_conversation(self) -> Optional[Conversation]:
        return self.conversation
