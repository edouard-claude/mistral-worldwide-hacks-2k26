"""Custom exceptions for Game of Claw."""


class GameError(Exception):
    """Base exception for game errors."""


class LLMError(GameError):
    """Error communicating with LLM provider."""


class ClientError(GameError):
    """Error from an external service client."""


class RoutingError(ClientError):
    """OSRM routing failure."""


class StorageError(ClientError):
    """DuckDB or Qdrant storage failure."""
