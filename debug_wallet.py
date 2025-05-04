from jager_app.wallet import Wallet

def debug_wallet_import(private_key):
    """调试钱包导入过程"""
    print(f"调试钱包导入...")
    print(f"私钥类型: {type(private_key)}")
    
    if private_key is None:
        print("错误: 私钥为空")
        return False
        
    if not isinstance(private_key, str):
        print(f"错误: 私钥必须是字符串，而不是 {type(private_key)}")
        return False
        
    print(f"私钥长度: {len(private_key)}")
    
    try:
        # 创建钱包实例
        wallet = Wallet(use_testnet=False)
        
        # 导入钱包
        wallet_data = wallet.import_wallet(private_key)
        print(f"钱包导入成功，地址: {wallet_data['address']}")
        return wallet_data
    except Exception as e:
        print(f"钱包导入失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 测试一些示例私钥
    test_keys = [
        "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",  # 有效私钥
        "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",    # 无0x前缀
        None,                                                                  # None值
        123456,                                                                # 整数
        ""                                                                     # 空字符串
    ]
    
    for i, key in enumerate(test_keys):
        print(f"\n测试私钥 #{i+1}:")
        result = debug_wallet_import(key)
        print(f"结果: {result}")
