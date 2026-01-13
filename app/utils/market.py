import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import akshare as ak
from app.core import Market, global_config

logger = logging.getLogger(__name__)


def get_market_symbols(force_update: bool = False) -> pd.DataFrame:
    """
    获取全市场标的（A股 + 港股通），支持本地缓存和定期更新。
    """
    file_path = "data/market_symbols.csv"
    update_interval_days = global_config.market_data.update_interval_days
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    need_update = not os.path.exists(file_path) or force_update
    if not need_update:
        try:
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if datetime.now() - file_mtime > timedelta(days=update_interval_days):
                need_update = True
        except Exception:
            need_update = True

    if need_update:
        logger.info("开始更新市场标的数据...")
        df = _fetch_and_merge_data()
        df.to_csv(file_path, index=False)
        logger.info(f"市场标的数据已更新并保存至: {file_path}, 共 {len(df)} 条")
    else:
        logger.info(f"使用本地缓存的市场标的数据: {file_path}")
        df = pd.read_csv(file_path)
    return df


def _fetch_and_merge_data() -> pd.DataFrame:
    """
    从 AkShare 获取数据并合并
    """
    df_a = ak.stock_info_a_code_name()
    df_a = df_a.rename(columns={"code": "raw_code", "name": "name"})
    symbol_board = df_a["raw_code"].apply(_get_a_share_symbol_and_board)
    df_a["symbol"] = symbol_board.apply(lambda x: x[0])
    df_a["board"] = symbol_board.apply(lambda x: x[1])
    df_a["market"] = df_a["symbol"].apply(
        lambda x: x.split(".")[-1] if "." in x else "UNKNOWN"
    )
    df_a = df_a[["symbol", "name", "market", "board"]]
    df_a = df_a[df_a["market"] != "UNKNOWN"]
    logger.info(f"获取A股数据...: 共 {len(df_a)} 条")

    df_hk = ak.stock_hk_ggt_components_em()
    code_col = next((col for col in df_hk.columns if "代码" in col), None)
    name_col = next((col for col in df_hk.columns if "名称" in col), None)
    df_hk = df_hk.rename(columns={code_col: "raw_code", name_col: "name"})
    df_hk["symbol"] = df_hk["raw_code"].apply(lambda x: str(x).zfill(5) + ".HK")
    df_hk["market"] = "HK"
    df_hk["board"] = Market.HK.value
    df_hk = df_hk[["symbol", "name", "market", "board"]]
    logger.info(f"获取港股通数据...: 共 {len(df_hk)} 条")
    # 合并
    df_all = pd.concat([df_a, df_hk], ignore_index=True)
    df_all = df_all.drop_duplicates(subset=["symbol"])
    return df_all


def _get_a_share_symbol_and_board(code: str) -> tuple[str, str]:
    code = str(code)
    # 沪市主板 (600, 601, 603, 605)
    if code.startswith("60"):
        return f"{code}.SH", Market.MAIN.value
    # 沪市科创板 (688, 689)
    elif code.startswith("68"):
        return f"{code}.SH", Market.STAR.value
    # 沪市B股 (900)
    elif code.startswith("900"):
        return f"{code}.SH", Market.BSHARE.value
    # 深市主板 (000, 001, 002, 003)
    elif code.startswith("00"):
        return f"{code}.SZ", Market.MAIN.value
    # 深市创业板 (300, 301)
    elif code.startswith("30"):
        return f"{code}.SZ", Market.CHINEXT.value
    # 深市B股 (200)
    elif code.startswith("200"):
        return f"{code}.SZ", Market.BSHARE.value
    # 北交所 (43, 83, 87, 92)
    elif (
        code.startswith("83")
        or code.startswith("87")
        or code.startswith("43")
        or code.startswith("92")
    ):
        return f"{code}.BJ", Market.BSE.value
    # 新三板 (400, 420)
    elif code.startswith("400") or code.startswith("420"):
        return f"{code}.NQ", Market.NQ.value

    return f"{code}.UNKNOWN", "UNKNOWN"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = get_market_symbols(force_update=True)
