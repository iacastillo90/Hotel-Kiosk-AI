from typing import Optional
from app.ports.output.llm_port import LLMRequest
from app.domain.commands import GenerateLLMStreamCommand
from app.domain.entities.conversation import Conversation
from app.domain.services.conversation_context import ConversationContext

class PromptFactory:
    """
    Fábrica de Prompts Dinámicos (Autonomía Cognitiva).
    Genera la personalidad y estrategia del asistente en tiempo real.
    """
    
    def generate_llm_request(self, command: GenerateLLMStreamCommand, 
                             conversation: Optional[Conversation], 
                             context: Optional[ConversationContext]) -> LLMRequest:
        
        # 1. Determinar Personalidad Dinámica
        personalidad = self._determine_personality(command)
        
        # 2. Construir System Prompt
        system_prompt = self._build_system_prompt(personalidad, command)
        
        # 3. Obtener Historial (si existe conversación)
        conversation_history = conversation.get_recent_context(8) if conversation else ""
        
        return LLMRequest(
            user_message=command.user_message,
            conversation_history=conversation_history,
            hotel_context=command.hotel_context,
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
            return "un Asistente de Resolución de Conflictos, empático, calmado y eficiente"
        elif command.kb_confidence < 0.5:
            return "un Asistente Cauteloso, que verifica todo y no asume información"
        elif command.system_latency_ms > 2000:
            return "un Asistente Ágil, que va directo al grano para compensar la espera"
        else:
            return "un Concierge Virtual de Hotel de 5 estrellas, profesional y cálido"

    def _build_system_prompt(self, personalidad: str, command: GenerateLLMStreamCommand) -> str:
        """Construye el prompt completo."""
        base_prompt = f"""Eres {personalidad}.
Reglas Fundamentales:
- Tu objetivo es servir al huésped del Hotel Paradise Resort.
- Responde siempre en español.
- Sé conciso (máximo 2-3 oraciones) para una conversación fluida por voz.
- Si no sabes algo, admítelo y ofrece llamar a recepción.
"""

        # Reglas Adaptativas (Meta-Cognición)
        meta_rules = ""
        if command.emotional_state in ["Frustrado", "Enojo"]:
            meta_rules += "- El usuario parece molesto. Discúlpate por cualquier inconveniente y prioriza la solución.\n"
        
        if command.kb_confidence < 0.5:
            meta_rules += "- La información de tu base de conocimientos es incierta. Usa frases como 'Según tengo entendido...' o 'Podría ser...'.\n"
            
        if command.system_latency_ms > 2000:
            meta_rules += "- El sistema ha tardado en responder. Agradece la paciencia o sé muy breve.\n"

        return base_prompt + "\nEstrategia de Respuesta:\n" + meta_rules
