from sqlalchemy import Column, Integer, LargeBinary, Numeric, String, Table, Text, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql.sqltypes import NullType

Base = declarative_base()
metadata = Base.metadata


class TaskOld20220523(Base):
    __tablename__ = '_task_old_20220523'

    tplid = Column(Integer, nullable=False)
    userid = Column(Integer, nullable=False)
    disabled = Column(Integer, nullable=False, server_default=text('0'))
    success_count = Column(Integer, nullable=False, server_default=text('0'))
    failed_count = Column(Integer, nullable=False, server_default=text('0'))
    last_failed_count = Column(Integer, nullable=False, server_default=text('0'))
    ctime = Column(Integer, nullable=False)
    mtime = Column(Integer, nullable=False)
    ontimeflg = Column(Integer, nullable=False, server_default=text('0'))
    ontime = Column(String(256), nullable=False, server_default=text("'00:10:00'"))
    _groups = Column(String(128), nullable=False, server_default=text("'None'"))
    pushsw = Column(Numeric(128), nullable=False, server_default=text('\'{"logen":false,"pushen":true}\''))
    newontime = Column(Numeric(256), nullable=False, server_default=text('\'{"sw":false,"time":"00:10:10","randsw":false,"tz1":0,"tz2":0}\''))
    retry_count = Column(Integer, nullable=False, server_default=text('8'))
    id = Column(Integer, primary_key=True)
    init_env = Column(LargeBinary)
    env = Column(LargeBinary)
    session = Column(LargeBinary)
    last_success = Column(Integer)
    last_failed = Column(Integer)
    next = Column(Integer, server_default=text('NULL'))
    note = Column(String(256))
    retry_interval = Column(Integer)


class Notepad(Base):
    __tablename__ = 'notepad'

    id = Column(Integer, primary_key=True)
    userid = Column(Integer, nullable=False)
    notepadid = Column(Integer, nullable=False)
    content = Column(Text)


class Pubtpl(Base):
    __tablename__ = 'pubtpl'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, server_default=text("''"))
    author = Column(Text, nullable=False, server_default=text("''"))
    comments = Column(Text, nullable=False, server_default=text("''"))
    content = Column(Text, nullable=False, server_default=text("''"))
    filename = Column(Text, nullable=False, server_default=text("''"))
    date = Column(Text, nullable=False, server_default=text("''"))
    version = Column(Text, nullable=False, server_default=text("''"))
    url = Column(Text, nullable=False, server_default=text("''"))
    update = Column(Text, nullable=False, server_default=text("''"))
    reponame = Column(Text, nullable=False, server_default=text("''"))
    repourl = Column(Text, nullable=False, server_default=text("''"))
    repoacc = Column(Text, nullable=False, server_default=text("''"))
    repobranch = Column(Text, nullable=False, server_default=text("''"))
    commenturl = Column(Text, nullable=False, server_default=text("''"))


class PushRequest(Base):
    __tablename__ = 'push_request'

    from_tplid = Column(Integer, nullable=False)
    from_userid = Column(Integer, nullable=False)
    status = Column(Integer, nullable=False, index=True, server_default=text('0'))
    ctime = Column(Integer, nullable=False)
    mtime = Column(Integer, nullable=False)
    atime = Column(Integer, nullable=False)
    id = Column(Integer, primary_key=True)
    to_tplid = Column(Integer)
    to_userid = Column(Integer, index=True)
    msg = Column(String(1024))


class Site(Base):
    __tablename__ = 'site'

    id = Column(Integer, primary_key=True)
    regEn = Column(Integer, nullable=False, server_default=text('1'))
    MustVerifyEmailEn = Column(Integer, nullable=False, server_default=text('0'))
    logDay = Column(Integer, nullable=False, server_default=text('365'))
    repos = Column(Text, nullable=False, server_default=text('\'{"repos":[{"reponame":"default","repourl":"https://github.com/qiandao-today/templates","repobranch":"master","repoacc":true}], "lastupdate":0}\''))


t_sqlite_sequence = Table(
    'sqlite_sequence', metadata,
    Column('name', NullType),
    Column('seq', NullType)
)


class Task(Base):
    __tablename__ = 'task'

    tplid = Column(Integer, nullable=False, index=True)
    userid = Column(Integer, nullable=False, index=True)
    disabled = Column(Integer, nullable=False, server_default=text('0'))
    success_count = Column(Integer, nullable=False, server_default=text('0'))
    failed_count = Column(Integer, nullable=False, server_default=text('0'))
    last_failed_count = Column(Integer, nullable=False, server_default=text('0'))
    ctime = Column(Integer, nullable=False)
    mtime = Column(Integer, nullable=False)
    ontimeflg = Column(Integer, nullable=False, server_default=text('0'))
    ontime = Column(String(256), nullable=False, server_default=text("'00:10:00'"))
    _groups = Column(Numeric(128), nullable=False, server_default=text("'None'"))
    pushsw = Column(Numeric(128), nullable=False, server_default=text('\'{"logen":false,"pushen":true}\''))
    newontime = Column(Numeric(256), nullable=False, server_default=text('\'{"sw":false,"time":"00:10:10","randsw":false,"tz1":0,"tz2":0}\''))
    retry_count = Column(Integer, nullable=False, server_default=text('8'))
    id = Column(Integer, primary_key=True)
    init_env = Column(LargeBinary)
    env = Column(LargeBinary)
    session = Column(LargeBinary)
    last_success = Column(Integer)
    last_failed = Column(Integer)
    next = Column(Integer, server_default=text('NULL'))
    note = Column(String(256))
    retry_interval = Column(Integer)


class Tasklog(Base):
    __tablename__ = 'tasklog'

    taskid = Column(Integer, nullable=False)
    success = Column(Integer, nullable=False)
    ctime = Column(Integer, nullable=False)
    id = Column(Integer, primary_key=True)
    msg = Column(Text)


class Tpl(Base):
    __tablename__ = 'tpl'

    disabled = Column(Integer, nullable=False, server_default=text('0'))
    public = Column(Integer, nullable=False, index=True, server_default=text('0'))
    lock = Column(Integer, nullable=False, server_default=text('0'))
    success_count = Column(Integer, nullable=False, server_default=text('0'))
    failed_count = Column(Integer, nullable=False, server_default=text('0'))
    ctime = Column(Integer, nullable=False)
    mtime = Column(Integer, nullable=False)
    atime = Column(Integer, nullable=False)
    updateable = Column(Integer, nullable=False, server_default=text('0'))
    _groups = Column(String(256), nullable=False, server_default=text("'None'"))
    id = Column(Integer, primary_key=True)
    userid = Column(Integer)
    siteurl = Column(String(256), index=True)
    sitename = Column(String(128), index=True)
    banner = Column(String(1024))
    fork = Column(Integer)
    har = Column(NullType)
    tpl = Column(NullType)
    variables = Column(Text)
    interval = Column(Integer)
    note = Column(String(1024))
    last_success = Column(Integer)
    tplurl = Column(String(1024), server_default=text("''"))


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String(256), nullable=False, unique=True)
    email_verified = Column(Integer, nullable=False, server_default=text('0'))
    password = Column(Numeric(128), nullable=False)
    password_md5 = Column(Numeric(128), nullable=False, server_default=text("''"))
    userkey = Column(Numeric(128), nullable=False)
    ctime = Column(Integer, nullable=False)
    mtime = Column(Integer, nullable=False)
    atime = Column(Integer, nullable=False)
    cip = Column(Numeric(16), nullable=False)
    mip = Column(Numeric(16), nullable=False)
    aip = Column(Numeric(16), nullable=False)
    skey = Column(Numeric(128), nullable=False, server_default=text("''"))
    barkurl = Column(Numeric(128), nullable=False, server_default=text("''"))
    wxpusher = Column(Numeric(128), nullable=False, server_default=text("''"))
    noticeflg = Column(Integer, nullable=False, server_default=text('1'))
    logtime = Column(Numeric(1024), nullable=False, server_default=text('\'{"en":false,"time":"20:00:00","ts":0,"schanEn":false,"WXPEn":false}\''))
    status = Column(Numeric(1024), nullable=False, server_default=text("'Enable'"))
    diypusher = Column(Numeric(1024), nullable=False, server_default=text("''"))
    qywx_token = Column(Numeric(1024), nullable=False, server_default=text("''"))
    tg_token = Column(Numeric(1024), nullable=False, server_default=text("''"))
    dingding_token = Column(Numeric(1024), nullable=False, server_default=text("''"))
    push_batch = Column(Numeric(1024), nullable=False, server_default=text('\'{"sw":false,"time":0,"delta":86400}\''))
    nickname = Column(String(64), unique=True)
    role = Column(String(128))
