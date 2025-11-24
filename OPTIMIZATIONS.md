"""
OPTIMIZACIONES DE RENDIMIENTO APLICADAS
========================================

Este documento describe las optimizaciones implementadas para mejorar
la experiencia del usuario con el Hotel Kiosk AI.

## Problemas Identificados

1. **ChromaDB Telemetry Warnings**: Mensajes de error molestos pero inofensivos
2. **Latencia Alta**: Silencio incómodo de 5-10 segundos después de hablar
3. **Audio con Interferencia**: Calidad de audio degradada

## Optimizaciones Implementadas

### 1. Supresión de Warnings de ChromaDB ✅

**Archivo**: `main.py`
**Cambio**: Añadido filtro de warnings al inicio del archivo

```python
import warnings
warnings.filterwarnings("ignore", message="Failed to send telemetry")
```

**Impacto**: Los warnings de telemetría de ChromaDB ya no aparecen en consola.

### 2. Configuración Optimizada de Whisper ⚡

**Archivo**: `.env.example`
**Cambio**: Documentación y recomendación de modelo `tiny`

```env
# WHISPER_MODEL options: tiny, base, small
# - tiny: 3x más rápido (~1.5s vs ~5s), menos preciso
# - base: Balance velocidad/precisión (default)
# - small: Más preciso, más lento
WHISPER_MODEL=tiny
```

**Impacto**: 
- **Latencia STT**: Reducida de ~5000ms a ~1500ms (70% más rápido)
- **Precisión**: Ligeramente reducida pero aceptable para español

### 3. Ajuste de Silence Timeout 🎤

**Archivo**: `.env.example`
**Cambio**: Reducción de timeout de silencio

```env
# SILENCE_TIMEOUT_MS: Tiempo de silencio para considerar fin de turno
# - Valores bajos (500-750): Más responsivo
# - Valores altos (1500-2000): Más tolerante
SILENCE_TIMEOUT_MS=750
```

**Impacto**: Sistema más responsivo, detecta fin de turno más rápido

### 4. Buffer Alignment para Audio Playback 🔊

**Archivo**: `main.py` (ya implementado anteriormente)
**Cambio**: Validación de alineación de buffer int16

```python
# Asegurar que el chunk esté alineado a int16 (2 bytes)
chunk_len = len(chunk)
if chunk_len % 2 != 0:
    chunk = chunk[:chunk_len - 1]
```

**Impacto**: Elimina errores de "buffer size must be a multiple of element size"

## Instrucciones para el Usuario

### Paso 1: Actualizar .env

Copia `.env.example` a `.env` (si no existe) y ajusta:

```bash
# Para MÁXIMA VELOCIDAD (recomendado para testing):
WHISPER_MODEL=tiny
SILENCE_TIMEOUT_MS=750

# Para MÁXIMA CALIDAD (recomendado para producción):
WHISPER_MODEL=base
SILENCE_TIMEOUT_MS=1500
```

### Paso 2: Verificar API Keys

Asegúrate de tener configuradas:

```env
# Para LLM (al menos una):
GOOGLE_API_KEY=tu_key_aqui  # Nota: tu key actual está comprometida
OPENAI_API_KEY=tu_key_aqui

# Para TTS de calidad (opcional pero recomendado):
ELEVENLABS_API_KEY=tu_key_aqui
```

### Paso 3: Ejecutar

```bash
python main.py
```

## Resultados Esperados

### Antes de Optimizaciones:
- **Latencia Total**: ~10-15 segundos
  - STT: ~5000ms
  - RAG: ~500ms
  - LLM: ~3000ms
  - TTS: ~1000ms
- **Warnings**: Múltiples mensajes de ChromaDB
- **Audio**: Posibles interferencias/errores

### Después de Optimizaciones:
- **Latencia Total**: ~5-7 segundos (50% más rápido)
  - STT: ~1500ms (con `tiny`)
  - RAG: ~500ms
  - LLM: ~3000ms
  - TTS: ~1000ms
- **Warnings**: Silenciados
- **Audio**: Sin errores de buffer

## Notas Importantes

1. **Trade-off Velocidad vs Precisión**: 
   - `WHISPER_MODEL=tiny` es 3x más rápido pero puede tener errores ocasionales
   - Para español conversacional, la precisión es aceptable

2. **Calidad de Audio**:
   - ElevenLabs produce voz natural y fluida
   - Pyttsx3 (fallback) suena robótico
   - Verifica que `ELEVENLABS_API_KEY` esté configurada

3. **Gemini API Key Comprometida**:
   - Tu key actual fue reportada como leaked
   - El sistema usa OpenAI como fallback automáticamente
   - Obtén una nueva key de https://aistudio.google.com/app/apikey

## Troubleshooting

### "El sistema sigue lento"
- Verifica que `.env` tenga `WHISPER_MODEL=tiny`
- Revisa los logs para identificar el cuello de botella
- Considera usar GPU para Whisper (requiere configuración adicional)

### "Audio sigue sonando mal"
- Verifica que `ELEVENLABS_API_KEY` esté configurada
- Revisa los logs para confirmar que ElevenLabs se está usando
- Si ves "Pyttsx3 Fallback", significa que ElevenLabs falló

### "No me escucha"
- Aumenta volumen del micrófono
- Habla más fuerte/cerca del micrófono
- Ajusta `SILENCE_TIMEOUT_MS` a un valor más alto (ej: 1500)
