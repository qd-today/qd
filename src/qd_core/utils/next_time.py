import datetime
import random
import time
from typing import Literal, Union

import croniter
from pydantic import BaseModel, Field, field_validator
from qd_core.utils.decorator import log_and_raise_error
from qd_core.utils.log import Log

logger_nexttime = Log("QD.Core.NextTime").getlogger()


class NextTsBase(BaseModel):
    randsw: bool = False
    sw: bool = False
    tz1: int = Field(default=0, validate_default=True)
    tz2: int = Field(default=0, validate_default=True)

    @field_validator("tz1", "tz2")
    @classmethod
    def validate_tz(cls, v, values):
        if values["randsw"] and values["sw"] and (v is not None and values["tz1"] > values["tz2"]):
            raise ValueError("tz1 必须小于等于 tz2")
        return v


class OnTimeEnv(NextTsBase):
    mode: Literal["ontime"]
    date: str
    time: str


class CronEnv(NextTsBase):
    mode: Literal["cron"]
    cron_val: str


class Cal:
    @log_and_raise_error(logger_nexttime, "Calculate Next Timestamp error: %s")
    def cal_next_ts_ontime(self, envs: OnTimeEnv) -> int:
        t = f"{envs.date} {envs.time}"
        d = datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S").timetuple()
        ts = int(time.mktime(d))

        if envs.randsw and envs.sw:
            r_ts = random.randint(envs.tz1, envs.tz2)
            ts += r_ts

        return ts

    @log_and_raise_error(logger_nexttime, "Calculate Next Timestamp error: %s")
    async def cal_next_ts_cron(self, envs: CronEnv) -> int:
        cron = croniter.croniter(envs.cron_val, datetime.datetime.now())
        t = cron.get_next(datetime.datetime).strftime("%Y-%m-%d %H:%M:%S")

        d = datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S").timetuple()
        ts = int(time.mktime(d))

        if envs.randsw and envs.sw:
            r_ts = random.randint(envs.tz1, envs.tz2)
            ts += r_ts

        return ts

    def cal_next_ts(self, envs: Union[OnTimeEnv, CronEnv]) -> int:
        if isinstance(envs, OnTimeEnv):
            return self.cal_next_ts_ontime(envs)
        if isinstance(envs, CronEnv):
            return self.cal_next_ts_cron(envs)
        raise TypeError("Unsupported environment class for timestamp calculation")
