"""
PDF 문서 파싱, 청킹, 임베딩 및 ChromaDB 업서트 파이프라인
"""
import os
from pathlib import Path
from typing import List, Dict
import PyPDF2
from chromadb import Client
from openai import OpenAI


class DocumentIngestor:
    def __init__(self, config_path: str = "configs/settings.yaml"):
        self.config = self._load_config(config_path)
        self.chroma_client = None
        self.openai_client = OpenAI()
        
    def _load_config(self, path: str) -> dict:
        """설정 파일 로드"""
        # TODO: YAML 파싱 구현
        pass
    
    def parse_pdf(self, pdf_path: Path) -> str:
        """PDF 파일에서 텍스트 추출"""
        # TODO: PDF 파싱 로직 구현
        pass
    
    def chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[Dict]:
        """텍스트를 청크로 분할"""
        # TODO: 청킹 로직 구현
        pass
    
    def generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """텍스트 청크에 대한 임베딩 생성"""
        # TODO: OpenAI 임베딩 API 호출
        pass
    
    def upsert_to_chroma(self, chunks: List[Dict], embeddings: List[List[float]]):
        """ChromaDB에 청크 및 임베딩 업서트"""
        # TODO: ChromaDB 업서트 로직
        pass
    
    def run(self, pdf_dir: Path):
        """전체 인제스트 파이프라인 실행"""
        pdf_files = list(pdf_dir.glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files")
        
        for pdf_path in pdf_files:
            print(f"Processing {pdf_path.name}...")
            text = self.parse_pdf(pdf_path)
            chunks = self.chunk_text(text, 
                                    self.config.get("chunk_size", 512),
                                    self.config.get("chunk_overlap", 50))
            embeddings = self.generate_embeddings([c["text"] for c in chunks])
            self.upsert_to_chroma(chunks, embeddings)


if __name__ == "__main__":
    ingestor = DocumentIngestor()
    ingestor.run(Path("data/raw/pdf"))
