"""
Script to clean and reinitialize ChromaDB.
Run this when ChromaDB has schema corruption issues.
"""
import os
import shutil
import subprocess
import sys

def main():
    chroma_path = "data/chroma_db"
    
    print("🧹 Limpiando ChromaDB...")
    
    # Delete ChromaDB directory
    if os.path.exists(chroma_path):
        try:
            shutil.rmtree(chroma_path)
            print(f"✅ Eliminado: {chroma_path}")
        except Exception as e:
            print(f"❌ Error eliminando ChromaDB: {e}")
            print("⚠️ Cierra todas las instancias de main.py y vuelve a intentar")
            return 1
    else:
        print(f"✓ {chroma_path} no existe")
    
    # Regenerate hotel documents
    print("\n📝 Regenerando documentos del hotel...")
    result = subprocess.run([sys.executable, "data/documents/generate_hotel_documents.py"])
    if result.returncode != 0:
        print("❌ Error generando documentos")
        return 1
    
    # Ingest into ChromaDB
    print("\n📦 Ingiriendo datos en ChromaDB...")
    result = subprocess.run([sys.executable, "ingest.py"])
    if result.returncode != 0:
        print("❌ Error ingiriendo datos")
        return 1
    
    print("\n✅ ChromaDB limpio y listo!")
    print("Ahora puedes ejecutar: python main.py")
    return 0

if __name__ == "__main__":
    sys.exit(main())
