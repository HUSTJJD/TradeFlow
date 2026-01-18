from qlib.tests.data import GetData
from qlib.cli.data import GetDatax
from datetime import datetime, timedelta
import qlib
# 加载数据
from qlib.data import D
qlib.init(provider_uri="data/qlib_data", region="cn")
GetData().qlib_data(target_dir="data/qlib_data", region="cn", exists_skip=True)

data = D.calendar(start_time=datetime.today()- timedelta(days=365), end_time=datetime.today().strftime('%Y-%m-%d'), freq='day')[:2]
print(data)
# 获取某个市场的所有标的
data = D.instruments(market="all")
# 列出标的
stocks = D.list_instruments(data)
print(len(stocks))
print(data)