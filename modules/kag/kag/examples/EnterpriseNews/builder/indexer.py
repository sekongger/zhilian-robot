import os
import logging

from kag.common.registry import import_modules_from_path
from kag.builder.runner import BuilderChainRunner

logger = logging.getLogger(__name__)


def build_kb(file_path: str):
    from kag.common.conf import KAG_CONFIG

    runner = BuilderChainRunner.from_config(KAG_CONFIG.all_config["kag_builder_pipeline"])
    runner.invoke(file_path)
    logger.info("buildKB successfully for %s", file_path)


if __name__ == "__main__":
    import_modules_from_path(".")
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "data", "new1.md")
    build_kb(file_path)
