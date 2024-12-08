import locale
import os
from typing import List, Optional

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po
from babel.support import NullTranslations, Translations

from qd_core.config import get_settings
from qd_core.utils.log import Log

logger = Log("QD.Core.Utils").getlogger()


def compile_po_to_mo(locale_dir, locales=None, domain="messages"):
    """
    Compile source po files to mo files

    :param locale_dir: path to locale directory
    :param locales: list of locales to compile. If None, all locales will be compiled.
    :param domain: translation domain, default: messages
    """
    if locales is None:
        # 自动扫描 locale 目录下的语言
        logger.info("Auto detect locales from %s", locale_dir)
        locales = [d for d in os.listdir(locale_dir) if os.path.isdir(os.path.join(locale_dir, d))]
        logger.info("Found locales: %s", locales)

    for _locale in locales:
        po_file_path = os.path.join(locale_dir, _locale, "LC_MESSAGES", f"{domain}.po")
        mo_file_path = os.path.join(locale_dir, _locale, "LC_MESSAGES", f"{domain}.mo")

        if os.path.exists(po_file_path):
            try:
                # 打开 .po 文件并解析
                with open(po_file_path, encoding="utf-8") as po_file:
                    catalog = read_po(po_file)
                    logger.info("PO file %s loaded successfully.", po_file_path)

                # 将 Catalog 写入 .mo 文件
                with open(mo_file_path, "wb") as mo_file:
                    write_mo(mo_file, catalog)
                    logger.info("MO file %s generated successfully.", mo_file_path)

                logger.info("Compiled %s.po file to %s.mo successfully for %s locale.", domain, domain, _locale)
            except Exception as e:
                logger.error("Compile %s.po to %s.mo failed for %s locale, error: %s", domain, domain, _locale, e)
        else:
            logger.error("Invalid PO file path: %s", po_file_path)


def check_mo_file(locale_dir, locales=None, domain="messages"):
    """
    Check .mo file is exist or not

    :param locale_dir: path to locale directory
    :param locales: list of locales to check. If None, all language will be checked
    :param domain: translation domain, default: messages
    """

    if locales is None:
        # 自动扫描 locale 目录下的语言
        logger.info("Auto detect locales from %s", locale_dir)
        locales = [d for d in os.listdir(locale_dir) if os.path.isdir(os.path.join(locale_dir, d))]
        logger.info("Found locales: %s", locales)

    for _locale in locales:
        mo_file_path = os.path.join(locale_dir, _locale, "LC_MESSAGES", f"{domain}.mo")
        if os.path.exists(mo_file_path):
            logger.info("MO file found: %s", mo_file_path)
        else:
            logger.warning("MO file not found: %s", mo_file_path)


def get_translation(
    locale_dir: Optional[str] = get_settings().i18n.locale_dir,
    user_locale: Optional[str] = get_settings().i18n.locale,
    fallback_locale: str = get_settings().i18n.fallback_locale,
    domain: str = get_settings().i18n.domain,
    names: List[str] = ["gettext"],
) -> NullTranslations:
    selected_locale = user_locale or locale.getdefaultlocale()[0]
    selected_locales = []
    if selected_locale is not None:
        selected_locales.append(selected_locale)
    selected_locales.append(fallback_locale)
    logger.info("Selected locales: %s", selected_locales)

    translation = Translations.load(locale_dir, selected_locales, domain)
    logger.info("Loaded translations: %s", translation)
    translation.install(names=names)
    return translation


TRANSLATION = get_translation()


def gettext(message: str):
    return TRANSLATION.gettext(message)


if __name__ == "__main__":
    # 配置翻译文件目录, 默认为上上层的 "locale" 目录
    locale_dir = get_settings().i18n.locale_dir

    # 编译 .po 文件为 .mo 文件
    logger.info("Compiling .po files to .mo files...")
    compile_po_to_mo(locale_dir=locale_dir)

    # 检查 .mo 文件是否生成
    logger.info("Checking .mo files...")
    check_mo_file(locale_dir=locale_dir)
