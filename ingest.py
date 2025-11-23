import asyncio
import os
from dotenv import load_dotenv
from config.settings import Settings
from config.container import DIContainer
from app.domain.services.document_loader import DocumentLoader

async def ingest_data():
    """
    Lee documentos de 'data/documents' y los guarda en ChromaDB.
    """
    load_dotenv()
    settings = Settings()
    
    # Forzamos uso de DB real si la tienes, o local
    container = DIContainer(settings)
    
    # Inicializar solo la Knowledge Base (no necesitamos audio ni STT aquí)
    kb_port = container.get_kb_port()
    
    # 1. Cargar documentos del disco
    docs_folder = "./data/documents"
    loader = DocumentLoader(docs_folder)
    
    print(f"\n📚 INICIANDO INGESTA DE CONOCIMIENTO")
    print("="*50)
    
    extracted_docs = loader.load_documents()
    
    if not extracted_docs:
        print("\n⚠️ No se encontraron documentos o texto válido.")
        print(f"👉 Pon tus PDFs, Word o Txt en: {os.path.abspath(docs_folder)}")
        return

    # 2. Guardar en Base de Datos Vectorial (ChromaDB)
    print(f"\n💾 Guardando {len(extracted_docs)} fragmentos en la memoria de la IA...")
    
    try:
        # Usamos 'add_documents' del puerto. 
        # NOTA: Esto se suma a lo que ya existe.
        await kb_port.add_documents(
            documents=extracted_docs,
            metadata={"source": "local_files", "type": "dynamic"}
        )
        print("\n✅ ¡ÉXITO! El asistente ha aprendido la nueva información.")
        print("   Ahora puedes ejecutar 'python main.py' y preguntar sobre estos temas.")
        
    except Exception as e:
        print(f"\n✗ Error guardando en BD: {e}")

if __name__ == "__main__":
    asyncio.run(ingest_data())
