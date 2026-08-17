"""Configurazione tipizzata, caricata senza aprire connessioni a Oracle."""

from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    NestedSecretsSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class OracleCredentials(BaseModel):
    """Credenziali utente/password, oscurate nelle rappresentazioni normali."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user: SecretStr = Field(min_length=1)
    password: SecretStr = Field(min_length=1)


class OracleSettings(BaseModel):
    """Parametri di connessione al database Oracle ARPAS."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    host: str = "localhost"
    port: int = Field(default=1521, gt=0, le=65535)
    service_name: str = "orcl"
    credentials: OracleCredentials | None = None

    @property
    def dsn(self) -> str:
        """Connect descriptor per python-oracledb in thin mode (no Instant Client)."""

        return f"{self.host}:{self.port}/{self.service_name}"


class AppSettings(BaseSettings):
    """Configurazione completa e immutabile di un processo."""

    model_config = SettingsConfigDict(
        env_prefix="FDP_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir=(".secrets", "/run/secrets"),
        extra="ignore",
        frozen=True,
    )

    oracle: OracleSettings = Field(default_factory=OracleSettings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Supporta secret Docker annidati come FDP_ORACLE__CREDENTIALS__USER."""

        del settings_cls
        nested_secrets = NestedSecretsSettingsSource(
            file_secret_settings,
            secrets_dir=file_secret_settings.secrets_dir,
            secrets_dir_missing="ok",
            secrets_case_sensitive=False,
            secrets_prefix="FDP_",
            secrets_nested_delimiter="__",
        )
        return init_settings, env_settings, dotenv_settings, nested_secrets


@lru_cache
def get_settings() -> AppSettings:
    """Carica la configurazione una sola volta per processo."""

    return AppSettings()
