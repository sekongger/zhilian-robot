"""OpenSPG/KAG 产业头条演示模块。"""

from .builder_templates import get_robot_chain_mvp_builder_template
from .headlines_service import build_headlines_from_news
from .schema_templates import get_my_news_demo_schema_script, get_robot_chain_mvp_schema_template

__all__ = [
    "build_headlines_from_news",
    "get_robot_chain_mvp_schema_template",
    "get_my_news_demo_schema_script",
    "get_robot_chain_mvp_builder_template",
]
