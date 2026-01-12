import os
import yaml
from typing import Any
from .singleton import singleton_threadsafe


@singleton_threadsafe
class AppConfig:
    """
    应用程序配置管理器。
    从 YAML 文件加载配置并提供访问方法。
    """

    def __init__(self) -> None:
        """
        初始化 AppConfig。
        """
        current = os.path.dirname(__file__)
        while os.path.basename(current) != "app":
            current = os.path.dirname(current)
        base_dir = os.path.dirname(current)
        config_path = os.path.join(base_dir, "config", "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """
        使用点号表示法获取配置值。

        Args:
                        key: 配置键（例如 'longport.app_key'）。
                        default: 如果键未找到时的默认值。

        Returns:
                配置值或默认值。
        """
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default


# 全局配置实例
global_config = AppConfig()
