import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import akshare as ak
# from app.core.config import global_config

logger = logging.getLogger(__name__)

def get_market_symbols(force_update: bool = False) -> pd.DataFrame:
    """
    获取全市场标的（A股 + 港股通），支持本地缓存和定期更新。
    """
    # market_cfg = global_config.get("market_data", {})
    file_path = "data/market_symbols.csv"
    # update_interval_days = global_config.get("market_update_interval_days", 7)
    update_interval_days = 0

    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

    need_update = force_update
    if not os.path.exists(file_path):
        need_update = True
    else:
        try:
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if datetime.now() - file_mtime > timedelta(days=update_interval_days):
                need_update = True
        except Exception:
            need_update = True

    if need_update:
        logger.info("开始更新市场标的数据...")
        try:
            df = _fetch_and_merge_data()
            df.to_csv(file_path, index=False)
            logger.info(f"市场标的数据已更新并保存至: {file_path}, 共 {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"更新市场标的数据失败: {e}")
            if os.path.exists(file_path):
                logger.warning("尝试读取本地旧数据...")
                return pd.read_csv(file_path)
            raise
    else:
        logger.info(f"使用本地缓存的市场标的数据: {file_path}")
        return pd.read_csv(file_path)

def _fetch_and_merge_data() -> pd.DataFrame:
    """
    从 AkShare 获取数据并合并
    """
    logger.info("正在获取 A 股数据...")
    df_a = ak.stock_info_a_code_name()
    df_a = df_a.rename(columns={"code": "raw_code", "name": "name"})
    df_a["symbol"] = df_a["raw_code"].apply(_format_a_share_symbol)
    df_a["market"] = df_a["symbol"].apply(lambda x: x.split(".")[-1] if "." in x else "UNKNOWN")
    df_a = df_a[["symbol", "name", "market"]]
    # 过滤掉无法识别市场的
    df_a = df_a[df_a["market"] != "UNKNOWN"]

    # 2. 获取港股通数据
    logger.info("正在获取港股通数据...")

    df_hk = ak.stock_hk_ggt_components_em()
    # 查找包含“代码”和“名称”的列
    code_col = next((col for col in df_hk.columns if "代码" in col), None)
    name_col = next((col for col in df_hk.columns if "名称" in col), None)
    
    df_hk = df_hk.rename(columns={code_col: "raw_code", name_col: "name"})
    df_hk["symbol"] = df_hk["raw_code"].apply(lambda x: str(x).zfill(5) + ".HK")
    df_hk["market"] = "HK"
    df_hk = df_hk[["symbol", "name", "market"]]


    # 合并
    df_all = pd.concat([df_a, df_hk], ignore_index=True)
    df_all = df_all.drop_duplicates(subset=["symbol"])
    return df_all

def _format_a_share_symbol(code: str) -> str:
    code = str(code)
    if code.startswith("6"):
        return f"{code}.SH"
    elif code.startswith("0") or code.startswith("3"):
        return f"{code}.SZ"
    elif code.startswith("4") or code.startswith("8"):
        return f"{code}.BJ"
    else:
        return code 

# 兼容旧函数名（如果需要）
def get_stacks_in_all_market():
    logger.warning("get_stacks_in_all_market is deprecated, use get_market_symbols instead.")
    df = get_market_symbols()
    return df.to_dict('records')

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = get_market_symbols()
    print(df.head())
    print(f"Total: {len(df)}")
