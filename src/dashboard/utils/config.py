# ============================================================
# src/dashboard/utils/config.py - Dashboard Configuration
# ============================================================

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Dashboard configuration"""

    # API Settings
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    API_TIMEOUT: int = 60

    # Neo4j Settings
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "ur5e_password")

    # UI Settings
    PAGE_TITLE: str = "UR5e RAG Dashboard"
    PAGE_ICON: str = "🤖"
    LAYOUT: str = "wide"

    # Theme Colors
    PRIMARY_COLOR: str = "#2196F3"
    SECONDARY_COLOR: str = "#4CAF50"
    ERROR_COLOR: str = "#F44336"
    WARNING_COLOR: str = "#FF9800"

    # Node Colors (Neo4j style)
    NODE_COLORS: dict = None
    EDGE_COLORS: dict = None

    def __post_init__(self):
        self.NODE_COLORS = {
            "ErrorCode": "#F44336",      # Red
            "Component": "#2196F3",      # Blue
            "Solution": "#4CAF50",       # Green
            "Symptom": "#FF9800",        # Orange
            "Document": "#9C27B0",       # Purple
            "Other": "#9E9E9E",          # Gray
        }

        self.EDGE_COLORS = {
            "CAUSED_BY": "#E91E63",
            "RESOLVED_BY": "#4CAF50",
            "RELATED_TO": "#9E9E9E",
            "HAS_SYMPTOM": "#FF9800",
            "BELONGS_TO": "#2196F3",
            "MENTIONED_IN": "#9C27B0",
        }


# Global config instance
config = Config()
