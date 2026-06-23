from openks.entry.bootstrap import build_bootstrap_manifest


def build_cli_snapshot():
    manifest = build_bootstrap_manifest()
    return [
        f"{item['stage']}: {item['name']} ({item['owner']})"
        for item in manifest["kg_modules"]
    ]


if __name__ == "__main__":
    for line in build_cli_snapshot():
        print(line)
