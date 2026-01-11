import sys
import os

# 强制设置标准输出编码为 utf-8
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 将项目根目录添加到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.logger import setup_logging


if __name__ == "__main__":
    setup_logging(global_config.get("log_level", "INFO"))
    
    quote_ctx = AppBootstrap().create_quote_context()
    if quote_ctx is None:
        return

    TradingWorkflow(quote_ctx=quote_ctx).run()