from app.wallet import Wallet
import time
import argparse
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# JagerHunter代币合约地址
JAGER_CONTRACT = "0x74836cc0e821a6be18e407e6388e430b689c66e9"

def monitor_jager_token(wallet, interval=60, duration=3600):
    """监控JagerHunter代币的接收情况"""
    print(f"开始监控JagerHunter代币，地址: {JAGER_CONTRACT}")
    print(f"钱包地址: {wallet.account.address}")
    print(f"监控间隔: {interval}秒")
    print(f"监控时长: {duration}秒")
    
    start_time = time.time()
    end_time = start_time + duration
    
    # 获取初始余额
    try:
        initial_balance_info = wallet.get_token_balance(JAGER_CONTRACT)
        initial_balance = initial_balance_info['balance']
        decimals = initial_balance_info['decimals']
        symbol = initial_balance_info['symbol']
        
        print(f"初始{symbol}余额: {initial_balance / (10 ** decimals)}")
    except Exception as e:
        print(f"获取初始余额失败: {str(e)}")
        initial_balance = 0
        decimals = 18
        symbol = "JAGER"
    
    # 监控循环
    try:
        while time.time() < end_time:
            current_time = time.time()
            elapsed = current_time - start_time
            remaining = end_time - current_time
            
            print(f"\n已监控: {int(elapsed)}秒, 剩余: {int(remaining)}秒")
            
            try:
                # 获取当前余额
                balance_info = wallet.get_token_balance(JAGER_CONTRACT)
                current_balance = balance_info['balance']
                
                # 计算接收的代币数量
                received = current_balance - initial_balance
                
                if received > 0:
                    received_tokens = received / (10 ** decimals)
                    print(f"已接收 {received_tokens} 个 {symbol}!")
                    print(f"当前余额: {current_balance / (10 ** decimals)} {symbol}")
                    
                    # 更新初始余额，以便检测新的接收
                    initial_balance = current_balance
                else:
                    print(f"当前余额: {current_balance / (10 ** decimals)} {symbol}, 未接收新代币")
            
            except Exception as e:
                print(f"检查余额失败: {str(e)}")
            
            # 等待下一次检查
            if time.time() < end_time:
                print(f"等待 {interval} 秒后进行下一次检查...")
                time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n监控已手动停止")
    
    # 最终余额检查
    try:
        final_balance_info = wallet.get_token_balance(JAGER_CONTRACT)
        final_balance = final_balance_info['balance']
        total_received = final_balance - initial_balance
        
        print("\n监控结束")
        print(f"最终{symbol}余额: {final_balance / (10 ** decimals)}")
        if total_received > 0:
            print(f"总共接收: {total_received / (10 ** decimals)} {symbol}")
        else:
            print("未接收任何代币")
    except Exception as e:
        print(f"获取最终余额失败: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='自动接收JagerHunter代币工具')
    parser.add_argument('--private-key', '-k', required=True, help='钱包私钥')
    parser.add_argument('--testnet', '-t', action='store_true', help='使用测试网')
    parser.add_argument('--interval', '-i', type=int, default=60, help='监控间隔（秒）')
    parser.add_argument('--duration', '-d', type=int, default=3600, help='监控时长（秒）')
    
    args = parser.parse_args()
    
    # 创建钱包实例
    wallet = Wallet(use_testnet=args.testnet)
    
    # 导入钱包
    try:
        wallet_data = wallet.import_wallet(args.private_key)
        print(f"钱包导入成功，地址: {wallet_data['address']}")
    except Exception as e:
        print(f"钱包导入失败: {str(e)}")
        return
    
    # 开始监控
    monitor_jager_token(wallet, interval=args.interval, duration=args.duration)

if __name__ == "__main__":
    main()
