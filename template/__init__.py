"""Template extract and validation."""
from .render import render_template_extract_html
from .validation import validate_ca1, ValidationResult

__all__ = ["render_template_extract_html", "validate_ca1", "ValidationResult"]
