#!/usr/bin/env python
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: A76yyyy<a76yyyy@gmail.com>
#         http://www.a76yyyy.cn
# Created on 2022-03-14 12:00:00

import re
from typing import Optional
from urllib.parse import ParseResult, urlparse

from pydantic import AnyUrl, BaseModel


class UrlInfo(BaseModel):
    scheme: str
    host: Optional[str]
    port: Optional[int]
    username: Optional[str]
    password: Optional[str]
    href: AnyUrl


def parse_url(url: str):
    if not url:
        return None

    result: ParseResult = urlparse(url)

    # 检查是否成功解析出 netloc，如果没有，则返回 None
    if not result.netloc:
        return None

    # href = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"  # 考虑简化处理href为基本格式

    return UrlInfo(
        scheme=result.scheme,
        host=result.hostname,
        port=result.port or None,
        username=result.username,
        password=result.password or None,
        href=AnyUrl(url),
    )


def urlmatch(url):
    reobj = re.compile(
        r"""(?xi)\A
                ([a-z][a-z0-9+\-.]*://)?                            # Scheme
                ([a-z0-9\-._~%]+                                    # domain or IPv4 host
                |\[[a-z0-9\-._~%!$&'()*+,;=:]+\])                   # IPv6+ host
                (:[0-9]+)? """  # :port
    )
    match = reobj.search(url)
    return match.group()


def url_match_with_limit(url):
    ip_middle_octet = r"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5]))"
    ip_last_octet = r"(?:\.(?:0|[1-9]\d?|1\d\d|2[0-4]\d|25[0-5]))"

    reobj = re.compile(  # noqa: W605
        r"^"
        # protocol identifier
        r"(?:(?:https?|ftp)://)"
        # user:pass authentication
        r"(?:[-a-z\u00a1-\uffff0-9._~%!$&'()*+,;=:]+"
        r"(?::[-a-z0-9._~%!$&'()*+,;=:]*)?@)?"
        r"(?:"
        r"(?P<private_ip>"
        # IP address exclusion
        # private & local networks
        r"(?:(?:10|127)" + ip_middle_octet + r"{2}" + ip_last_octet + r")|"
        r"(?:(?:169\.254|192\.168)" + ip_middle_octet + ip_last_octet + r")|"
        r"(?:172\.(?:1[6-9]|2\d|3[0-1])" + ip_middle_octet + ip_last_octet + r"))"
        r"|"
        # private & local hosts
        r"(?P<private_host>"
        r"(?:localhost))"
        r"|"
        # IP address dotted notation octets
        # excludes loopback network 0.0.0.0
        # excludes reserved space >= 224.0.0.0
        # excludes network & broadcast addresses
        # (first & last IP address of each class)
        r"(?P<public_ip>"
        r"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
        r"" + ip_middle_octet + r"{2}"
        r"" + ip_last_octet + r")"
        r"|"
        # IPv6 RegEx from https://stackoverflow.com/a/17871737
        r"\[("
        # 1:2:3:4:5:6:7:8
        r"([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|"
        # 1::                              1:2:3:4:5:6:7::
        r"([0-9a-fA-F]{1,4}:){1,7}:|"
        # 1::8             1:2:3:4:5:6::8  1:2:3:4:5:6::8
        r"([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|"
        # 1::7:8           1:2:3:4:5::7:8  1:2:3:4:5::8
        r"([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|"
        # 1::6:7:8         1:2:3:4::6:7:8  1:2:3:4::8
        r"([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|"
        # 1::5:6:7:8       1:2:3::5:6:7:8  1:2:3::8
        r"([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|"
        # 1::4:5:6:7:8     1:2::4:5:6:7:8  1:2::8
        r"([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|"
        # 1::3:4:5:6:7:8   1::3:4:5:6:7:8  1::8
        r"[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|"
        # ::2:3:4:5:6:7:8  ::2:3:4:5:6:7:8 ::8       ::
        r":((:[0-9a-fA-F]{1,4}){1,7}|:)|"
        # fe80::7:8%eth0   fe80::7:8%1
        # (link-local IPv6 addresses with zone index)
        r"fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|"
        r"::(ffff(:0{1,4}){0,1}:){0,1}"
        r"((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}"
        # ::255.255.255.255   ::ffff:255.255.255.255  ::ffff:0:255.255.255.255
        # (IPv4-mapped IPv6 addresses and IPv4-translated addresses)
        r"(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|"
        r"([0-9a-fA-F]{1,4}:){1,4}:"
        r"((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}"
        # 2001:db8:3:4::192.0.2.33  64:ff9b::192.0.2.33
        # (IPv4-Embedded IPv6 Address)
        r"(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])"
        r")\]|"
        # host name
        r"(?:(?:(?:xn--[-]{0,2})|[a-z\u00a1-\uffff\U00010000-\U0010ffff0-9]-?)*"
        r"[a-z\u00a1-\uffff\U00010000-\U0010ffff0-9]+)"
        # domain name
        r"(?:\.(?:(?:xn--[-]{0,2})|[a-z\u00a1-\uffff\U00010000-\U0010ffff0-9]-?)*"
        r"[a-z\u00a1-\uffff\U00010000-\U0010ffff0-9]+)*"
        # TLD identifier
        r"(?:\.(?:(?:xn--[-]{0,2}[a-z\u00a1-\uffff\U00010000-\U0010ffff0-9]{2,})|"
        r"[a-z\u00a1-\uffff\U00010000-\U0010ffff]{2,}))"
        r")"
        # port number
        r"(?::\d{2,5})?"
        # resource path
        r"(?:/[-a-z\u00a1-\uffff\U00010000-\U0010ffff0-9._~%!$&'()*+,;=:@/]*)?"
        # query string
        r"(?:\?\S*)?"
        # fragment
        r"(?:#\S*)?"
        r"$",
        re.UNICODE | re.IGNORECASE,
    )

    match = reobj.search(url)
    if match:
        return match.group()
    return ""


def domain_match(domain):
    reobj = re.compile(
        r"^(?:[a-zA-Z0-9]"  # First character of the domain
        r"(?:[a-zA-Z0-9-_]{0,61}[A-Za-z0-9])?\.)"  # Sub domain + hostname
        r"+[A-Za-z0-9][A-Za-z0-9-_]{0,61}"  # First 61 characters of the gTLD
        r"[A-Za-z]$"  # Last character of the gTLD
    )

    match = reobj.search(domain)
    if match:
        return match.group()
    return ""


# if __name__ == "__main__":
#     # 测试URL列表
#     test_urls = [
#         "http://example.com/sasa",
#         "https://user:pass@example.com/sasa",
#         "socks5h://another.example.org",
#         "socks5://noauth@proxyserver",
#         "http://127.0.0.1",
#         "https://[2001:db8::1]",
#         "ftp://ftp.example.net",
#         # 包含端口号
#         "http://example.com:80",
#         "https://user:pass@example.com:443",
#         "socks5h://another.example.org:1080",
#         "socks5://noauth@192.168.1.1:1080",
#         "http://127.0.0.1:8080",
#         "https://[2001:db8::1]:443",
#         # 无 schema
#         "example.com",
#         "user:pass@example.com",
#         "127.0.0.1",
#         "[2001:db8::1]",
#         # 错误或不完整的URL示例
#         "http://:80",
#         "http://example.com:",
#         "http:///path",
#         "http://user:@example.com",
#     ]

#     # import re
#     for url in test_urls:
#         # regex_result = re.match(
#         #     r"((?P<scheme>(https?|socks5h?)+)://)?((?P<username>[^:@/]+)(:(?P<password>[^@/]+))?@)?(?P<host>[^:@/]+):(?P<port>\d+)",
#         #     url,
#         # )

#         parse_result = urlparse(url)

#         print(f"URL: {url}")

#         # if regex_result:
#         #     print("Regex Matched components:")
#         #     for key, value in regex_result.groupdict().items():
#         #         if value:
#         #             print(f"{key}: {value}")
#         # else:
#         #     print(f"URL '{url}' did not match the regex pattern.\n")

#         print("Parsed with urlparse:")
#         print(f"Scheme: {parse_result.scheme}")
#         print(f"Host: {parse_result.hostname}")
#         print(f"Port: {parse_result.port}")
#         print(f"Username: {parse_result.username}")
#         print(f"Password: {parse_result.password}")

#         print("\n")
