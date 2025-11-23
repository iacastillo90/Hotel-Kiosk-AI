import chromadb
import logging
import os
import asyncio
from typing import List
from app.ports.output.knowledge_base_port import KnowledgeBasePort, KnowledgeBaseQuery, KnowledgeBaseResult

# Configurar logger para ver qué pasa
logger = logging.getLogger(__name__)

class ChromaDBAdapter(KnowledgeBasePort):
    def __init__(self, db_path: str = "./data/chroma_db", collection_name: str = "hotel_knowledge"):
        """
        Inicializa la conexión persistente a ChromaDB.
        """
        # Asegurar ruta absoluta para evitar confusiones en Windows
        self.db_path = os.path.abspath(db_path)
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        
        print(f"📦 Conectando a ChromaDB en: {self.db_path}")
        
        try:
            # Usamos PersistentClient para asegurar que lea del disco
            self.client = chromadb.PersistentClient(path=self.db_path)
            
            # Obtenemos o creamos la colección
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            # DIAGNÓSTICO: Contar documentos al iniciar
            count = self.collection.count()
            print(f"📊 Estado de la Memoria: {count} documentos indexados.")
            
            if count == 0:
                logger.warning("⚠️ La base de datos está vacía. Ejecuta 'python ingest.py' primero.")
            else:
                print("✅ Memoria cargada correctamente.")
                
        except Exception as e:
            logger.error(f"❌ Error fatal inicializando ChromaDB: {e}")
            self.collection = None

    def is_ready(self) -> bool:
        """Verifica si la KB está lista"""
        return self.collection is not None and self.collection.count() > 0

    async def add_documents(self, documents: List[str], metadata: dict) -> None:
        """Añade documentos a la colección"""
        if not self.collection:
            logger.error("DB no inicializada, no se puede guardar.")
            return

        # Generar IDs únicos usando hash para evitar colisiones
        import uuid
        ids = [str(uuid.uuid4()) for _ in documents]
        metadatas = [metadata] * len(documents)
        
        try:
            # Ejecutar en executor para no bloquear
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            )
            logger.info(f"✓ {len(documents)} documentos añadidos a ChromaDB")
        except Exception as e:
            logger.error(f"Error añadiendo documentos: {e}")
            raise

    async def search(self, query: KnowledgeBaseQuery) -> List[KnowledgeBaseResult]:
        """Busca información relevante"""
        if not self.collection:
            logger.warning("⚠️ KB no inicializada, retornando vacío")
            return []
            
        # Verificar si hay datos antes de buscar
        if self.collection.count() == 0:
            logger.warning("⚠️ La KB está vacía (0 documentos).")
            return []

        try:
            # Ejecutar búsqueda en executor
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.collection.query(
                    query_texts=[query.query_text],
                    n_results=query.top_k
                )
            )
            
            kb_results = []
            if results['documents'] and results['documents'][0]:
                distances = results['distances'][0] if 'distances' in results else [0] * len(results['documents'][0])
                
                for i, doc in enumerate(results['documents'][0]):
                    # En ChromaDB, distancia coseno: 0 = idéntico, 2 = opuesto
                    distance = distances[i]
                    
                    # Convertir distancia a score (0-1)
                    score = 1 - (distance / 2)
                    
                    if score >= query.min_score:
                        kb_results.append(KnowledgeBaseResult(
                            content=doc,
                            source="chromadb",
                            score=score
                        ))
            
            logger.info(f"🔍 Búsqueda: '{query.query_text}' -> {len(kb_results)} resultados")
            return kb_results
            
        except Exception as e:
            logger.error(f"Error buscando en KB: {e}")
            return []

    def get_stats(self) -> dict:
        """Devuelve estadísticas para debugging"""
        return {
            "count": self.collection.count() if self.collection else 0,
            "path": self.db_path,
            "collection": self.collection_name,
            "status": "ok" if self.collection else "error"
        }
    
    def reset(self) -> None:
        """Resetea la base de datos (elimina colección)"""
        try:
            if self.collection:
                self.client.delete_collection(self.collection_name)
                self.collection = None
                print("✓ Colección eliminada")
        except Exception as e:
            print(f"⚠️ Error reseteando ChromaDB: {e}")
