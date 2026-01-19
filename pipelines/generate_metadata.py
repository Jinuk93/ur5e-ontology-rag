"""
sources.yaml 및 chunk_manifest.jsonl 메타데이터 생성 파이프라인
"""
import json
from pathlib import Path
from datetime import datetime
import yaml


class MetadataGenerator:
    def __init__(self, raw_dir: Path, output_dir: Path):
        self.raw_dir = raw_dir
        self.output_dir = output_dir
        
    def generate_sources_yaml(self):
        """sources.yaml 생성"""
        sources = []
        pdf_files = list(self.raw_dir.glob("*.pdf"))
        
        for idx, pdf_path in enumerate(pdf_files):
            source = {
                "id": f"source_{idx:03d}",
                "filename": pdf_path.name,
                "path": str(pdf_path),
                "type": "pdf",
                "indexed_at": datetime.now().isoformat()
            }
            sources.append(source)
        
        output_path = self.output_dir / "sources.yaml"
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump({"sources": sources}, f, allow_unicode=True)
        
        print(f"Generated {output_path}")
        
    def generate_chunk_manifest(self):
        """chunk_manifest.jsonl 생성"""
        # TODO: 실제 청크 정보를 기반으로 매니페스트 생성
        output_path = self.output_dir / "chunk_manifest.jsonl"
        
        # 샘플 데이터
        sample_chunks = [
            {
                "chunk_id": "chunk_001",
                "source_id": "source_000",
                "page_num": 1,
                "start_char": 0,
                "end_char": 512,
                "text_preview": "Sample chunk text...",
                "created_at": datetime.now().isoformat()
            }
        ]
        
        with open(output_path, "w", encoding="utf-8") as f:
            for chunk in sample_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        
        print(f"Generated {output_path}")
    
    def run(self):
        """메타데이터 생성 실행"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generate_sources_yaml()
        self.generate_chunk_manifest()


if __name__ == "__main__":
    generator = MetadataGenerator(
        raw_dir=Path("data/raw/pdf"),
        output_dir=Path("data/processed/metadata")
    )
    generator.run()
