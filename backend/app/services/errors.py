class ServiceError(Exception):
    """Base class for errors raised by external service adapters."""


class OllamaError(ServiceError):
    """Raised when the local model runtime cannot produce a response."""


class HindsightError(ServiceError):
    """Raised when the long-term memory service cannot be reached."""
