# ============================================================
# src/dashboard/utils/formatters.py - Formatting Utilities
# ============================================================


def format_latency(ms: float) -> str:
    """Format latency in milliseconds to human readable string"""
    if ms < 1000:
        return f"{ms:.0f}ms"
    else:
        return f"{ms/1000:.2f}s"


def format_cost(cost: float) -> str:
    """Format cost in dollars"""
    if cost < 0.01:
        return f"${cost:.4f}"
    elif cost < 1:
        return f"${cost:.3f}"
    else:
        return f"${cost:.2f}"


def format_tokens(tokens: int) -> str:
    """Format token count"""
    if tokens < 1000:
        return str(tokens)
    elif tokens < 1000000:
        return f"{tokens/1000:.1f}K"
    else:
        return f"{tokens/1000000:.2f}M"


def format_score(score: float) -> str:
    """Format relevance score as percentage"""
    return f"{score * 100:.1f}%"


def format_confidence(confidence: float) -> tuple:
    """Format confidence with icon and color"""
    if confidence >= 0.7:
        return "🟢", "green", f"{confidence * 100:.0f}%"
    elif confidence >= 0.4:
        return "🟡", "orange", f"{confidence * 100:.0f}%"
    else:
        return "🔴", "red", f"{confidence * 100:.0f}%"


def get_verification_badge(status: str) -> tuple:
    """Get badge icon and color for verification status"""
    badges = {
        "verified": ("✅", "green", "Verified"),
        "partial": ("⚠️", "orange", "Partial"),
        "unverified": ("❌", "red", "Unverified"),
        "insufficient": ("❓", "gray", "Insufficient"),
    }
    return badges.get(status, ("❓", "gray", status))


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
