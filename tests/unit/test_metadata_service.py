# ============================================================
# tests/unit/test_metadata_service.py - MetadataService 단위 테스트
# ============================================================
# pytest -v tests/unit/test_metadata_service.py
# ============================================================

import os
import sys
import pytest

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.api.services.metadata_service import MetadataService, DocumentInfo, ChunkMapping


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def metadata_service():
    """테스트용 MetadataService"""
    service = MetadataService()
    service.load()
    return service


# ============================================================
# [1] sources.yaml 로드 테스트
# ============================================================

class TestSourcesYaml:
    """sources.yaml 관련 테스트"""

    def test_load_sources(self, metadata_service):
        """sources.yaml 로드 성공"""
        docs = metadata_service.get_all_documents()
        assert len(docs) == 3

    def test_get_document_error_codes(self, metadata_service):
        """error_codes 문서 정보 조회"""
        doc = metadata_service.get_document("error_codes")
        assert doc is not None
        assert doc.title == "Error Codes Directory"
        assert doc.version == "5.12"
        assert doc.pages == 167

    def test_get_document_service_manual(self, metadata_service):
        """service_manual 문서 정보 조회"""
        doc = metadata_service.get_document("service_manual")
        assert doc is not None
        assert "Service Manual" in doc.title
        assert doc.pages == 123

    def test_get_document_user_manual(self, metadata_service):
        """user_manual 문서 정보 조회"""
        doc = metadata_service.get_document("user_manual")
        assert doc is not None
        assert "User Manual" in doc.title
        assert doc.pages == 249

    def test_document_not_found(self, metadata_service):
        """존재하지 않는 문서"""
        doc = metadata_service.get_document("nonexistent")
        assert doc is None

    def test_document_has_sections(self, metadata_service):
        """문서 섹션 정보 확인"""
        doc = metadata_service.get_document("error_codes")
        assert doc.sections is not None
        assert len(doc.sections) >= 1


# ============================================================
# [2] chunk_manifest.jsonl 로드 테스트
# ============================================================

class TestChunkManifest:
    """chunk_manifest.jsonl 관련 테스트"""

    def test_load_manifest(self, metadata_service):
        """manifest 로드 성공"""
        # 최소 100개 이상의 청크가 있어야 함
        stats = metadata_service.get_stats()
        assert stats["total_chunks"] >= 100

    def test_get_chunk_mapping(self, metadata_service):
        """청크 매핑 조회"""
        mapping = metadata_service.get_chunk_mapping("error_codes_C4_004")
        assert mapping is not None
        assert mapping.doc_id == "error_codes"

    def test_chunk_mapping_has_page(self, metadata_service):
        """청크에 페이지 정보 있음"""
        mapping = metadata_service.get_chunk_mapping("error_codes_C4_004")
        assert mapping.page > 0

    def test_chunk_mapping_has_section(self, metadata_service):
        """청크에 섹션 정보 있음"""
        mapping = metadata_service.get_chunk_mapping("error_codes_C4_004")
        assert mapping.section != ""

    def test_chunk_not_found(self, metadata_service):
        """존재하지 않는 청크"""
        mapping = metadata_service.get_chunk_mapping("nonexistent_chunk")
        assert mapping is None


# ============================================================
# [3] Citation 생성 테스트
# ============================================================

class TestCitation:
    """Citation 생성 테스트"""

    def test_get_citation_error_codes(self, metadata_service):
        """error_codes 청크 citation"""
        citation = metadata_service.get_citation("error_codes_C4_004")
        assert citation is not None
        assert "doc_title" in citation
        assert "page" in citation
        assert "citation" in citation

    def test_citation_format(self, metadata_service):
        """citation 문자열 형식"""
        citation = metadata_service.get_citation("error_codes_C4_004")
        # "Error Codes Directory v5.12, p.12, ..." 형식
        assert "v5.12" in citation["citation"]
        assert "p." in citation["citation"]

    def test_citation_includes_doc_title(self, metadata_service):
        """citation에 문서 제목 포함"""
        citation = metadata_service.get_citation("error_codes_C4_004")
        assert "Error Codes" in citation["citation"]

    def test_citation_includes_page(self, metadata_service):
        """citation에 페이지 번호 포함"""
        citation = metadata_service.get_citation("error_codes_C4_004")
        assert citation["page"] > 0

    def test_citation_not_found(self, metadata_service):
        """존재하지 않는 청크 citation"""
        citation = metadata_service.get_citation("nonexistent_chunk")
        assert citation is None

    def test_citation_service_manual(self, metadata_service):
        """service_manual 청크 citation"""
        citation = metadata_service.get_citation("service_manual_000")
        assert citation is not None
        assert "Service Manual" in citation["citation"]

    def test_citation_user_manual(self, metadata_service):
        """user_manual 청크 citation"""
        citation = metadata_service.get_citation("user_manual_000")
        assert citation is not None
        assert "User Manual" in citation["citation"]


# ============================================================
# [4] 문서별 청크 조회 테스트
# ============================================================

class TestChunksByDocument:
    """문서별 청크 조회 테스트"""

    def test_get_chunks_by_doc_error_codes(self, metadata_service):
        """error_codes 문서의 청크 조회"""
        chunks = metadata_service.get_chunks_by_doc("error_codes")
        assert len(chunks) == 99

    def test_get_chunks_by_doc_service_manual(self, metadata_service):
        """service_manual 문서의 청크 조회"""
        chunks = metadata_service.get_chunks_by_doc("service_manual")
        assert len(chunks) == 197

    def test_get_chunks_by_doc_user_manual(self, metadata_service):
        """user_manual 문서의 청크 조회"""
        chunks = metadata_service.get_chunks_by_doc("user_manual")
        assert len(chunks) == 426

    def test_get_chunks_by_doc_nonexistent(self, metadata_service):
        """존재하지 않는 문서의 청크 조회"""
        chunks = metadata_service.get_chunks_by_doc("nonexistent")
        assert len(chunks) == 0


# ============================================================
# [5] 통계 테스트
# ============================================================

class TestStats:
    """통계 정보 테스트"""

    def test_get_stats(self, metadata_service):
        """통계 정보 조회"""
        stats = metadata_service.get_stats()
        assert "total_documents" in stats
        assert "total_chunks" in stats
        assert "documents" in stats

    def test_stats_total_documents(self, metadata_service):
        """총 문서 수"""
        stats = metadata_service.get_stats()
        assert stats["total_documents"] == 3

    def test_stats_total_chunks(self, metadata_service):
        """총 청크 수"""
        stats = metadata_service.get_stats()
        assert stats["total_chunks"] == 722


# ============================================================
# [6] 데이터 클래스 테스트
# ============================================================

class TestDataClasses:
    """데이터 클래스 테스트"""

    def test_document_info_to_dict(self):
        """DocumentInfo.to_dict()"""
        doc = DocumentInfo(
            doc_id="test",
            title="Test Document",
            version="1.0",
            date="2024-01",
            pages=100,
            source_file="test.pdf",
            chunk_count=50
        )
        d = doc.to_dict()
        assert d["doc_id"] == "test"
        assert d["title"] == "Test Document"

    def test_chunk_mapping_to_dict(self):
        """ChunkMapping.to_dict()"""
        mapping = ChunkMapping(
            chunk_id="test_001",
            doc_id="test",
            page=10,
            section="Test Section",
            doc_type="test"
        )
        d = mapping.to_dict()
        assert d["chunk_id"] == "test_001"
        assert d["page"] == 10


# ============================================================
# 메인 실행
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
