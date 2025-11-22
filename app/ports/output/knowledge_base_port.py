from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class KnowledgeBaseQuery:
    """Query para la base de conocimiento"""
    query_text: str
    top_k: int = 3
    min_score: float = 0.5


@dataclass
class KnowledgeBaseResult:
    """Resultado de búsqueda en la base de conocimiento"""
    content: str
    score: float  # 0.0 - 1.0 (similaridad)
    source: str


class KnowledgeBasePort(ABC):
    """
    Contrato para la base de conocimiento vectorial (ChromaDB, Pinecone).
    Define comportamiento RAG sin acoplar tecnología.
    """
    
    @abstractmethod
    async def search(self, query: KnowledgeBaseQuery) -> List[KnowledgeBaseResult]:
        """
        Busca información relevante en la base de conocimiento.
        
        Args:
            query: Query con texto y parámetros de búsqueda
            
        Returns:
            Lista de resultados ordenados por relevancia
        """
        pass
    
    @abstractmethod
    async def add_documents(self, documents: List[str], metadata: dict) -> None:
        """
        Añade documentos a la base de conocimiento.
        
        Args:
            documents: Lista de textos a indexar
            metadata: Metadatos asociados a los documentos
        """
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """
        Verifica si la KB está lista para usar.
        
        Returns:
            True si está inicializada y lista
        """
        pass
