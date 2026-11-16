"""Provider adapters. Importing this package registers the built-in ones."""

from .anthropic_adapter import wrap_anthropic
from .base import patch_method, register_adapter, wrap
from .mcp_adapter import wrap_mcp
from .openai_adapter import wrap_openai

__all__ = [
    "patch_method",
    "register_adapter",
    "wrap",
    "wrap_anthropic",
    "wrap_mcp",
    "wrap_openai",
]
