from config.settings import Settings


def test_settings_ignores_extra_env_file(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "TZ=Asia/Shanghai\n"
        "MONGO_INITDB_ROOT_USERNAME=admin\n"
        "MONGO_INITDB_ROOT_PASSWORD=password123\n"
        "BACKEND_PORT=8000\n"
    )
    Settings(_env_file=str(env_path))
