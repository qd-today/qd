#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: A76yyyy<q981331502@163.com>
#         http://www.a76yyyy.cn
# Created on 2022-03-14 12:00:00

from urllib.parse import urlparse


def parse_url(url):
    if not url:
        return None

    result = urlparse(url)

    # 检查是否成功解析出 netloc，如果没有，则返回 None
    if not result.netloc:
        return None

    # href = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"  # 考虑简化处理href为基本格式

    return {
        'scheme': result.scheme,
        'host': result.hostname,
        'port': result.port or None,
        'username': result.username,
        'password': result.password or None,
        'href': str(url)
    }


# if __name__ == '__main__':
#     # 测试URL列表
#     test_urls = [
#         'http://example.com/sasa',
#         'https://user:pass@example.com/sasa',
#         'socks5h://another.example.org',
#         'socks5://noauth@proxyserver',
#         'http://127.0.0.1',
#         'https://[2001:db8::1]',
#         'ftp://ftp.example.net',

#         # 包含端口号
#         'http://example.com:80',
#         'https://user:pass@example.com:443',
#         'socks5h://another.example.org:1080',
#         'socks5://noauth@192.168.1.1:1080',
#         'http://127.0.0.1:8080',
#         'https://[2001:db8::1]:443',

#         # 无 schema
#         'example.com',
#         'user:pass@example.com',
#         '127.0.0.1',
#         '[2001:db8::1]',

#         # 错误或不完整的URL示例
#         'http://:80',
#         'http://example.com:',
#         'http:///path',
#         'http://user:@example.com',
#     ]

#     # import re
#     for url in test_urls:
#         # regex_result = re.match(r'((?P<scheme>(https?|socks5h?)+)://)?((?P<username>[^:@/]+)(:(?P<password>[^@/]+))?@)?(?P<host>[^:@/]+):(?P<port>\d+)', url)

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
