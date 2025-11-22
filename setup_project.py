#!/usr/bin/env python3
"""
setup_project.py - Generador automático de estructura de carpetas
para Hotel Kiosk AI siguiendo Arquitectura Hexagonal
"""

import os
from pathlib import Path

def create_directory_structure():
    """Crea la estructura completa de directorios y archivos __init__.py"""
    
    # Estructura base del proyecto
    structure = {
        "app": {
            "__init__.py": "",
            "domain": {
                "__init__.py": "",
                "entities": {
                    "__init__.py": "",
                    "message.py": "",
                    "hotel.py": "",
                    "conversation.py": "",
                },
                "services": {
                    "__init__.py": "",
                    "assistant_service.py": "",
                    "intent_service.py": "",
                    "conversation_context.py": "",
                }
            },
            "ports": {
                "__init__.py": "",
                "input": {
                    "__init__.py": "",
                    "audio_input_port.py": "",
                },
                "output": {
                    "__init__.py": "",
                    "llm_port.py": "",
                    "stt_port.py": "",
                    "tts_port.py": "",
                    "knowledge_base_port.py": "",
                }
            }
        },
        "adapters": {
            "__init__.py": "",
            "utils": {
                "__init__.py": "",
                "resilience.py": "",
            },
            "input": {
                "__init__.py": "",
                "mic_listener": {
                    "__init__.py": "",
                    "vad_filter.py": "",
                    "pyaudio_handler.py": "",
                },
                "mic_listener_adapter.py": "",
            },
            "output": {
                "__init__.py": "",
                "llm": {
                    "__init__.py": "",
                    "gemini_adapter.py": "",
                    "openai_adapter.py": "",
                },
                "speech": {
                    "__init__.py": "",
                    "whisper_local_adapter.py": "",
                    "elevenlabs_adapter.py": "",
                    "pyttsx3_fallback_adapter.py": "",
                },
                "database": {
                    "__init__.py": "",
                    "chroma_adapter.py": "",
                },
                "external": {
                    "__init__.py": "",
                    "restaurant_booking_adapter.py": "",
                },
                "logging": {
                    "__init__.py": "",
                    "analytics_adapter.py": "",
                }
            }
        },
        "config": {
            "__init__.py": "",
            "settings.py": "",
            "container.py": "",
        },
        "data": {
            "chroma_db": {},
            "temp_audio": {},
        },
        "logs": {},
    }
    
    # Archivos raíz
    root_files = {
        "main.py": "",
        "requirements.txt": "",
        ".env.example": "",
        ".gitignore": "",
        "README.md": "",
        "Dockerfile": "",
    }
    
    def create_structure(base_path: Path, structure: dict):
        """Recursivamente crea directorios y archivos"""
        for name, content in structure.items():
            path = base_path / name
            
            if isinstance(content, dict):
                # Es un directorio
                path.mkdir(parents=True, exist_ok=True)
                print(f"✓ Creado directorio: {path}")
                create_structure(path, content)
            else:
                # Es un archivo
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
                    print(f"✓ Creado archivo: {path}")
                else:
                    print(f"⚠ Ya existe: {path}")
    
    # Crear estructura
    print("\n" + "="*60)
    print("🏗️  Generando estructura de proyecto Hotel Kiosk AI")
    print("="*60 + "\n")
    
    base = Path.cwd()
    
    # Crear directorios del proyecto
    create_structure(base, structure)
    
    # Crear archivos raíz
    print("\n📄 Creando archivos raíz...")
    for filename, content in root_files.items():
        filepath = base / filename
        if not filepath.exists():
            filepath.touch()
            print(f"✓ Creado: {filename}")
        else:
            print(f"⚠ Ya existe: {filename}")
    
    print("\n" + "="*60)
    print("✅ Estructura de proyecto creada exitosamente")
    print("="*60)
    print("\n📁 Árbol de directorios generado:")
    print("""
hotel_kiosk_ai/
├── app/
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── message.py
│   │   │   ├── hotel.py
│   │   │   └── conversation.py
│   │   └── services/
│   │       ├── assistant_service.py
│   │       ├── intent_service.py
│   │       └── conversation_context.py
│   └── ports/
│       ├── input/
│       │   └── audio_input_port.py
│       └── output/
│           ├── llm_port.py
│           ├── stt_port.py
│           ├── tts_port.py
│           └── knowledge_base_port.py
├── adapters/
│   ├── utils/
│   │   └── resilience.py
│   ├── input/
│   │   ├── mic_listener/
│   │   │   ├── vad_filter.py
│   │   │   └── pyaudio_handler.py
│   │   └── mic_listener_adapter.py
│   └── output/
│       ├── llm/
│       ├── speech/
│       ├── database/
│       ├── external/
│       └── logging/
├── config/
│   ├── settings.py
│   └── container.py
├── data/
│   ├── chroma_db/
│   └── temp_audio/
├── logs/
├── main.py
├── requirements.txt
├── .env.example
└── Dockerfile
    """)

if __name__ == "__main__":
    try:
        create_directory_structure()
        print("\n🎉 Proyecto listo para comenzar el desarrollo\n")
        print("📌 Próximos pasos:")
        print("   1. Revisar la estructura generada")
        print("   2. Implementar las entidades de dominio")
        print("   3. Definir los contratos (Ports)")
        print("   4. Desarrollar los adaptadores")
        print("   5. Configurar la inyección de dependencias")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
