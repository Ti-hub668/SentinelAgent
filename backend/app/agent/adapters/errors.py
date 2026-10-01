"""Errors raised by governed external tool adapters."""


class ToolAdapterError(RuntimeError):
    """Base error for adapter execution failures."""


class ToolAdapterConfigurationError(
    ToolAdapterError
):
    """Required external integration configuration is missing."""


class ToolAdapterTransportError(
    ToolAdapterError
):
    """External tool transport failed."""


class ToolAdapterResponseError(
    ToolAdapterError
):
    """External tool returned an invalid or unsuccessful response."""