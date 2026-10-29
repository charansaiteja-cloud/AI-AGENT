from __future__ import annotations

from pathlib import Path

from backend.app.config import Settings


def test_defaults_are_development_safe() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "Support AI"
    assert settings.environment == "development"
    assert settings.is_production is False
    assert settings.api_auth_enabled is False


def test_paths_are_expanded(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        upload_dir="~/support-uploads",
        static_dir="~/support-static",
    )

    assert settings.upload_dir == Path("~/support-uploads").expanduser()
    assert settings.static_dir == Path("~/support-static").expanduser()


def test_cors_and_extension_lists_are_trimmed() -> None:
    settings = Settings(
        _env_file=None,
        cors_origins="http://localhost:5173, https://support.example.com ,",
        allowed_upload_extensions=".PNG, .txt ,",
    )

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "https://support.example.com",
    ]
    assert settings.allowed_extensions == {".png", ".txt"}


def test_blank_api_key_disables_auth() -> None:
    settings = Settings(_env_file=None, app_api_key="   ")

    assert settings.app_api_key is None
    assert settings.api_auth_enabled is False


def test_api_key_enables_auth() -> None:
    settings = Settings(_env_file=None, app_api_key=" secret ")

    assert settings.app_api_key == "secret"
    assert settings.api_auth_enabled is True


def test_production_flag() -> None:
    assert Settings(_env_file=None, environment="production").is_production is True
