import json
import os
from typing import Dict, Optional

import toml
import yaml

from qd_core.utils.i18n import gettext


class FileSystem:
    @staticmethod
    def __get_base_dir():
        """At most all application packages are just one level deep"""
        current_path = os.path.abspath(os.path.dirname(__file__))
        return os.path.abspath(os.path.dirname(current_path))

    @staticmethod
    def __get_config_directory() -> str:
        base_dir = FileSystem.__get_base_dir()
        return os.path.join(base_dir, "settings")

    @staticmethod
    def get_plugins_directory() -> str:
        base_dir = FileSystem.__get_base_dir()
        return os.path.join(base_dir, "plugins")

    @staticmethod
    def load_configuration(
        name: str = "settings.json",
        config_directory: Optional[str] = None,
    ) -> Dict:
        if config_directory is None:
            config_directory = FileSystem.__get_config_directory()

        file_path = os.path.join(config_directory, name)
        file_extension = os.path.splitext(name)[1].lower()

        if file_extension == ".json":
            with open(file_path) as file:
                input_data = json.load(file)
        elif file_extension == ".toml":
            with open(file_path) as file:
                input_data = toml.load(file)
        elif file_extension in [".yml", ".yaml"]:
            with open(file_path) as file:
                input_data = yaml.safe_load(file)
        else:
            raise ValueError(
                gettext("Unsupported configuration file format: {file_extension}").format(file_extension=file_extension)
            )

        return input_data
