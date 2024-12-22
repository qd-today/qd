import asyncio
import base64
import datetime
import html
import os
import re
import time
import urllib
from typing import Annotated, Any, Dict, Optional

import aiohttp
from Crypto import Random
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from pydantic import Field
from tornado.web import HTTPError
from zoneinfo import ZoneInfo

from qd_core.config import get_settings
from qd_core.plugins.base import api_function_plugin, logger_plugins
from qd_core.utils.i18n import gettext

try:
    import ddddocr  # type: ignore
except ImportError as e:
    if get_settings().log.display_import_warning:
        logger_plugins.warning(
            gettext(
                'Import DdddOCR module falied: "%s". \n'
                "Tips: This warning message is only for prompting, it will not affect running of QD framework."
            ),
            e,
        )
    ddddocr = None


@api_function_plugin(
    namespace="qd.plugins.default",
    name="util-delay",
    path_list=["/delay/{seconds}", "/delay"],
    method_list=[["GET"], ["GET", "POST"]],
)
async def delay(
    seconds: Annotated[
        float,
        Field(
            ...,
            description=(
                gettext(
                    "seconds: delay the specified time, greater than {delay_max_timeout}s "
                    "are considered as delay {delay_max_timeout}s"
                ).format(delay_max_timeout=get_settings().client_request.delay_max_timeout)
            ),
        ),
    ] = 0.0,
):
    result = ""
    if seconds < 0.0:
        seconds = 0.0
        result = gettext("Error, seconds must be greater than 0.0, ")
    elif seconds > get_settings().client_request.delay_max_timeout:
        seconds = get_settings().client_request.delay_max_timeout
        result = gettext("Error, limited by delay_max_timeout, ")
    await asyncio.sleep(seconds)
    return result + gettext("delay {seconds} second.").format(seconds=seconds)


def yearday(year: int):
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        return "366"
    else:
        return "365"


GMT_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


@api_function_plugin(
    namespace="qd.plugins.default",
    name="util-timestamp",
    path_list=["/timestamp"],
    method_list=[["GET", "POST"]],
)
async def timestamp(
    ts: Annotated[Optional[float], Field(None, description="timestamp")] = None,
    dt: Annotated[Optional[str], Field(None, description="datetime string")] = None,
    form: Annotated[str, Field("%Y-%m-%d %H:%M:%S", description="format string")] = "%Y-%m-%d %H:%M:%S",
):
    try:
        if ts:
            ts = float(ts)
            if ts < 0.0:
                ts = 0.0
        rtv: Dict[str, Any] = {}

        if dt:
            _time = datetime.datetime.strptime(dt, form)
            ts = _time.timestamp()

        if ts:
            _time = datetime.datetime.fromtimestamp(ts)
        else:
            # 当前本机时间戳, 本机时间
            ts = time.time()
            _time = datetime.datetime.fromtimestamp(ts)
            rtv["本机时间"] = _time.strftime(form)
        _time_cst = datetime.datetime.fromtimestamp(ts, ZoneInfo("Asia/Shanghai"))
        _time_utc = datetime.datetime.fromtimestamp(ts, ZoneInfo("UTC"))
        rtv["完整时间戳"] = ts
        rtv["时间戳"] = int(rtv["完整时间戳"])
        rtv["16位时间戳"] = int(rtv["完整时间戳"] * 1000000)
        rtv["周"] = _time.strftime("%w/%W")
        rtv["日"] = "/".join([_time.strftime("%j"), yearday(_time.year)])
        rtv["北京时间"] = _time_cst.strftime(form)
        rtv["GMT格式"] = _time_utc.strftime(GMT_FORMAT)
        rtv["ISO格式"] = _time_utc.isoformat().split("+")[0] + "Z"
        rtv["状态"] = "200"
    except Exception as e:
        rtv["状态"] = str(e)
    return rtv


@api_function_plugin(
    namespace="qd.plugins.default",
    name="util-unicode",
    path_list=["/unicode"],
    method_list=[["GET", "POST"]],
)
async def unicode(
    content: Annotated[str, Field("", description=gettext("Content to be transcoded"))] = "",
    html_unescape: Annotated[
        bool,
        Field(
            False,
            description=gettext(
                "Whether to perform HTML escaping, the default is False, "
                "and the content needs to be urlencoded to enable this parameter"
            ),
        ),
    ] = False,
):
    rtv = {}
    try:
        tmp = bytes(content, "unicode_escape").decode("utf-8").replace(r"\u", r"\\u").replace(r"\\\u", r"\\u")
        tmp = bytes(tmp, "utf-8").decode("unicode_escape")
        tmp = tmp.encode("utf-8").replace(b"\xc2\xa0", b"\xa0").decode("unicode_escape")
        if html_unescape:
            tmp = html.unescape(tmp)
        rtv["转换后"] = tmp
        rtv["状态"] = "200"
    except Exception as e:
        rtv["状态"] = str(e)
    return rtv


@api_function_plugin(
    namespace="qd.plugins.default",
    name="util-urldecode",
    path_list=["/urldecode"],
    method_list=[["GET", "POST"]],
)
async def urldecode(
    content: Annotated[
        str,
        Field(
            "",
            description=(
                gettext(
                    "The urlencoded content to be transcoded. "
                    "If content is a non-utf-8 encoded urlencoded string, "
                    "please urlencode it again before passing it in"
                )
            ),
        ),
    ] = "",
    encoding: Annotated[str, Field("utf-8", description=gettext("Specified encoding, default is utf-8"))] = "utf-8",
    unquote_plus: Annotated[
        bool,
        Field(
            False,
            description=gettext(
                "Whether to decode plus(+) to space( ), only valid when encoding is utf-8, default is False"
            ),
        ),
    ] = False,
):
    rtv = {}
    try:
        if unquote_plus:
            rtv["转换后"] = urllib.parse.unquote_plus(content, encoding=encoding)
        else:
            rtv["转换后"] = urllib.parse.unquote(content, encoding=encoding)
        rtv["状态"] = "200"
    except Exception as e:
        rtv["状态"] = str(e)
    return rtv


@api_function_plugin(
    namespace="qd.plugins.default",
    name="util-gb2312",
    path_list=["/gb2312"],
    method_list=[["GET", "POST"]],
)
async def gb2312(content: Annotated[str, Field("", description=gettext("Content to be transcoded"))] = ""):
    rtv = {}
    try:
        rtv["转换后"] = urllib.parse.unquote(content, encoding="gb2312")
        rtv["状态"] = "200"
    except Exception as e:
        rtv["状态"] = str(e)
    return rtv


@api_function_plugin(
    namespace="qd.plugins.default",
    name="util-regex",
    path_list=["/regex"],
    method_list=[["GET", "POST"]],
)
async def regex(
    data: Annotated[str, Field("", description=gettext("Raw data"))] = "",
    p: Annotated[str, Field("", description=gettext("Regular expression"))] = "",
):
    rtv: Dict[str, Any] = {}
    try:
        temp = {}
        ds = re.findall(p, data, re.IGNORECASE)
        for cnt, d in enumerate(ds):
            temp[cnt + 1] = d
        rtv["数据"] = temp
        rtv["状态"] = "OK"
    except Exception as e:
        rtv["状态"] = str(e)
    return rtv


@api_function_plugin(
    namespace="qd.plugins.default",
    name="util-string-replace",
    path_list=["/string/replace"],
    method_list=[["GET", "POST"]],
)
async def string_replace(
    p: Annotated[str, Field("", description=gettext("Regular expression"))] = "",
    t: Annotated[str, Field("", description=gettext("Content to be replaced"))] = "",
    s: Annotated[str, Field("", description=gettext("String to be replaced"))] = "",
    r: Annotated[str, Field("", description=gettext("Return type, 'text' or 'json', default is json"))] = "",
):
    rtv = {}
    try:
        rtv["原始字符串"] = s
        rtv["处理后字符串"] = re.sub(p, t, s)
        rtv["状态"] = "OK"
        if r == "text":
            return rtv["处理后字符串"]
    except Exception as e:
        rtv["状态"] = str(e)
    return rtv


@api_function_plugin(
    namespace="qd.plugins.default",
    name="util-rsa",
    path_list=["/rsa"],
    method_list=[["GET", "POST"]],
)
async def rsa(
    key: Annotated[str, Field("", description=gettext("RSA private key"))] = "",
    data: Annotated[str, Field("", description=gettext("Data to be encrypted or decrypted"))] = "",
    f: Annotated[str, Field("", description=gettext("'encode' is encryption, 'decode' is decryption"))] = "",
    rand_bytes_str: Annotated[
        Optional[str], Field(None, description=gettext("Random byte string, default is None"))
    ] = None,
    rand_bytes_encode: Annotated[
        str, Field("utf-8", description=gettext("The encoding method of the random byte string, default is utf-8"))
    ] = "utf-8",
):
    try:
        if key and data and f:
            lines = ""
            for line in key.split("\n"):
                if line.find("--") < 0:
                    line = line.replace(" ", "+")
                lines = lines + line + "\n"
            data = data.replace(" ", "+")

            def randfunc(i: int) -> bytes:
                if rand_bytes_str:
                    return rand_bytes_str.encode(rand_bytes_encode)
                return Random.get_random_bytes(i)

            cipher_rsa = PKCS1_v1_5.new(RSA.import_key(lines), randfunc if rand_bytes_str else None)
            if f.find("encode") > -1:
                crypt_text = cipher_rsa.encrypt(bytes(data, encoding="utf8"))
                crypt_text_str = base64.b64encode(crypt_text).decode("utf8")
                return crypt_text_str
            elif f.find("decode") > -1:
                decrypt_text = cipher_rsa.decrypt(base64.b64decode(data), Random.new().read(1))
                decrypt_text_str = decrypt_text.decode("utf8")
                return decrypt_text_str
            else:
                raise Exception(gettext("Function Selection Error"))
        else:
            return Exception(gettext("Incomplete parameters, please confirm"))
    except Exception as e:
        raise e


class DdddOcrServer:
    def __init__(self):
        if ddddocr is not None and hasattr(ddddocr, "DdddOcr"):
            self.oldocr = ddddocr.DdddOcr(old=True, show_ad=False)
            self.ocr = ddddocr.DdddOcr(show_ad=False)
            self.det = ddddocr.DdddOcr(det=True, show_ad=False)
            self.slide = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
            self.extra = {}
            if (
                len(get_settings().ddddocr.extra_onnx_name) == len(get_settings().ddddocr.extra_charsets_name)
                and get_settings().ddddocr.extra_onnx_name[0]
                and get_settings().ddddocr.extra_charsets_name[0]
            ):
                for onnx_name in get_settings().ddddocr.extra_onnx_name:
                    self.extra[onnx_name] = ddddocr.DdddOcr(
                        show_ad=False,
                        import_onnx_path=os.path.join(
                            os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                            "config",
                            f"{onnx_name}.onnx",
                        ),
                        charsets_path=os.path.join(
                            os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                            "config",
                            f"{onnx_name}.json",
                        ),
                    )
                    logger_plugins.info(gettext("Successfully loaded custom ONNX model: %s.onnx"), onnx_name)

    def classification(self, img: bytes, old=False, extra_onnx_name=""):
        if extra_onnx_name:
            return self.extra[extra_onnx_name].classification(img)
        if old:
            return self.oldocr.classification(img)
        else:
            return self.ocr.classification(img)

    def detection(self, img: bytes):
        return self.det.detection(img)

    def slide_match(self, imgtarget: bytes, imgbg: bytes, comparison=False, simple_target=False):
        if comparison:
            return self.slide.slide_comparison(imgtarget, imgbg)
        if not simple_target:
            try:
                return self.slide.slide_match(imgtarget, imgbg)
            except Exception as e:
                logger_plugins.debug(gettext("slide_match error: %s"), e, exc_info=get_settings().log.traceback_print)
        return self.slide.slide_match(imgtarget, imgbg, simple_target=True)


if ddddocr:
    DDDDOCR_SERVER: Optional[DdddOcrServer] = DdddOcrServer()
else:
    DDDDOCR_SERVER = None


async def get_img_from_url(imgurl):
    async with aiohttp.ClientSession(conn_timeout=get_settings().client_request.connect_timeout) as session:
        async with session.get(imgurl, verify_ssl=False, timeout=get_settings().client_request.request_timeout) as res:
            content = await res.read()
            base64_data = base64.b64encode(content).decode()
            return base64.b64decode(base64_data)


async def get_img(
    img="",
    imgurl="",
):
    if img:
        # 判断是否为URL
        if img.startswith("http"):
            try:
                return await get_img_from_url(img)
            except Exception as e:
                logger_plugins.debug(
                    gettext("get_img_from_url error: %s"), e, exc_info=get_settings().log.traceback_print
                )
                return base64.b64decode(img)
        return base64.b64decode(img)
    elif imgurl:
        return await get_img_from_url(imgurl)
    else:
        raise HTTPError(415)


@api_function_plugin(
    namespace="qd.plugins.default",
    name="util-dddd-ocr",
    path_list=["/dddd/ocr"],
    method_list=[["GET", "POST"]],
)
async def dddd_ocr(
    img: Annotated[str, Field("", description=gettext("Content of the Base64 image to be recognized"))] = "",
    imgurl: Annotated[str, Field("", description=gettext("URL address of the web image to be identified"))] = "",
    old: Annotated[
        bool, Field(False, description=gettext("Whether to use the old model, the default is False"))
    ] = False,
    extra_onnx_name: Annotated[
        str, Field("", description=gettext("Customize ONNX filename, the default is None"))
    ] = "",
):
    rtv = {}
    try:
        if DDDDOCR_SERVER:
            img_bytes = await get_img(img, imgurl)
            rtv["Result"] = DDDDOCR_SERVER.classification(img_bytes, old=old, extra_onnx_name=extra_onnx_name)
            rtv["状态"] = "OK"
        else:
            raise HTTPError(406)
    except Exception as e:
        rtv["状态"] = str(e)
    return rtv


@api_function_plugin(
    namespace="qd.plugins.default",
    name="util-dddd-det",
    path_list=["/dddd/det"],
    method_list=[["GET", "POST"]],
)
async def dddd_det(
    img: Annotated[str, Field("", description=gettext("Content of the Base64 image to be detected"))] = "",
    imgurl: Annotated[str, Field("", description=gettext("URL address of the web image to be detected"))] = "",
):
    rtv = {}
    try:
        if DDDDOCR_SERVER:
            img_bytes = await get_img(img, imgurl)
            rtv["Result"] = DDDDOCR_SERVER.detection(img_bytes)
            rtv["状态"] = "OK"
        else:
            raise HTTPError(406)
    except Exception as e:
        rtv["状态"] = str(e)
    return rtv


@api_function_plugin(
    namespace="qd.plugins.default",
    name="util-dddd-slide",
    path_list=["/dddd/slide"],
    method_list=[["GET", "POST"]],
)
async def dddd_slide(
    imgtarget: Annotated[str, Field("", description=gettext("Content of the Base64 image to be recognized"))] = "",
    imgbg: Annotated[str, Field("", description=gettext("URL address of the web image to be identified"))] = "",
    simple_target: Annotated[
        bool,
        Field(
            False, description=gettext("Whether the small slider image contains too much background, default is False")
        ),
    ] = False,
    comparison: Annotated[
        bool,
        Field(
            False,
            description=gettext(
                "Whether `imgtarget` is not a small slider, True means the original image with pits, "
                "False means a small slider, the default is False"
            ),
        ),
    ] = False,
):
    rtv = {}
    try:
        if DDDDOCR_SERVER:
            imgtarget_bytes = await get_img(imgtarget, "")
            imgbg_bytes = await get_img(imgbg, "")
            rtv["Result"] = DDDDOCR_SERVER.slide_match(
                imgtarget_bytes, imgbg_bytes, comparison=comparison, simple_target=simple_target
            )
            rtv["状态"] = "OK"
        else:
            raise HTTPError(406)
    except Exception as e:
        rtv["状态"] = str(e)
    return rtv
