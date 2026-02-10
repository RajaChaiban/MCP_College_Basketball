"""Custom exception hierarchy for the CBB MCP server."""


class CBBError(Exception):
    """Base exception for all CBB MCP errors."""


class SourceError(CBBError):
    """Error from a data source (API down, bad response, etc.)."""

    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"[{source}] {message}")


class SourceTimeoutError(SourceError):
    """A data source request timed out."""


class SourceRateLimitError(SourceError):
    """Rate limit exceeded for a data source."""


class AllSourcesFailedError(CBBError):
    """All sources in the fallback chain failed."""

    def __init__(self, capability: str, errors: list[SourceError]):
        self.errors = errors
        sources = ", ".join(e.source for e in errors)
        super().__init__(
            f"All sources failed for {capability}. Tried: {sources}"
        )


class TeamNotFoundError(CBBError):
    """Team could not be found by name or ID."""

    def __init__(self, query: str):
        super().__init__(f"Team not found: {query}")


class GameNotFoundError(CBBError):
    """Game could not be found by ID."""

    def __init__(self, game_id: str):
        super().__init__(f"Game not found: {game_id}")


class ValidationError(CBBError):
    """Input validation failed."""
