import asyncio
import chromadb
from typing import List

from app.ports.output.knowledge_base_port import (
    KnowledgeBasePort,
    KnowledgeBaseQuery,
    KnowledgeBaseResult
)


class ChromaDBAdapter(KnowledgeBasePort):
    """
    Adaptador para ChromaDB (Vector Store local).
    
    ChromaDB es una base de datos vectorial embebida que permite:
    - Búsqueda semántica (RAG - Retrieval Augmented Generation)
    - Embeddings automáticos
    - Persistencia local (sin servidor)
    - Rápido (consultas en ms)
    
    Flujo:
    1. Inicialización: Crea/carga colección
    2. Indexación: add_documents() → genera embeddings → almacena
    3. Búsqueda: search() → embedding de query → busca similares → retorna Top-K
    
    Ventajas:
    - 100% local (sin dependencias de red)
    - Gratis
    - Embeddings automáticos (usa sentence-transformers)
    - Simple de usar
    
    Casos de uso:
    - Base de conocimiento del hotel
    - FAQ
    - Documentación
    - Políticas y procedimientos
    """
    
    def __init__(self, db_path: str = "./data/chroma_db"):
        """
        Constructor.
        
        Args:
            db_path: Ruta donde persistir la base de datos
        """
        print(f"📦 Inicializando ChromaDB en {db_path}...")
        
        try:
            # Inicializar cliente ChromaDB con persistencia (nueva API)
            self.db = chromadb.PersistentClient(path=db_path)
            
            self.collection = None
            self.db_path = db_path
            
            print("✓ ChromaDB inicializado")
            
        except Exception as e:
            print(f"✗ Error inicializando ChromaDB: {e}")
            raise
    
    def is_ready(self) -> bool:
        """
        Verifica si la KB está lista para usar.
        
        Returns:
            True si la colección está creada e indexada
        """
        return self.collection is not None
    
    async def add_documents(self, documents: List[str], metadata: dict) -> None:
        """
        Añade documentos a la colección.
        
        ChromaDB automáticamente:
        1. Genera embeddings usando sentence-transformers
        2. Almacena vectores en índice HNSW
        3. Persiste en disco
        
        Args:
            documents: Lista de textos a indexar
            metadata: Metadatos asociados (ej: source, type, date)
            
        Ejemplo:
            await kb.add_documents(
                documents=[
                    "Check-in a las 15:00",
                    "WiFi gratis en habitaciones",
                ],
                metadata={"source": "hotel_info", "type": "faq"}
            )
        """
        if not documents:
            print("⚠️ No hay documentos para añadir")
            return
        
        try:
            # Crear colección si no existe
            if self.collection is None:
                self.collection = self.db.get_or_create_collection(
                    name="hotel_knowledge",
                    metadata={"hnsw:space": "cosine"}  # Métrica de similitud
                )
            
            # Añadir documentos (ChromaDB genera embeddings automáticamente)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.collection.add(
                    documents=documents,
                    ids=[f"doc_{i}" for i in range(len(documents))],
                    metadatas=[metadata] * len(documents)
                )
            )
            
            print(f"✓ {len(documents)} documentos añadidos a ChromaDB")
            
        except Exception as e:
            print(f"✗ Error añadiendo documentos: {e}")
            raise
    
    async def search(self, query: KnowledgeBaseQuery) -> List[KnowledgeBaseResult]:
        """
        Busca documentos relevantes usando búsqueda semántica.
        
        Flujo:
        1. Embedding de la query (automático)
        2. Búsqueda de K-nearest neighbors en el espacio vectorial
        3. Retorna documentos ordenados por similitud
        
        Args:
            query: Query con texto y parámetros
            
        Returns:
            Lista de resultados ordenados por relevancia
            
        Ejemplo:
            results = await kb.search(
                KnowledgeBaseQuery(
                    query_text="¿Cuál es el WiFi?",
                    top_k=3,
                    min_score=0.5
                )
            )
            
            for result in results:
                print(f"Score: {result.score}, Text: {result.content}")
        """
        if not self.is_ready():
            print("⚠️ KB no está lista, retornando lista vacía")
            return []
        
        try:
            loop = asyncio.get_event_loop()
            
            # Búsqueda vectorial
            results = await loop.run_in_executor(
                None,
                lambda: self.collection.query(
                    query_texts=[query.query_text],
                    n_results=query.top_k
                )
            )
            
            kb_results = []
            
            # Procesar resultados
            if results['distances'] and len(results['distances']) > 0:
                distances = results['distances'][0]
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                
                for i, (distance, doc, metadata) in enumerate(
                    zip(distances, documents, metadatas)
                ):
                    # Convertir distancia a score (0-1)
                    # ChromaDB usa distancia coseno: 0 = idéntico, 2 = opuesto
                    score = 1 - (distance / 2)  # Normalizar a 0-1
                    
                    # Filtrar por min_score
                    if score >= query.min_score:
                        kb_results.append(
                            KnowledgeBaseResult(
                                content=doc,
                                score=score,
                                source=metadata.get('source', 'unknown')
                            )
                        )
            
            return kb_results
            
        except Exception as e:
            print(f"✗ Error búsqueda ChromaDB: {e}")
            return []
    
    def reset(self) -> None:
        """
        Resetea la base de datos (elimina colección).
        
        Útil para:
        - Testing
        - Re-indexación completa
        - Limpiar datos obsoletos
        """
        try:
            if self.collection:
                self.db.delete_collection("hotel_knowledge")
                self.collection = None
                print("✓ Colección eliminada")
        except Exception as e:
            print(f"⚠️ Error reseteando ChromaDB: {e}")
    
    def get_stats(self) -> dict:
        """
        Retorna estadísticas de la base de datos.
        
        Returns:
            Diccionario con métricas
        """
        if not self.is_ready():
            return {"status": "not_ready", "count": 0}
        
        try:
            count = self.collection.count()
            return {
                "status": "ready",
                "count": count,
                "collection": "hotel_knowledge",
                "path": self.db_path
            }
        except:
            return {"status": "error", "count": 0}
