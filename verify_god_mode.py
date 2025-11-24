import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.domain.services.command_bus import CommandBus
from app.domain.services.prompt_factory import PromptFactory
from app.domain.commands import GenerateLLMStreamCommand
from app.ports.output.llm_port import LLMPort, LLMRequest

# Mocks
class MockGemini(LLMPort):
    async def generate_stream(self, request: LLMRequest):
        print("🔴 Gemini: Intentando generar...")
        raise Exception("Simulated Gemini Failure") # Simula fallo
        yield "unreachable"
    async def health_check(self): return False

class MockOpenAI(LLMPort):
    async def generate_stream(self, request: LLMRequest):
        print(f"🟢 OpenAI (Fallback): Generando respuesta... [Prompt: {request.system_prompt[:30]}...]")
        yield "Respuesta salvada por OpenAI."
    async def health_check(self): return True

async def main():
    print("--- 🧪 INICIANDO PRUEBA DE FUEGO: WAUOO NIVEL DIOS ---")
    
    # 1. Setup Self-Healing Chain
    llm_chain = [MockGemini(), MockOpenAI()]
    
    # 2. Setup Prompt Factory
    prompt_factory = PromptFactory()
    
    # 3. Setup Command Bus
    bus = CommandBus(
        llm_chain=llm_chain,
        tts_chain=[], # No needed for this test
        kb_port=MagicMock(),
        repository_port=MagicMock(),
        prompt_factory=prompt_factory
    )
    
    # 4. Test Case 1: Frustrated User + High Latency (Should trigger Empathetic Prompt + Failover)
    print("\n[ESCENARIO 1] Usuario Frustrado + Fallo en Gemini")
    cmd = GenerateLLMStreamCommand(
        user_message="¡Esto no funciona!",
        emotional_state="Frustrado",
        system_latency_ms=2500, # High latency
        kb_confidence=0.9
    )
    
    try:
        stream = await bus.execute_command(cmd)
        async for chunk in stream:
            print(f"📢 Output: {chunk}")
    except Exception as e:
        print(f"❌ Test Failed: {e}")

    # 5. Test Case 2: Low Confidence (Should trigger Cautious Prompt)
    print("\n[ESCENARIO 2] Baja Confianza KB")
    cmd2 = GenerateLLMStreamCommand(
        user_message="¿Tienen piscina en la azotea?",
        emotional_state="Neutral",
        kb_confidence=0.3 # Low confidence
    )
    
    # For this test we can inspect the generated request via a spy if we wanted, 
    # but here we just trust the output or add print in MockOpenAI
    
    stream = await bus.execute_command(cmd2)
    async for chunk in stream:
        pass # Just consume

    print("\n--- ✅ PRUEBA COMPLETADA ---")

if __name__ == "__main__":
    asyncio.run(main())
