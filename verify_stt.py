import sys
import os
import asyncio
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from adapters.output.speech.whisper_local_adapter import WhisperLocalAdapter

async def main():
    print("Initializing WhisperLocalAdapter...")
    try:
        adapter = WhisperLocalAdapter(model_size="tiny", language="es") # Use tiny for quick test
        print("Model loaded successfully.")
        
        # Create dummy audio (1 second of silence)
        # 16000 Hz, 1 channel, int16
        dummy_audio = np.zeros(16000, dtype=np.int16).tobytes()
        
        print("Testing transcription with silence...")
        response = await adapter.transcribe(dummy_audio)
        print(f"Transcription result: '{response.text}'")
        print(f"Latency: {response.latency_ms:.2f}ms")
        print("Verification passed!")
        
    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
