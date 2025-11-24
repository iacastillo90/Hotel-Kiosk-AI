from typing import Optional
from app.ports.output.llm_port import LLMRequest
from app.domain.commands import GenerateLLMStreamCommand
from app.domain.entities.conversation import Conversation
from app.domain.services.conversation_context import ConversationContext

class PromptFactory:
    """
    Fábrica de Prompts Dinámicos (Autonomía Cognitiva & Concierge Mode).
    """
    
    def generate_llm_request(self, command: GenerateLLMStreamCommand, 
                             conversation: Optional[Conversation], 
                             context: Optional[ConversationContext]) -> LLMRequest:
        
        # 1. Determinar Personalidad Dinámica
        personalidad = self._determine_personality(command)
        
        # 2. Construir System Prompt (Ahora con lógica de entrevista)
        system_prompt = self._build_system_prompt(personalidad, command)
        
        # 3. Obtener Historial
        conversation_history = conversation.get_recent_context(8) if conversation else ""
        
        # 4. Context Trimming (Optimización TTFT)
        max_context_len = 2500 # Aumentamos un poco para incluir detalles de tours
        safe_context = command.hotel_context[:max_context_len] + "..." if command.hotel_context and len(command.hotel_context) > max_context_len else command.hotel_context

        return LLMRequest(
            user_message=command.user_message,
            conversation_history=conversation_history,
            hotel_context=safe_context,
            emotional_state=command.emotional_state,
            kb_confidence=command.kb_confidence,
            system_latency_ms=command.system_latency_ms,
            system_prompt=system_prompt,
            tools=command.tools,
            language=command.language
        )

    def _determine_personality(self, command: GenerateLLMStreamCommand) -> str:
        """Define la 'máscara' del asistente según el estado."""
        if command.emotional_state in ["Frustrado", "Enojo", "Urgente"]:
            return "un Asistente de Resolución de Conflictos"
        elif command.kb_confidence < 0.5:
            # Si no sabe la respuesta, es cauteloso
            return "un Asistente Cauteloso"
        else:
            # Por defecto es el Concierge Experto
            return "un Concierge Local Experto del Hotel Paradise Resort"

    def _build_system_prompt(self, personalidad: str, command: GenerateLLMStreamCommand) -> str:
        base_prompt = f"""Eres {personalidad}.

OBJETIVO PRINCIPAL:
Ayudar al huésped a vivir la mejor experiencia en la Riviera Maya basándote EXCLUSIVAMENTE en el CONTEXTO DEL HOTEL proporcionado.

REGLAS DE ORO (COMPORTAMIENTO):
1. RESPUESTA DIRECTA: Si piden un dato concreto (hora, precio), dalo inmediatamente.
2. MODO CONCIERGE (RECOMENDACIONES):
   Si el usuario pide recomendaciones ABIERTAS (ej: "¿Qué puedo hacer hoy?", "¿A dónde voy?", "Turismo"), NO des una lista aleatoria.
   DEBES HACER UNA PREGUNTA DE FILTRADO PRIMERO:
   - "¿Buscas aventura (cenotes, tirolesas) o cultura (ruinas)?"
   - "¿Prefieres relajarte en la playa o ir de compras?"
   - "¿Vienes con niños y buscas un plan familiar?"
   
   Solo cuando el usuario responda a tu filtro, recomiéndale el lugar ideal del CONTEXTO, mencionando:
   A) Nombre del Lugar.
   B) Distancia/Tiempo desde el hotel (ej: "A solo 15 min en taxi").
   C) La Experiencia (ej: "Es ideal para caminar y ver historia...").

3. NUNCA repitas la pregunta del usuario.
4. Sé breve: Máximo 2-3 oraciones habladas.
5. Usa siempre precios y horarios reales del CONTEXTO si están disponibles.
"""

        # Reglas Adaptativas (Meta-Cognición)
        meta_rules = ""
        
        # Si la latencia fue alta, ser ultra-breve
        if command.system_latency_ms > 6000:
            meta_rules += "- Ha habido una demora técnica. Sé extremadamente breve.\n"
            
        # Si el usuario parece querer salir del hotel (detectado por palabras clave simples en el mensaje)
        user_msg_lower = command.user_message.lower()
        if any(x in user_msg_lower for x in ["hacer", "ir", "salir", "recomienda", "turiste", "pasear"]):
            meta_rules += "- El usuario busca actividades. Si no especificó qué le gusta, PREGUNTA sus preferencias (Aventura, Relax, Familia, Shopping) antes de sugerir.\n"

        return base_prompt + "\nINSTRUCCIONES ADICIONALES:\n" + meta_rules
