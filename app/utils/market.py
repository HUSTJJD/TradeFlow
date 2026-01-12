from app.core import global_config, Market

def get_stacks_in_all_market():
    stacks = []
    markets_config = global_config.get(f"trading.markets", [])
    for market, market_config in markets_config:
        if market == Market.SSE_MAIN:
            pass
        elif market == Market.SSE_STAR:
            pass
        elif market == Market.SZSE_MAIN:
            pass
        elif market == Market.SZSE_GEM:
            pass
        elif market == Market.HKCONNECT:
            pass
    return stacks
