import argparse
from app.wallet import Wallet
from airdrop_monitor import AirdropMonitor
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='自动接收代币和获取空投工具')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 导入钱包命令
    import_parser = subparsers.add_parser('import', help='导入钱包')
    import_parser.add_argument('--private-key', '-k', required=True, help='钱包私钥')
    import_parser.add_argument('--testnet', '-t', action='store_true', help='使用测试网')
    
    # 添加监控代币命令
    add_parser = subparsers.add_parser('add', help='添加监控代币')
    add_parser.add_argument('--token', '-t', required=True, help='代币合约地址')
    add_parser.add_argument('--name', '-n', help='代币名称（可选）')
    add_parser.add_argument('--private-key', '-k', required=True, help='钱包私钥')
    add_parser.add_argument('--testnet', action='store_true', help='使用测试网')
    
    # 移除监控代币命令
    remove_parser = subparsers.add_parser('remove', help='移除监控代币')
    remove_parser.add_argument('--token', '-t', required=True, help='代币合约地址')
    remove_parser.add_argument('--private-key', '-k', required=True, help='钱包私钥')
    remove_parser.add_argument('--testnet', action='store_true', help='使用测试网')
    
    # 查看监控代币命令
    list_parser = subparsers.add_parser('list', help='查看监控代币')
    list_parser.add_argument('--private-key', '-k', required=True, help='钱包私钥')
    list_parser.add_argument('--testnet', action='store_true', help='使用测试网')
    
    # 检查代币余额命令
    check_parser = subparsers.add_parser('check', help='检查代币余额')
    check_parser.add_argument('--token', '-t', help='代币合约地址（可选，不提供则检查所有监控代币）')
    check_parser.add_argument('--private-key', '-k', required=True, help='钱包私钥')
    check_parser.add_argument('--testnet', action='store_true', help='使用测试网')
    
    # 开始监控命令
    monitor_parser = subparsers.add_parser('monitor', help='开始监控空投')
    monitor_parser.add_argument('--interval', '-i', type=int, default=60, help='监控间隔（秒）')
    monitor_parser.add_argument('--private-key', '-k', required=True, help='钱包私钥')
    monitor_parser.add_argument('--testnet', action='store_true', help='使用测试网')
    monitor_parser.add_argument('--auto-claim', '-c', action='store_true', help='自动认领空投')
    monitor_parser.add_argument('--auto-sell', '-s', action='store_true', help='自动卖出空投')
    
    # 解析参数
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 创建钱包实例
    wallet = Wallet(use_testnet=args.testnet if hasattr(args, 'testnet') else False)
    
    # 导入钱包
    if hasattr(args, 'private_key') and args.private_key:
        try:
            wallet_data = wallet.import_wallet(args.private_key)
            print(f"钱包导入成功，地址: {wallet_data['address']}")
        except Exception as e:
            print(f"钱包导入失败: {str(e)}")
            return
    
    # 创建空投监控器
    monitor = AirdropMonitor(wallet)
    
    # 执行命令
    if args.command == 'import':
        # 钱包已导入，无需额外操作
        pass
    
    elif args.command == 'add':
        monitor.add_token_to_monitor(args.token, args.name)
    
    elif args.command == 'remove':
        monitor.remove_token_from_monitor(args.token)
    
    elif args.command == 'list':
        if not monitor.config['monitored_tokens']:
            print("监控列表为空")
        else:
            print("监控代币列表:")
            for i, token in enumerate(monitor.config['monitored_tokens']):
                print(f"{i+1}. {token['name']} ({token['address']})")
                print(f"   初始余额: {token['initial_balance']}")
                print(f"   最后检查余额: {token['last_checked_balance']}")
                print(f"   最后检查时间: {token['last_checked_time']}")
                print()
    
    elif args.command == 'check':
        if args.token:
            # 检查特定代币
            try:
                balance_info = wallet.get_token_balance(args.token)
                print(f"代币地址: {balance_info['token_address']}")
                print(f"代币符号: {balance_info['symbol']}")
                print(f"余额: {balance_info['balance_token']} ({balance_info['balance']})")
            except Exception as e:
                print(f"检查代币余额失败: {str(e)}")
        else:
            # 检查所有监控代币
            results = monitor.check_token_balances()
            if results:
                print("检测到新的代币接收:")
                for result in results:
                    print(f"代币: {result['token_name']}")
                    print(f"接收数量: {result['received_token_amount']}")
                    print()
            else:
                print("没有检测到新的代币接收")
    
    elif args.command == 'monitor':
        # 设置自动认领和自动卖出选项
        if hasattr(args, 'auto_claim'):
            monitor.config['auto_claim'] = args.auto_claim
        if hasattr(args, 'auto_sell'):
            monitor.config['auto_sell'] = args.auto_sell
        monitor.save_config()
        
        # 开始监控
        monitor.monitor_new_airdrops(interval=args.interval)

if __name__ == "__main__":
    main()
