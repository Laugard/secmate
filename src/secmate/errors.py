"""Domain exceptions safe to translate into user-facing messages."""


class SecMateError(Exception):
    """Base class for expected application failures."""


class ConfigurationError(SecMateError):
    """Configuration is missing or unsafe."""


class OllamaUnavailable(SecMateError):
    """The local Ollama service is unavailable."""


class ModelResponseError(SecMateError):
    """A local model returned unusable output."""


class ValidationError(SecMateError):
    """User or source input failed validation."""


class NoEvidenceError(SecMateError):
    """No document evidence passed the retrieval threshold."""
