import os
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Settings:
    """
    Configuración centralizada desde variables de entorno (.env).
    
    Todas las configuraciones se cargan desde .env usando python-dotenv.
    Esto permite cambiar configuración sin modificar código.
    """
    
    # =========================================================================
    # LLM Configuration
    # =========================================================================
    llm_provider: Literal["gemini", "openai"] = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "gemini"))
    google_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    
    # =========================================================================
    # STT Configuration
    # =========================================================================
    whisper_model: Literal["tiny", "base", "small"] = field(default_factory=lambda: os.getenv("WHISPER_MODEL", "base"))
    stt_language: str = field(default_factory=lambda: os.getenv("STT_LANGUAGE", "es"))
    
    # =========================================================================
    # TTS Configuration
    # =========================================================================
    tts_provider: Literal["elevenlabs", "pyttsx3"] = field(default_factory=lambda: os.getenv("TTS_PROVIDER", "elevenlabs"))
    elevenlabs_api_key: str = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", ""))
    tts_voice_id: str = field(default_factory=lambda: os.getenv("TTS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"))
    
    # =========================================================================
    # Audio Configuration
    # =========================================================================
    sample_rate: int = field(default_factory=lambda: int(os.getenv("SAMPLE_RATE", "16000")))
    chunk_size: int = field(default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1024")))
    silence_timeout_ms: float = field(default_factory=lambda: float(os.getenv("SILENCE_TIMEOUT_MS", "1500")))
    
    # =========================================================================
    # Database Configuration
    # =========================================================================
    chroma_db_path: str = field(default_factory=lambda: os.getenv("CHROMA_DB_PATH", "./data/chroma_db"))
    
    # MySQL Settings
    use_database: bool = field(default_factory=lambda: os.getenv("USE_DATABASE", "False").lower() == "true")
    db_host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    db_port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "3306")))
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", "hotel_kiosk"))
    db_user: str = field(default_factory=lambda: os.getenv("DB_USER", "root"))
    db_password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", "root"))
    
    # =========================================================================
    # Debug
    # =========================================================================
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "False").lower() == "true")
    
    def validate(self) -> None:
        """
        Valida que la configuración sea completa.
        
        Raises:
            ValueError: Si faltan configuraciones críticas
        """
        errors = []
        
        # Validar LLM
        if self.llm_provider == "gemini" and not self.google_api_key:
            errors.append("❌ GOOGLE_API_KEY requerida para Gemini")
        
        if self.llm_provider == "openai" and not self.openai_api_key:
            errors.append("❌ OPENAI_API_KEY requerida para OpenAI")
        
        # Validar TTS
        if self.tts_provider == "elevenlabs" and not self.elevenlabs_api_key:
            errors.append("❌ ELEVENLABS_API_KEY requerida para ElevenLabs")
        
        # Validar audio
        if self.sample_rate not in [8000, 16000, 32000, 48000]:
            errors.append(f"❌ SAMPLE_RATE debe ser 8000, 16000, 32000 o 48000, recibido: {self.sample_rate}")
        
        if errors:
            raise ValueError("Configuración inválida:\n" + "\n".join(errors))
        
        print("✓ Configuración validada")
