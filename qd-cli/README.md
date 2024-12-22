# 开发说明

## 调试

```env
QD_DEBUG=True
```

### 更新翻译

```shell
# pybabel
# 解析提取翻译文本
pybabel.exe extract -o .\qd-cli\src\qd_cli\locale\qd_cli.po .\qd-cli\src\qd_cli\ --last-translator="a76yyyy <a76yyyy@gmail.com>" --project="qd-cli" --version="0.0.1" --no-wrap

# # 生成指定语言的翻译文件
# pybabel.exe init -i .\qd-cli\src\qd_cli\locale\qd_cli.po -d .\qd-cli\src\qd_cli\locale -l zh_CN
# pybabel.exe init -i .\qd-cli\src\qd_cli\locale\qd_cli.po -d .\qd-cli\src\qd_cli\locale -l en_US

# 更新翻译文本
pybabel.exe update -i .\qd-cli\src\qd_cli\locale\qd_cli.po -d .\qd-cli\src\qd_cli\locale --no-wrap

# 编译翻译文件
pybabel.exe compile -d .\qd-cli\src\qd_cli\locale
```

## 项目构建

```shell
uv sync --all-packages --all-extras --group dev --group lint
uv run --directory qd-core qd_plugins
uv build --all-packages
```
