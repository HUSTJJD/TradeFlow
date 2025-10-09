# LongPort
## App初始化
```python
config = Config.from_env()
# 行情
quote_ctx = QuoteContext(config)
# 交易
trade_ctx = TradeContext(config)
```

## 行情
### 大盘
#### 历史市场温度
```python
quote_ctx.history_market_temperature(Market.US, datetime.date(2024, 1, 1), datetime.date(2025, 1, 1))
```
#### 当前市场温度
```python
quote_ctx.market_temperature(Market.US)
```
#### 券商席位 id
```python
quote_ctx.participants()
```
#### 轮证发行商 id
```python
quote_ctx.warrant_issuers()
```
#### 各市场当日交易时段
```python
quote_ctx.trading_session()
```
#### 市场交易日
```python
quote_ctx.trading_days(Market.HK, date(2022, 1, 1), date(2022, 2, 1))
```
#### 标的列表
```python
quote_ctx.security_list(Market.US, SecurityListCategory.Overnight)
```
#### 创建自选股分组
```python
quote_ctx.create_watchlist_group(name = "Watchlist1", securities = ["700.HK", "AAPL.US"])
```
#### 删除自选股分组
```python
quote_ctx.delete_watchlist_group(10086)
```
#### 获取自选股分组
```python
quote_ctx.watchlist()
```
#### 更新自选股分组
```python
quote_ctx.update_watchlist_group(10086, name = "WatchList2", securities = ["700.HK", "AAPL.US"], SecuritiesUpdateMode.Replace)
```

### 标的
#### 基础信息
```python
quote_ctx.static_info(["700.HK", "AAPL.US", "TSLA.US", "NFLX.US"])
```
#### 实时行情
```python
quote_ctx.quote(["700.HK", "AAPL.US", "TSLA.US", "NFLX.US"])
```
#### 经纪队列
```python
quote_ctx.brokers("700.HK")
```
#### 盘口
```python
quote_ctx.depth("700.HK")
```
#### 成交明细
```python
quote_ctx.trades("700.HK", 10)
```
#### 当日分时
```python
quote_ctx.intraday("700.HK")
```
#### 历史 K 线
```python
quote_ctx.history_candlesticks_by_offset("700.HK", Period.Day, AdjustType.NoAdjust, True, 10, datetime(2023, 1, 1))
quote_ctx.history_candlesticks_by_offset("700.HK", Period.Day, AdjustType.NoAdjust, False, 10, datetime(2023, 1, 1))
quote_ctx.history_candlesticks_by_date("700.HK", Period.Day, AdjustType.NoAdjust, date(2023, 1, 1), date(2023, 2, 1))
```
#### 当日资金流向
```python
quote_ctx.capital_flow("700.HK")
```
#### 当日资金分布
```python
quote_ctx.capital_distribution("700.HK")
```
#### 计算指标
```python
quote_ctx.calc_indexes(["700.HK", "APPL.US"], [CalcIndex.LastDone, CalcIndex.ChangeRate])
```
#### K 线
```python
quote_ctx.candlesticks("700.HK", Period.Day, 10, AdjustType.NoAdjust)
quote_ctx.candlesticks("700.HK", Period.Day, 10, AdjustType.NoAdjust, trade_session=TradeSessions.All)
```

### 期权
#### 实时行情
```python
quote_ctx.option_quote(["AAPL230317P160000.US"])
```
#### 期权链到期日列表
```python
quote_ctx.option_chain_expiry_date_list("AAPL.US")
```
#### 期权链到期日期权标的列表
```python
quote_ctx.option_chain_info_by_date("AAPL.US", date(2023, 1, 20))
```

### 轮证
#### 实时行情
```python
quote_ctx.warrant_quote(["21125.HK"])
```
#### 轮证筛选列表
```python
quote_ctx.warrant_list("700.HK", WarrantSortBy.LastDone, SortOrderType.Ascending)
```

### 回调
#### 实时价格推送
```python
def on_quote(symbol: str, event: PushQuote):
    print(symbol, event)
quote_ctx.set_on_quote(on_quote)
```
#### 实时盘口推送
```python
def on_depth(symbol: str, event: PushDepth):
    print(symbol, event)
quote_ctx.set_on_depth(on_depth)
```
#### 实时经纪队列推送
```python
def on_brokers(symbol: str, event: PushBrokers):
    print(symbol, event)
quote_ctx.set_on_brokers(on_brokers)
```
#### 实时逐笔成交明细推送
```python
def on_trades(symbol: str, event: PushTrades):
    print(symbol, event)
quote_ctx.set_on_trades(on_trades)
```
#### 订阅行情数据
```python
quote_ctx.subscribe(["700.HK", "AAPL.US"], [SubType.Quote], is_first_push=True)
```
#### 取消订阅行情数据
```python
quote_ctx.unsubscribe(["AAPL.US"], [SubType.Quote])
```
#### 获取已订阅标的行情
```python
quote_ctx.subscriptions()
```

## 交易
### 标的
#### 历史成交明细
```python
trade_ctx.history_executions(
    symbol = "700.HK",
    start_at = datetime(2022, 5, 9),
    end_at = datetime(2022, 5, 12),
)
```
#### 当日成交明细
```python
trade_ctx.today_executions(symbol = "700.HK")
```
#### 保证金比例
```python
trade_ctx.margin_ratio("700.HK")
```
#### 预估最大购买数量
```python
trade_ctx.estimate_max_purchase_quantity(
    symbol = "700.HK",
    order_type = OrderType.LO,
    side = OrderSide.Buy,
)
```
#### 历史订单
```python
trade_ctx.history_orders(
    symbol = "700.HK",
    status = [OrderStatus.Filled, OrderStatus.New],
    side = OrderSide.Buy,
    market = Market.HK,
    start_at = datetime(2022, 5, 9),
    end_at = datetime(2022, 5, 12),
)
```
#### 当日订单
```python
trade_ctx.today_orders(
    symbol = "700.HK",
    status = [OrderStatus.Filled, OrderStatus.New],
    side = OrderSide.Buy,
    market = Market.HK,
)
```
#### 订单详情
```python
trade_ctx.order_detail(
    order_id = "701276261045858304",
)
```
#### 修改订单
```python
trade_ctx.replace_order(
    order_id = "709043056541253632",
    quantity = Decimal(100),
    price = Decimal(50),
)
```
#### 委托下单
```python
trade_ctx.submit_order(
    "700.HK",
    OrderType.LO,
    OrderSide.Buy,
    Decimal(100),
    TimeInForceType.Day,
    submitted_price=Decimal(380),
    remark="Hello from Python SDK",
)
```
#### 撤销订单
```python
trade_ctx.cancel_order("709043056541253632")
```

### 账户
#### 账户资金
```python
trade_ctx.account_balance()
```
#### 资金流水
```python
trade_ctx.cash_flow(start_at=datetime(2022, 5, 9), end_at=datetime(2022, 5, 12))
```
#### 基金持仓
```python
trade_ctx.fund_positions()
```
#### 股票持仓
```python
trade_ctx.stock_positions()
```

### 回调
#### 交易推送
```python
def on_order_changed(event: PushOrderChanged):
    print(event)
trade_ctx.set_on_order_changed(on_order_changed)
```
#### 订阅交易信息
```python
trade_ctx.subscribe([TopicType.Private])
```
#### 取消订阅交易信息
```python
trade_ctx.unsubscribe([TopicType.Private])
```