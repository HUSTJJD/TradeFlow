import os
import yaml
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class AppConfig:
    """
    应用程序配置管理器。
    从 YAML 文件加载配置并提供访问方法。
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        初始化 AppConfig。

        Args:
            config_path: 配置文件路径。如果为 None，默认为 config/config.yaml。
        """
        if config_path is None:
            current = os.path.dirname(__file__)
            while os.path.basename(current) != "app":
                current = os.path.dirname(current)
            base_dir = os.path.dirname(current)
            config_path = os.path.join(base_dir, "config", "config.yaml")
        self.config: Dict[str, Any] = self._load_config(config_path)

    def _load_config(self, path: str) -> Dict[str, Any]:
        """
        从 YAML 文件加载配置。

        Args:
            path: YAML 文件路径。

        Returns:
            包含配置的字典，如果失败则为空字典。
        """
        if not os.path.exists(path):
            logger.warning(f"配置文件 {path} 不存在。")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return {}

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
