from app.wallet import Wallet
from web3 import Web3
import argparse
import json
import time
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

class TokenTransactionMonitor:
    def __init__(self, wallet, config_file='token_monitor_config.json'):
        """初始化代币交易监控器"""
        self.wallet = wallet
        self.w3 = wallet.w3
        self.config_file = config_file
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    'monitored_tokens': [],
                    'last_block': self.w3.eth.block_number,
                    'auto_approve': True,
                    'gas_price_gwei': None
                }
                self.save_config()
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            self.config = {
                'monitored_tokens': [],
                'last_block': self.w3.eth.block_number,
                'auto_approve': True,
                'gas_price_gwei': None
            }
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
    
    def add_token_to_monitor(self, token_address, token_name=None):
        """添加代币到监控列表"""
        token_address = self.wallet.to_checksum_address(token_address)
        
        # 检查代币是否已在监控列表中
        for token in self.config['monitored_tokens']:
            if token['address'].lower() == token_address.lower():
                print(f"代币 {token_address} 已在监控列表中")
                return
        
        # 如果没有提供代币名称，尝试从合约获取
        if not token_name:
            try:
                abi = [
                    {
                        "constant": True,
                        "inputs": [],
                        "name": "name",
                        "outputs": [{"name": "", "type": "string"}],
                        "type": "function"
                    },
                    {
                        "constant": True,
                        "inputs": [],
                        "name": "symbol",
                        "outputs": [{"name": "", "type": "string"}],
                        "type": "function"
                    }
                ]
                token_contract = self.w3.eth.contract(address=token_address, abi=abi)
                token_name = token_contract.functions.name().call()
                token_symbol = token_contract.functions.symbol().call()
                token_name = f"{token_name} ({token_symbol})"
            except Exception as e:
                print(f"获取代币信息失败: {str(e)}")
                token_name = token_address
        
        # 添加代币到监控列表
        self.config['monitored_tokens'].append({
            'address': token_address,
            'name': token_name,
            'last_balance': 0
        })
        
        self.save_config()
        print(f"已添加代币 {token_name} ({token_address}) 到监控列表")
    
    def update_token_balances(self):
        """更新所有监控代币的余额"""
        if not self.wallet.account:
            print("请先导入钱包")
            return
        
        for token in self.config['monitored_tokens']:
            try:
                balance_info = self.wallet.get_token_balance(token['address'])
                token['last_balance'] = balance_info['balance']
                token['decimals'] = balance_info['decimals']
                token['symbol'] = balance_info['symbol']
            except Exception as e:
                print(f"更新代币 {token['address']} 余额失败: {str(e)}")
        
        self.save_config()
    
    def monitor_pending_transactions(self, interval=10, duration=3600):
        """监控待处理的交易"""
        print(f"开始监控待处理交易...")
        print(f"钱包地址: {self.wallet.account.address}")
        print(f"监控间隔: {interval}秒")
        print(f"监控时长: {duration}秒")
        
        start_time = time.time()
        end_time = start_time + duration
        
        # 更新初始余额
        self.update_token_balances()
        
        # 获取当前区块号
        current_block = self.w3.eth.block_number
        self.config['last_block'] = current_block
        self.save_config()
        
        # 监控循环
        try:
            while time.time() < end_time:
                current_time = time.time()
                elapsed = current_time - start_time
                remaining = end_time - current_time
                
                print(f"\n已监控: {int(elapsed)}秒, 剩余: {int(remaining)}秒")
                
                # 获取新区块
                new_block = self.w3.eth.block_number
                if new_block > self.config['last_block']:
                    print(f"检测到新区块: {new_block}, 上次检查的区块: {self.config['last_block']}")
                    
                    # 检查新区块中的交易
                    for block_number in range(self.config['last_block'] + 1, new_block + 1):
                        self.check_block_for_transactions(block_number)
                    
                    # 更新最后检查的区块
                    self.config['last_block'] = new_block
                    self.save_config()
                else:
                    print(f"没有新区块，当前区块: {new_block}")
                
                # 检查代币余额变化
                self.check_token_balance_changes()
                
                # 等待下一次检查
                if time.time() < end_time:
                    print(f"等待 {interval} 秒后进行下一次检查...")
                    time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n监控已手动停止")
        
        print("\n监控结束")
    
    def check_block_for_transactions(self, block_number):
        """检查指定区块中的交易"""
        try:
            print(f"检查区块 {block_number} 中的交易...")
            
            # 获取区块信息
            block = self.w3.eth.get_block(block_number, full_transactions=True)
            
            # 检查区块中的每个交易
            for tx in block.transactions:
                # 检查交易是否与我们的钱包地址相关
                if tx['to'] and tx['to'].lower() == self.wallet.account.address.lower():
                    print(f"发现与钱包相关的交易: {tx.hash.hex()}")
                    self.process_incoming_transaction(tx)
        
        except Exception as e:
            print(f"检查区块 {block_number} 时出错: {str(e)}")
    
    def process_incoming_transaction(self, tx):
        """处理传入的交易"""
        try:
            # 检查交易类型
            if tx['input'] and len(tx['input']) > 2:  # 合约交互
                # 解析交易输入数据
                function_signature = tx['input'][:10]  # 前4个字节（包括0x）是函数签名
                
                # 检查是否是代币转账（ERC20 transfer函数签名为0xa9059cbb）
                if function_signature == '0xa9059cbb':
                    # 解析transfer函数参数
                    data = tx['input'][10:]  # 去掉函数签名
                    # 第一个参数是地址（32字节）
                    to_address = '0x' + data[:64][-40:]  # 取最后20字节并添加0x前缀
                    # 第二个参数是金额（32字节）
                    amount = int(data[64:128], 16)
                    
                    print(f"检测到代币转账: 从 {tx['from']} 到 {to_address}, 金额: {amount}")
                    
                    # 如果接收地址是我们的钱包地址，这是一个传入的代币转账
                    if to_address.lower() == self.wallet.account.address.lower():
                        print(f"接收到代币转账!")
                        # 这里可以添加自动处理逻辑
                
                # 检查是否是代币授权（ERC20 approve函数签名为0x095ea7b3）
                elif function_signature == '0x095ea7b3':
                    # 解析approve函数参数
                    data = tx['input'][10:]
                    # 第一个参数是被授权地址
                    spender = '0x' + data[:64][-40:]
                    # 第二个参数是授权金额
                    amount = int(data[64:128], 16)
                    
                    print(f"检测到代币授权: 授权 {spender} 使用 {amount} 代币")
                    
                    # 如果我们的钱包是授权者，这是一个传出的授权
                    if tx['from'].lower() == self.wallet.account.address.lower():
                        print(f"发出代币授权!")
                        # 这里可以添加自动处理逻辑
            
            # 如果是普通ETH/BNB转账
            elif not tx['input'] or tx['input'] == '0x':
                value = tx['value']
                print(f"检测到ETH/BNB转账: 从 {tx['from']} 到 {tx['to']}, 金额: {self.w3.from_wei(value, 'ether')}")
        
        except Exception as e:
            print(f"处理交易时出错: {str(e)}")
    
    def check_token_balance_changes(self):
        """检查代币余额变化"""
        for token in self.config['monitored_tokens']:
            try:
                # 获取当前余额
                balance_info = self.wallet.get_token_balance(token['address'])
                current_balance = balance_info['balance']
                
                # 如果余额发生变化
                if current_balance != token['last_balance']:
                    change = current_balance - token['last_balance']
                    change_formatted = change / (10 ** balance_info['decimals'])
                    
                    if change > 0:
                        print(f"代币 {token['name']} 余额增加: +{change_formatted} {balance_info['symbol']}")
                        # 这里可以添加自动处理逻辑
                    else:
                        print(f"代币 {token['name']} 余额减少: {change_formatted} {balance_info['symbol']}")
                    
                    # 更新余额
                    token['last_balance'] = current_balance
                    self.save_config()
            
            except Exception as e:
                print(f"检查代币 {token['address']} 余额变化时出错: {str(e)}")
    
    def auto_approve_token(self, token_address, spender_address, amount=None):
        """自动授权代币使用权"""
        if not self.wallet.account:
            print("请先导入钱包")
            return False
        
        try:
            token_address = self.wallet.to_checksum_address(token_address)
            spender_address = self.wallet.to_checksum_address(spender_address)
            
            # 创建代币合约实例
            abi = [
                {
                    "constant": False,
                    "inputs": [
                        {"name": "_spender", "type": "address"},
                        {"name": "_value", "type": "uint256"}
                    ],
                    "name": "approve",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                }
            ]
            token_contract = self.w3.eth.contract(address=token_address, abi=abi)
            
            # 如果没有指定金额，则授权最大金额
            if amount is None:
                amount = 2**256 - 1  # 最大uint256值
            else:
                # 获取代币精度
                decimals = token_contract.functions.decimals().call()
                # 转换金额为代币最小单位
                amount = int(amount * (10 ** decimals))
            
            # 准备交易数据
            tx_data = token_contract.functions.approve(
                spender_address,
                amount
            ).build_transaction({
                'chainId': self.wallet.chain_id,
                'gas': 100000,
                'nonce': self.w3.eth.get_transaction_count(self.wallet.account.address)
            })
            
            # 设置Gas价格
            if self.config['gas_price_gwei']:
                tx_data['gasPrice'] = self.w3.to_wei(self.config['gas_price_gwei'], 'gwei')
            else:
                tx_data['gasPrice'] = self.w3.eth.gas_price
            
            # 签名交易
            signed_tx = self.w3.eth.account.sign_transaction(tx_data, self.wallet.account.key)
            
            # 发送交易
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"授权交易已提交，交易哈希: {tx_hash.hex()}")
            
            # 等待交易确认
            print("等待交易确认...")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                print(f"授权成功! 已授权 {spender_address} 使用 {token_address} 代币")
                return True
            else:
                print("授权交易失败!")
                return False
            
        except Exception as e:
            print(f"授权代币时出错: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='自动代币接收和交易监控工具')
    
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
    
    # 监控交易命令
    monitor_parser = subparsers.add_parser('monitor', help='监控交易')
    monitor_parser.add_argument('--interval', '-i', type=int, default=10, help='监控间隔（秒）')
    monitor_parser.add_argument('--duration', '-d', type=int, default=3600, help='监控时长（秒）')
    monitor_parser.add_argument('--private-key', '-k', required=True, help='钱包私钥')
    monitor_parser.add_argument('--testnet', action='store_true', help='使用测试网')
    monitor_parser.add_argument('--gas-price', '-g', type=float, help='Gas价格（Gwei）')
    
    # 授权代币命令
    approve_parser = subparsers.add_parser('approve', help='授权代币')
    approve_parser.add_argument('--token', '-t', required=True, help='代币合约地址')
    approve_parser.add_argument('--spender', '-s', required=True, help='被授权地址')
    approve_parser.add_argument('--amount', '-a', type=float, help='授权金额（不指定则授权最大金额）')
    approve_parser.add_argument('--private-key', '-k', required=True, help='钱包私钥')
    approve_parser.add_argument('--testnet', action='store_true', help='使用测试网')
    approve_parser.add_argument('--gas-price', '-g', type=float, help='Gas价格（Gwei）')
    
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
    
    # 创建监控器
    monitor = TokenTransactionMonitor(wallet)
    
    # 设置Gas价格
    if hasattr(args, 'gas_price') and args.gas_price:
        monitor.config['gas_price_gwei'] = args.gas_price
        monitor.save_config()
    
    # 执行命令
    if args.command == 'import':
        # 钱包已导入，无需额外操作
        pass
    
    elif args.command == 'add':
        monitor.add_token_to_monitor(args.token, args.name)
    
    elif args.command == 'monitor':
        monitor.monitor_pending_transactions(interval=args.interval, duration=args.duration)
    
    elif args.command == 'approve':
        monitor.auto_approve_token(args.token, args.spender, args.amount)

if __name__ == "__main__":
    main()
