from asyncio import current_task
from enum import Enum
from functools import cached_property, lru_cache
from gettext import gettext
from pathlib import Path
from typing import Union, cast
from urllib.parse import ParseResult, urlencode, urlparse

from pydantic import Field, ValidationInfo, field_validator, model_validator
from qd_core.config import DEFAULT_CONFIG_DIR, QDBaseSettings, QDCoreSettings, export_settings_to_json
from qd_core.utils.log import Log
from sqlalchemy.ext.asyncio import async_scoped_session, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession


class DBType(Enum):
    """
    Database type enum.
    """

    mysql = "mysql"
    sqlite3 = "sqlite3"


class Sqlite3Settings(QDBaseSettings):
    """
    SQLite3 settings class.
    """

    db_path: Path = Field(
        default_factory=lambda: DEFAULT_CONFIG_DIR.joinpath("database.db"), description=gettext("SQLite3 path")
    )
    db_schema: str = Field(default="sqlite", frozen=True, description=gettext("SQL schema"))
    driver: str = Field(default="aiosqlite", description=gettext("SQLite3 driver"))

    @property
    def engine_url(self) -> str:
        """
        Construct the full engine URL based on individual components.
        """
        return f"{self.db_schema}+{self.driver}:///{self.db_path}"


class MysqlSettings(QDBaseSettings):
    """
    MySQL settings class.
    """

    url: ParseResult = Field(
        default_factory=lambda: urlparse(""),
        alias="jawsdb_maria_url",
        description=gettext("MySQL url, e.g. mysql://user:passwd@host:port/database?auth_plugin=mysql_native_password"),
    )
    db_schema: str = Field(default="mysql", frozen=True, description=gettext("SQL schema"))
    driver: str = Field(default="aiomysql", description=gettext("MySQL driver"))
    hostname: str = Field(default="localhost", description=gettext("MySQL host"))
    port: int = Field(default=3306, description=gettext("MySQL port"))
    database: str = Field(default="qd", description=gettext("MySQL database"))
    username: str = Field(default="qd", description=gettext("MySQL user"))
    password: str = Field(default="", description=gettext("MySQL password"))
    auth_plugin: str = Field(
        default="mysql_native_password",
        description=gettext(
            "MySQL auth plugin, default is empty, "
            "allow values: mysql_native_password, mysql_clear_password, sha256_password, caching_sha2_password"
        ),
    )
    is_async_driver: bool = Field(default=True, description=gettext("whether the driver is async"))

    @model_validator(mode="after")
    def update_fields_from_url(self) -> "MysqlSettings":
        """
        Update other fields based on the 'url' value.
        """
        if self.url:
            parsed_url = self.url
            self.db_schema = parsed_url.scheme or self.db_schema
            self.hostname = parsed_url.hostname or self.hostname
            self.port = parsed_url.port or self.port
            self.database = (
                parsed_url.path[1:] if parsed_url.path and len(parsed_url.path) > 1 else ""
            ) or self.database
            self.username = parsed_url.username or self.username
            self.password = parsed_url.password or self.password
            self.auth_plugin = parsed_url.query or self.auth_plugin
        return self

    @property
    def engine_url(self) -> str:
        """
        Construct the full engine URL based on individual components.
        """
        query_params = {}
        if self.auth_plugin:
            query_params["auth_plugin"] = self.auth_plugin

        query_string = f"?{urlencode(query_params)}" if query_params else ""
        password_part = f":{self.password}" if self.password else ""
        return (
            f"{self.db_schema}+{self.driver}://{self.username}{password_part}@{self.hostname}:{self.port}/"
            f"{self.database}{query_string}"
        )


class DBPoolSettings(QDBaseSettings):
    """
    SQLAlchemy pool settings class.
    """

    logging_name: str = Field(
        default="QD.sql.pool", alias="qd_sql_pool_logging_name", description=gettext("SQLAlchemy pool logging name")
    )
    logging_level: str = Field(
        default="WARNING", alias="qd_sql_pool_logging_level", description=gettext("SQLAlchemy pool logging level")
    )
    size: int = Field(default=10, alias="qd_sql_pool_size", description=gettext("SQLAlchemy pool size"))
    pre_ping: bool = Field(
        default=True,
        alias="qd_sql_pool_pre_ping",
        description=gettext(
            "SQLAlchemy pool pre ping, i.e. check the connection by pinging before using it. Default is True"
        ),
    )
    recycle: int = Field(
        default=3600,
        alias="qd_sql_pool_recycle",
        description=gettext(
            "SQLAlchemy pool recycle, i.e. the number of seconds before the connection is recycled. "
            "Default is 3600 seconds"
        ),
    )
    timeout: int = Field(
        default=60,
        alias="qd_sql_pool_timeout",
        description=gettext(
            "SQLAlchemy pool timeout, "
            "i.e. the number of seconds to wait before giving up on getting a connection from the pool. "
            "Default is 60 seconds"
        ),
    )
    use_lifo: bool = Field(
        default=True,
        alias="qd_sql_pool_use_lifo",
        description=gettext("SQLAlchemy pool use lifo, i.e. use LIFO ordering. Default is True"),
    )


class DBSettings(QDBaseSettings):
    """
    Database settings class.
    """

    db_type: DBType = Field(default=DBType.sqlite3, description=gettext("Database type"))
    engine_settings: Union[MysqlSettings, Sqlite3Settings] = Field(
        default_factory=Sqlite3Settings, description=gettext("SQLAlchemy engine settings")
    )
    logging_name: str = Field(
        default="QD.SQL", alias="qd_sql_logging_name", description=gettext("SQLAlchemy logging name")
    )
    logging_level: str = Field(
        default="WARNING", alias="qd_sql_logging_level", description=gettext("SQLAlchemy logging level")
    )
    max_overflow: int = Field(
        default=50,
        alias="qd_sql_max_overflow",
        description=gettext(
            "SQLAlchemy max overflow, i.e. the maximum number of connections that can be created. Default is 50"
        ),
    )
    pool: DBPoolSettings = Field(default_factory=DBPoolSettings, description=gettext("SQLAlchemy pool settings"))

    @field_validator("engine_settings", mode="after")
    @classmethod
    def validate_and_bind_engine_settings(cls, value: Union[MysqlSettings, Sqlite3Settings], info: ValidationInfo):
        """
        Validate and bind the 'engine_settings' value.
        """
        db_type = info.data.get("db_type")
        if db_type == DBType.sqlite3 and not isinstance(value, Sqlite3Settings):
            raise ValueError(gettext("SQLite3 settings must be provided for SQLite3 database type"))
        elif db_type == DBType.mysql and not isinstance(value, MysqlSettings):
            raise ValueError(gettext("MySQL settings must be provided for MySQL database type"))
        return value

    @property
    def mysql_settings(self) -> MysqlSettings:
        if self.db_type != DBType.mysql:
            raise ValueError(f"Database type is not {DBType.mysql.value}")
        return cast(MysqlSettings, self.engine_settings)

    @property
    def sqlite3_settings(self) -> Sqlite3Settings:
        if self.db_type != DBType.sqlite3:
            raise ValueError(f"Database type is not {DBType.sqlite3.value}")
        return cast(Sqlite3Settings, self.engine_settings)

    @cached_property
    def engine(self):
        if self.db_type == DBType.sqlite3:
            engine = create_async_engine(
                self.sqlite3_settings.engine_url,
                logging_name=self.logging_name,
                # pool_size=self.pool.size,
                # max_overflow=self.max_overflow,
                pool_logging_name=self.pool.logging_name,
                pool_pre_ping=self.pool.pre_ping,
                pool_recycle=self.pool.recycle,
                # pool_timeout=self.pool.timeout,
                # pool_use_lifo=self.pool.use_lifo,
            )
        elif self.db_type == DBType.mysql:
            engine = create_async_engine(
                self.mysql_settings.engine_url,
                logging_name=self.logging_name,
                pool_size=self.pool.size,
                max_overflow=self.max_overflow,
                pool_logging_name=self.pool.logging_name,
                pool_pre_ping=self.pool.pre_ping,
                pool_recycle=self.pool.recycle,
                pool_timeout=self.pool.timeout,
                pool_use_lifo=self.pool.use_lifo,
            )
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
        engine_logger = Log(
            f"sqlalchemy.engine.Engine.{self.logging_name}",
            logger_level=self.logging_level,
            channel_level=self.logging_level,
        ).getlogger()
        engine_logger.info(f"Created engine: {engine}")
        if hasattr(engine.pool.logger, "logger"):
            pool_logger = Log(
                engine.pool.logger.logger,
                logger_level=self.pool.logging_level,
                channel_level=self.pool.logging_level,
            ).getlogger()
        else:
            pool_logger = Log(
                engine.pool.logger,
                logger_level=self.pool.logging_level,
                channel_level=self.pool.logging_level,
            ).getlogger()
        pool_logger.info(f"Created pool: {engine.pool}")
        return engine

    @cached_property
    def scoped_session(self):
        return async_scoped_session(
            async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False), scopefunc=current_task
        )


class QDServerSettings(QDCoreSettings):
    """
    QD Server settings class.
    """

    db: DBSettings = Field(default_factory=DBSettings, description=gettext("Database settings"))


@lru_cache
def get_settings() -> QDServerSettings:
    """
    Get the QD Server settings.
    """
    return QDServerSettings()


if __name__ == "__main__":
    settings = get_settings()
    print(id(settings))
    print(id(settings.db.engine))
    print(id(settings.db.engine))
    get_settings.cache_clear()
    settings = get_settings()
    print(id(settings))
    print(id(settings.db.engine))
    print(id(settings.db.engine))
    export_settings_to_json(settings=settings)
