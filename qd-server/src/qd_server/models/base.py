import contextlib
from typing import AsyncIterator, Optional

from qd_core.utils.log import Log
from sqlmodel.ext.asyncio.session import AsyncSession

from qd_server.config import get_settings

logger_db = Log(
    "sqlalchemy", logger_level=get_settings().db.logging_level, channel_level=get_settings().db.logging_level
).getlogger()
logger_db_engine = Log(
    f"sqlalchemy.engine.Engine.{get_settings().db.logging_name}",
    logger_level=get_settings().db.logging_level,
    channel_level=get_settings().db.logging_level,
).getlogger()
if hasattr(get_settings().db.engine.pool.logger, "logger"):
    logger_db_pool = Log(
        get_settings().db.engine.pool.logger.logger,
        logger_level=get_settings().db.pool.logging_level,
        channel_level=get_settings().db.pool.logging_level,
    ).getlogger()
else:
    logger_db_pool = Log(
        get_settings().db.engine.sync_engine.pool.logger,
        logger_level=get_settings().db.pool.logging_level,
        channel_level=get_settings().db.pool.logging_level,
    ).getlogger()


class AlchemyMixin:
    @property
    def sql_session(self):
        return get_settings().db.scoped_session()

    @contextlib.asynccontextmanager
    async def transaction(self, sql_session: Optional[AsyncSession] = None) -> AsyncIterator[AsyncSession]:
        try:
            if sql_session is None:
                async with self.sql_session as sql_session:
                    # deepcode ignore AttributeLoadOnNone: sql_session is not None
                    async with sql_session.begin():
                        yield sql_session
            elif not sql_session.in_transaction():
                async with sql_session.begin():
                    yield sql_session
            else:
                yield sql_session
        finally:
            get_settings().db.scoped_session.remove()
