import time
from typing import Optional

# Imports SOLO de domain y ports (Python puro, sin librerías externas)
from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Message, MessageRole
from app.ports.output.llm_port import LLMPort, LLMRequest
from app.ports.output.stt_port import STTPort
from app.ports.output.tts_port import TTSPort, TTSRequest
from app.ports.output.knowledge_base_port import KnowledgeBasePort, KnowledgeBaseQuery
from app.ports.output.repository_port import RepositoryPort
from app.domain.services.intent_service import IntentService, Intent


class AssistantService:
    """
    Orquestador principal del sistema CON ROUTING INTELIGENTE.
    Implementa la lógica de negocio: Audio → Texto → Intent → Respuesta → Audio
    
    CORRECCIÓN CRÍTICA #3: Ahora usa IntentService para detectar intenciones
    y enrutar a flujos especializados (reservas, check-in, etc).
    
    IMPORTANTE: Este servicio NO conoce detalles de implementación.
    Solo trabaja con los contratos (Ports) y entidades (Domain).
    """
    
    def __init__(self,
                 llm_port: LLMPort,
                 stt_port: STTPort,
                 tts_port: TTSPort,
                 kb_port: KnowledgeBasePort,
                 repository_port: RepositoryPort):
        """
        Constructor con inyección de dependencias.
        
        Args:
            llm_port: Implementación del contrato LLM
            stt_port: Implementación del contrato STT
            tts_port: Implementación del contrato TTS
            kb_port: Implementación del contrato Knowledge Base
        """
        self.llm_port = llm_port
        self.stt_port = stt_port
        self.tts_port = tts_port
        self.kb_port = kb_port
        self.repository_port = repository_port
        self.conversation: Optional[Conversation] = None
        
        # NUEVO: Intent Service para routing inteligente
        self.intent_service = IntentService()
    
    async def process_audio(self, audio_bytes: bytes) -> tuple[str, bytes]:
        """
        Flujo completo del sistema CON INTENT ROUTING:
        1. STT: Audio → Texto
        2. INTENT: Detecta intención del usuario
        3. ROUTING: Según intent, elige flujo (info, reserva, check-in)
        4. TTS: Texto → Audio
        
        Args:
            audio_bytes: Audio capturado del micrófono
            
        Returns:
            Tupla (texto_respuesta, audio_respuesta)
            
        Raises:
            Exception: Si algún componente falla críticamente
        """
        start_time = time.time()
        
        try:
            # ===================================================================
            # PASO 1: Transcribir audio a texto (STT)
            # ===================================================================
            stt_response = await self.stt_port.transcribe(audio_bytes)
            user_text = stt_response.text
            
            if not user_text.strip():
                # Audio vacío o ininteligible
                fallback_text = "No entendí bien lo que dijiste. ¿Podrías repetir?"
                return fallback_text, b""
            
            print(f"🎤 Usuario: {user_text}")
            
            # Añadir mensaje del usuario al historial
            if self.conversation:
                self.conversation.add_message(
                    Message(user_text, MessageRole.USER)
                )
            
            # ===================================================================
            # PASO 2: DETECTAR INTENCIÓN (NUEVO)
            # ===================================================================
            intent_result = self.intent_service.detect_intent(user_text)
            print(f"🎯 Intent detectado: {intent_result.intent.value} (confianza: {intent_result.confidence:.2f})")
            
            # ===================================================================
            # PASO 3: ROUTING SEGÚN INTENT
            # ===================================================================
            if intent_result.intent == Intent.GREETING:
                # Saludo: Respuesta rápida sin RAG
                assistant_text = await self._handle_greeting(user_text)
                
            elif intent_result.intent == Intent.BOOKING:
                # Reserva: Flujo especializado
                assistant_text = await self._handle_booking(user_text, intent_result.entities)
                
            elif intent_result.intent == Intent.CHECK_IN:
                # Check-in: Flujo especializado
                assistant_text = await self._handle_checkin(user_text)
                
            elif intent_result.intent == Intent.CONTACT:
                # Contacto: Respuesta directa sin LLM
                assistant_text = await self._handle_contact(user_text)
                
            else:
                # INFO o UNKNOWN: Flujo estándar (RAG + LLM)
                assistant_text = await self._handle_info(user_text)
            
            # Añadir respuesta del asistente al historial
            if self.conversation:
                self.conversation.add_message(
                    Message(assistant_text, MessageRole.ASSISTANT)
                )
            
            # ===================================================================
            # PASO 4: Sintetizar respuesta a audio (TTS)
            # ===================================================================
            tts_response = await self.tts_port.synthesize(
                TTSRequest(text=assistant_text, language="es")
            )
            
            # Calcular latencia total
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"✓ Procesamiento completo: {elapsed_ms:.1f}ms")
            
            # 5. PERSISTENCIA (Async)
            # Guardamos el log de la interacción sin bloquear
            if self.repository_port:
                await self.repository_port.log_interaction(
                    user_text=user_text,
                    intent=intent_result.intent.value,
                    response=assistant_text
                )
            
            return assistant_text, tts_response.audio_bytes
            
        except Exception as e:
            print(f"✗ Error en process_audio: {e}")
            raise
    
    # =========================================================================
    # HANDLERS POR INTENT (Flujos Especializados)
    # =========================================================================
    
    async def _handle_greeting(self, user_text: str) -> str:
        """Maneja saludos sin necesidad de RAG/LLM"""
        greetings = [
            "¡Hola! Bienvenido a nuestro hotel. ¿En qué puedo ayudarte?",
            "¡Buenos días! Soy tu asistente virtual. ¿Qué necesitas saber?",
            "¡Hola! Estoy aquí para ayudarte con cualquier consulta sobre el hotel."
        ]
        import random
        return random.choice(greetings)
    
    async def _handle_booking(self, user_text: str, entities: dict) -> str:
        """Maneja reservas (ejemplo simplificado)"""
        if entities.get("date") and entities.get("time"):
            # Guardar reserva en BD
            if self.repository_port:
                await self.repository_port.save_booking({
                    "name": "Usuario Voz", # En futuro extraer nombre real
                    "date": f"{entities['date']} {entities['time']}"
                })
                
            return (
                f"Entendido, quieres reservar para el {entities['date']} a las {entities['time']}. "
                f"¿Para cuántas personas?"
            )
        else:
            return (
                "Me gustaría ayudarte con la reserva. "
                "¿Para qué fecha y hora necesitas?"
            )
    
    async def _handle_checkin(self, user_text: str) -> str:
        """Maneja check-in"""
        return (
            "Para realizar el check-in necesito tu número de reserva. "
            "También puedes hacerlo directamente en recepción a partir de las 15:00."
        )
    
    async def _handle_contact(self, user_text: str) -> str:
        """Maneja consultas de contacto"""
        return (
            "Puedes contactarnos llamando al +34-XXX-XXXX o enviando un email a info@hotel.com. "
            "Nuestra recepción está disponible 24/7."
        )
    
    async def _handle_info(self, user_text: str) -> str:
        """Flujo estándar: RAG + LLM para consultas de información"""
        # Buscar contexto relevante (RAG)
        kb_results = await self.kb_port.search(
            KnowledgeBaseQuery(
                query_text=user_text,
                top_k=3,
                min_score=0.5
            )
        )
        
        kb_context = "\n".join([r.content for r in kb_results])
        
        if kb_results:
            print(f"📚 Contexto encontrado: {len(kb_results)} documentos")
        
        # Generar respuesta con LLM
        conversation_history = ""
        if self.conversation:
            conversation_history = self.conversation.get_recent_context(5)
        
        llm_request = LLMRequest(
            user_message=user_text,
            conversation_history=conversation_history,
            hotel_context=kb_context,
            language="es"
        )
        
        llm_response = await self.llm_port.generate(llm_request)
        
        print(f"🤖 Asistente: {llm_response.text}")
        
        return llm_response.text
    
    def set_conversation(self, conversation: Conversation) -> None:
        """
        Establece la conversación activa.
        
        Args:
            conversation: Instancia de Conversation
        """
        self.conversation = conversation
    
    def get_conversation(self) -> Optional[Conversation]:
        """
        Retorna la conversación activa.
        
        Returns:
            Conversación actual o None
        """
        return self.conversation
