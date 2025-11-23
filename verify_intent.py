import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.domain.services.intent_service import IntentService, Intent

def test_intent(service, text, expected_intent):
    result = service.detect_intent(text)
    print(f"Text: '{text}' -> Detected: {result.intent.value} (Expected: {expected_intent.value})")
    if result.intent == expected_intent:
        print("✅ PASS")
    else:
        print("❌ FAIL")

def main():
    print("Initializing IntentService...")
    service = IntentService()
    
    print("\n--- Testing Intents ---")
    
    # Greeting
    test_intent(service, "Hola, buenos días", Intent.GREETING)
    test_intent(service, "Hey, qué tal", Intent.GREETING)
    
    # Check-in
    test_intent(service, "Quiero hacer el check-in", Intent.CHECK_IN)
    test_intent(service, "Necesito registrarme", Intent.CHECK_IN)
    
    # Booking
    test_intent(service, "Me gustaría reservar una habitación", Intent.BOOKING)
    test_intent(service, "Quiero una reserva para mañana", Intent.BOOKING)
    
    # Contact
    test_intent(service, "Necesito hablar con alguien", Intent.CONTACT)
    test_intent(service, "Cuál es el teléfono de contacto", Intent.CONTACT)
    
    # Info
    test_intent(service, "¿A qué hora es el desayuno?", Intent.INFO)
    test_intent(service, "¿Tienen gimnasio?", Intent.INFO)
    test_intent(service, "¿Dónde está la piscina?", Intent.INFO)
    
    # Unknown
    test_intent(service, "Esto es una frase aleatoria que no debería entender", Intent.UNKNOWN)

if __name__ == "__main__":
    main()
