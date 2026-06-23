"""Common assets shared by all OpenKS knowledge graphs."""

from .interop import compile_module_schema, export_module_schema_to_kag_project, load_module_schema

__all__ = [
    "compile_module_schema",
    "export_module_schema_to_kag_project",
    "load_module_schema",
]
