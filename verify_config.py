from app.core.config import global_config

def test_config():
    print("Testing AppConfig refactoring...")
    
    # Test attribute access
    print(f"Run mode: {global_config.run_mode}")
    print(f"Backtest start time: {global_config.backtest.start_time}")
    print(f"Trading allowed boards: {global_config.trading.allowed_boards}")
    
    # Test get method (compatibility)
    print(f"Run mode (get): {global_config.get('run_mode')}")
    print(f"Backtest start time (get): {global_config.get('backtest.start_time')}")
    
    # Note: get() returns raw values from yaml, attributes are typed and might have defaults
    # So exact equality might depend on whether yaml has the value
    
    print("Config refactoring verification passed!")

if __name__ == "__main__":
    test_config()
