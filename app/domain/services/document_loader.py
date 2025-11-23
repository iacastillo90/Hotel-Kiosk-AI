import os
from typing import List
import logging

# Intentamos importar las librerías (manejo de errores si faltan)
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

try:
    import pandas as pd
except ImportError:
    pd = None

logger = logging.getLogger(__name__)

class DocumentLoader:
    """
    Lee archivos de una carpeta y extrae su texto.
    Soporta: .txt, .pdf, .docx, .xlsx
    """
    
    def __init__(self, folder_path: str):
        self.folder_path = folder_path

    def load_documents(self) -> List[str]:
        """Recorre la carpeta y devuelve una lista de textos (chunks)"""
        documents = []
        
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
            logger.warning(f"📂 Carpeta creada: {self.folder_path}. Pon tus archivos ahí.")
            return []

        print(f"📂 Escaneando documentos en: {self.folder_path}")

        for filename in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, filename)
            text = ""
            
            try:
                if filename.endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                        
                elif filename.endswith(".pdf"):
                    if PdfReader:
                        reader = PdfReader(file_path)
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                    else:
                        logger.warning("⚠️ pypdf no instalado")

                elif filename.endswith(".docx"):
                    if docx:
                        doc = docx.Document(file_path)
                        text = "\n".join([para.text for para in doc.paragraphs])
                    else:
                        logger.warning("⚠️ python-docx no instalado")

                elif filename.endswith(".xlsx") or filename.endswith(".xls"):
                    if pd:
                        df = pd.read_excel(file_path)
                        # Convertir todas las filas a texto
                        text = df.to_string(index=False)
                    else:
                        logger.warning("⚠️ pandas no instalado")

                # Si extrajimos texto, lo guardamos
                if text.strip():
                    # ⚡ TRUCO PRO: Dividir texto largo en trozos (Chunks)
                    # Si el texto es muy largo, Gemini se confunde. Lo partimos.
                    chunks = self._chunk_text(text, chunk_size=1000)
                    documents.extend(chunks)
                    print(f"  ✓ Leído: {filename} ({len(chunks)} fragmentos)")
                else:
                    print(f"  ⚠️ Archivo vacío o ilegible: {filename}")

            except Exception as e:
                print(f"  ✗ Error leyendo {filename}: {e}")

        return documents

    def _chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Divide un texto largo en trozos más pequeños para la IA"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1
            
            if current_length >= chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks
