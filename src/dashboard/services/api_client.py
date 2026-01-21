# ============================================================
# src/dashboard/services/api_client.py - API Client for FastAPI Backend
# ============================================================

import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time
import os
import sys

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.dashboard.utils.config import config


@dataclass
class QueryResult:
    """RAG Query result"""
    answer: str
    verification: Dict[str, Any]
    sources: List[Dict[str, Any]]
    query_analysis: Dict[str, Any]
    latency_ms: float
    success: bool
    error: Optional[str] = None


@dataclass
class SearchResult:
    """Search result"""
    results: List[Dict[str, Any]]
    query_analysis: Dict[str, Any]
    total_count: int
    latency_ms: float
    success: bool
    error: Optional[str] = None


class APIClient:
    """
    API Client for communicating with the RAG API server
    """

    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.API_BASE_URL
        self.timeout = config.API_TIMEOUT

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, params=params, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return {"success": True, "data": response.json()}

        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Cannot connect to API server"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timed out"}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "error": f"HTTP error: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Check API server health"""
        result = self._make_request("GET", "/health")
        if result["success"]:
            return result["data"]
        return {
            "status": "error",
            "version": "unknown",
            "components": {},
            "error": result.get("error"),
        }

    def query(
        self,
        question: str,
        top_k: int = 5,
        include_sources: bool = True,
        include_citation: bool = True,
    ) -> QueryResult:
        """
        Execute RAG query

        Args:
            question: User question
            top_k: Number of results to retrieve
            include_sources: Whether to include source info
            include_citation: Whether to include citation

        Returns:
            QueryResult with answer, verification, sources
        """
        result = self._make_request(
            "POST",
            "/api/v1/query",
            data={
                "question": question,
                "top_k": top_k,
                "include_sources": include_sources,
                "include_citation": include_citation,
            },
        )

        if result["success"]:
            data = result["data"]
            return QueryResult(
                answer=data.get("answer", ""),
                verification=data.get("verification", {}),
                sources=data.get("sources", []),
                query_analysis=data.get("query_analysis", {}),
                latency_ms=data.get("latency_ms", 0),
                success=True,
            )
        else:
            return QueryResult(
                answer="",
                verification={},
                sources=[],
                query_analysis={},
                latency_ms=0,
                success=False,
                error=result.get("error"),
            )

    def analyze(self, question: str) -> Dict[str, Any]:
        """
        Analyze question without generating answer

        Returns:
            Analysis result with error_codes, components, query_type, search_strategy
        """
        result = self._make_request(
            "POST",
            "/api/v1/analyze",
            data={"question": question},
        )

        if result["success"]:
            return result["data"]
        return {
            "original_query": question,
            "error_codes": [],
            "components": [],
            "query_type": "unknown",
            "search_strategy": "unknown",
            "error": result.get("error"),
        }

    def search(
        self,
        question: str,
        top_k: int = 5,
        strategy: str = None,
    ) -> SearchResult:
        """
        Search without LLM generation

        Args:
            question: Search query
            top_k: Number of results
            strategy: Search strategy (graph_first, vector_first, hybrid)

        Returns:
            SearchResult with results and analysis
        """
        data = {"question": question, "top_k": top_k}
        if strategy:
            data["strategy"] = strategy

        result = self._make_request("POST", "/api/v1/search", data=data)

        if result["success"]:
            data = result["data"]
            return SearchResult(
                results=data.get("results", []),
                query_analysis=data.get("query_analysis", {}),
                total_count=data.get("total_count", 0),
                latency_ms=data.get("latency_ms", 0),
                success=True,
            )
        else:
            return SearchResult(
                results=[],
                query_analysis={},
                total_count=0,
                latency_ms=0,
                success=False,
                error=result.get("error"),
            )

    def get_errors(self) -> List[str]:
        """Get list of all error codes"""
        result = self._make_request("GET", "/api/v1/errors")
        if result["success"]:
            return result["data"]
        return []

    def get_error_info(self, code: str) -> Dict[str, Any]:
        """Get specific error code info"""
        result = self._make_request("GET", f"/api/v1/errors/{code}")
        if result["success"]:
            return result["data"]
        return {"code": code, "error": result.get("error")}

    def get_components(self) -> List[str]:
        """Get list of all components"""
        result = self._make_request("GET", "/api/v1/components")
        if result["success"]:
            return result["data"]
        return []

    def get_component_info(self, name: str) -> Dict[str, Any]:
        """Get specific component info"""
        result = self._make_request("GET", f"/api/v1/components/{name}")
        if result["success"]:
            return result["data"]
        return {"name": name, "error": result.get("error")}

    def compare_strategies(
        self,
        question: str,
        top_k: int = 5,
    ) -> Dict[str, SearchResult]:
        """
        Compare all search strategies for the same question

        Returns:
            Dict with strategy names as keys and SearchResult as values
        """
        strategies = ["graph_first", "vector_first", "hybrid"]
        results = {}

        for strategy in strategies:
            results[strategy] = self.search(question, top_k, strategy)

        return results


# Global client instance
api_client = APIClient()
