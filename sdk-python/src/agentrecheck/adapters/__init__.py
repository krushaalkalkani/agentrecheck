"""Provider adapters. Importing this package registers the built-in ones."""

from .anthropic_adapter import wrap_anthropic
from .base import patch_method, register_adapter, wrap
from .openai_adapter import wrap_openai

__all__ = ["patch_method", "register_adapter", "wrap", "wrap_anthropic", "wrap_openai"]
