# Usamos Python 3.11 Slim para mantener la imagen ligera pero compatible
FROM python:3.11-slim

# Variables de entorno para optimizar Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Importante para sonido en contenedores
    Keep_Audio_Running=1

# 1. Instalar dependencias de sistema (Heavy Lifting)
# - build-essential: para compilar librerías de C
# - portaudio19-dev: para PyAudio/SoundDevice
# - ffmpeg: para conversión de audio (ElevenLabs/Whisper)
# - libsndfile1: requerido por soundfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    portaudio19-dev \
    libasound2-dev \
    ffmpeg \
    libsndfile1 \
    espeak-ng \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Crear directorio de trabajo
WORKDIR /app

# 3. Copiar dependencias de Python primero (Cache Layering)
COPY requirements.txt .

# 4. Instalar dependencias
# Actualizamos pip y wheel primero
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el código fuente
COPY . .

# 6. Crear directorios para datos persistentes si no existen
RUN mkdir -p data/chroma_db

# 7. Comando de arranque por defecto
# Usamos python directo. Para producción real, usaríamos un supervisor, 
# pero para este Kiosco, directo es mejor para ver logs.
CMD ["python", "main.py", "interactive"]
