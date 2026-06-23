from openks.common.registry import SUPPORT_MODULES, list_kg_modules


def build_bootstrap_manifest():
    modules = list_kg_modules()
    return {
        "engine": "supxmind-openks",
        "support_modules": SUPPORT_MODULES,
        "kg_modules": [
            {
                "name": item.name,
                "stage": item.stage,
                "owner": item.owner,
                "path": item.path,
                "dependencies": list(item.dependencies),
            }
            for item in modules
        ],
    }
