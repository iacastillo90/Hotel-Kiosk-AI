import numpy as np
from typing import AsyncGenerator
from app.ports.output.affect_port import AffectPort

class AcousticAdapter(AffectPort):
    """
    Adaptador acústico básico.
    Usa heurísticas de energía (volumen) para inferir estados simples.
    """
    
    async def analyze_stream(self, audio_stream: AsyncGenerator[bytes, None]) -> str:
        """
        Analiza la energía del audio para detectar frustración (gritos/volumen alto).
        """
        max_energy = 0.0
        avg_energy = 0.0
        chunk_count = 0
        
        # Umbrales (calibrar según micrófono)
        # Asumiendo float32 normalizado o int16 convertido
        HIGH_ENERGY_THRESHOLD = 0.5 # Si normalizado 0-1
        
        try:
            # Consumimos el stream (OJO: Esto consume el generador, 
            # así que necesitamos un mecanismo para duplicar el stream en el servicio
            # o pasar una copia. En Python los generadores se agotan.
            # El AssistantService deberá usar 'tee' o similar si quiere pasar el MISMO stream a STT y Affect.
            # O mejor, el AssistantService recibe chunks y los distribuye a colas.)
            
            # NOTA: Por simplicidad en esta fase, asumiremos que recibimos una COPIA del stream 
            # o que el AssistantService maneja la duplicación.
            
            async for chunk in audio_stream:
                if not chunk: continue
                
                # Convertir a numpy para análisis rápido
                # Asumimos int16 (lo estándar de pyaudio)
                data = np.frombuffer(chunk, dtype=np.int16)
                
                # Normalizar a 0-1
                normalized = np.abs(data) / 32768.0
                
                chunk_energy = np.mean(normalized)
                max_energy = max(max_energy, np.max(normalized))
                
                avg_energy += chunk_energy
                chunk_count += 1
            
            if chunk_count == 0:
                return "Neutral"
            
            final_avg = avg_energy / chunk_count
            
            # Heurística simple
            if max_energy > 0.8: # Picos muy altos
                return "Frustrado (Volumen Alto)"
            elif final_avg > 0.3: # Volumen promedio alto
                return "Urgente/Alto"
            else:
                return "Neutral"
                
        except Exception as e:
            print(f"⚠️ Error en AcousticAdapter: {e}")
            return "Neutral"
