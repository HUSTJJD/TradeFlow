import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import akshare as ak
from app.core import MarketType

logger = logging.getLogger(__name__)

def update_market_qlib_datas() -> None:
    logger.info("更新市场数据的功能尚未实现。")
    pass

def update_market_symbols() -> pd.DataFrame:
    """
    获取全市场标的（A股 + 港股通），支持本地缓存和定期更新。
    """
    file_path = "data/market_symbols.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if os.path.exists(file_path):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        if datetime.now() - file_mtime < timedelta(days=30):
            return pd.read_csv(file_path)
    logger.info("开始更新市场标的数据...")
    df = _fetch_and_merge_data()
    df.to_csv(file_path, index=False)
    logger.info(f"市场标的数据已更新并保存至: {file_path}, 共 {len(df)} 条")
    return df


def _fetch_and_merge_data() -> pd.DataFrame:
    """
    从 AkShare 获取数据并合并
    """
    stock_sh = ak.stock_info_sh_name_code(symbol="主板A股")
    stock_sh = stock_sh[["证券代码", "证券简称", "上市日期"]]
    stock_sh = stock_sh.rename(columns={"证券代码": "symbol", "证券简称": "name", "上市日期": "date"})
    stock_kcb = ak.stock_info_sh_name_code(symbol="科创板")
    stock_kcb = stock_kcb[["证券代码", "证券简称", "上市日期"]]
    stock_kcb = stock_kcb.rename(columns={"证券代码": "symbol", "证券简称": "name", "上市日期": "date"})
    stock_sz = ak.stock_info_sz_name_code(symbol="A股列表")
    stock_sz = stock_sz[["A股代码", "A股简称", "A股上市日期", "所属行业"]]
    stock_sz = stock_sz.rename(columns={"A股代码": "symbol", "A股简称": "name", "A股上市日期": "date", "所属行业": "industry"})
    stock_bse = ak.stock_info_bj_name_code()
    stock_bse = stock_bse[["证券代码", "证券简称", "上市日期", "所属行业"]]
    stock_bse = stock_bse.rename(columns={"证券代码": "symbol", "证券简称": "name", "上市日期": "date", "所属行业": "industry"})
    df_all = pd.concat([stock_sh, stock_kcb, stock_sz, stock_bse], ignore_index=True)
    df_all[["symbol", "board"]] = df_all["symbol"].apply(
        lambda x: pd.Series(_get_a_share_symbol_and_board(x))
    )
    stock_hk = ak.stock_hk_ggt_components_em()
    stock_hk = stock_hk[["代码", "名称"]]
    stock_hk = stock_hk.rename(columns={"代码": "symbol", "名称": "name"})
    stock_hk["symbol"] = stock_hk["symbol"].apply(lambda x: f"{x}.HK")
    stock_hk["board"] = MarketType.HK.value
    df_all = pd.concat([df_all, stock_hk], ignore_index=True)
    return df_all


def _get_a_share_symbol_and_board(code: str) -> tuple[str, str]:
    code = str(code)
    # 沪市主板 (600, 601, 603, 605)
    if code.startswith("60"):
        return f"{code}.SH", MarketType.MAIN.value
    # 沪市科创板 (688, 689)
    elif code.startswith("68"):
        return f"{code}.SH", MarketType.STAR.value
    # 沪市B股 (900)
    elif code.startswith("900"):
        return f"{code}.SH", MarketType.BSHARE.value
    # 深市主板 (000, 001, 002, 003)
    elif code.startswith("00"):
        return f"{code}.SZ", MarketType.MAIN.value
    # 深市创业板 (300, 301)
    elif code.startswith("30"):
        return f"{code}.SZ", MarketType.CHINEXT.value
    # 深市B股 (200)
    elif code.startswith("200"):
        return f"{code}.SZ", MarketType.BSHARE.value
    # 北交所 (43, 83, 87, 92)
    elif (
        code.startswith("83")
        or code.startswith("87")
        or code.startswith("43")
        or code.startswith("92")
    ):
        return f"{code}.BJ", MarketType.BSE.value
    # 新三板 (400, 420)
    elif code.startswith("400") or code.startswith("420"):
        return f"{code}.NQ", MarketType.NQ.value

    return f"{code}.UNKNOWN", "UNKNOWN"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = update_market_symbols()
