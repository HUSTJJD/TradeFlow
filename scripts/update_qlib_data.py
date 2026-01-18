from qlib.tests.data import GetData

if __name__ == "__main__":
    GetData().qlib_data(target_dir="data/qlib_data/cn_data", region="cn")
    GetData().qlib_data(target_dir="data/qlib_data/cn_data_1min", region="cn", interval="1min")
    GetData().qlib_data(target_dir="data/qlib_data/us_data", region="us")

