# 开发说明

## 调试

```env
QD_DEBUG=True
```

### 更新翻译

```shell
# pybabel
# 解析提取翻译文本
pybabel.exe extract -o .\qd-core\src\qd_core\locale\qd_core.po .\qd-core\src\qd_core\ --last-translator="a76yyyy <a76yyyy@gmail.com>" --project="qd-core" --version="0.0.1" --no-wrap

# # 生成指定语言的翻译文件
# pybabel.exe init -i .\qd-core\src\qd_core\locale\qd_core.po -d .\qd-core\src\qd_core\locale -l zh_CN
# pybabel.exe init -i .\qd-core\src\qd_core\locale\qd_core.po -d .\qd-core\src\qd_core\locale -l en_US

# 更新翻译文本
pybabel.exe update -i .\qd-core\src\qd_core\locale\qd_core.po -d .\qd-core\src\qd_core\locale --no-wrap

# 编译翻译文件
pybabel.exe compile -d .\qd-core\src\qd_core\locale
```

## 项目构建

```shell
uv sync --all-packages --all-extras --group dev --group lint
uv run --directory qd-core qd_plugins
uv build --all-packages
```
