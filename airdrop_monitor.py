from app.wallet import Wallet
from web3 import Web3
import time
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class AirdropMonitor:
    def __init__(self, wallet, config_file='airdrop_config.json'):
        """初始化空投监控器"""
        self.wallet = wallet
        self.config_file = config_file
        self.load_config()
        self.w3 = wallet.w3
        
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    'monitored_tokens': [],
                    'last_block': 0,
                    'auto_claim': True,
                    'auto_sell': False,
                    'min_value_to_sell': 0.01  # 最小价值（以BNB计）
                }
                self.save_config()
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            self.config = {
                'monitored_tokens': [],
                'last_block': 0,
                'auto_claim': True,
                'auto_sell': False,
                'min_value_to_sell': 0.01
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
        token_address = self.w3.to_checksum_address(token_address)
        
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
            'initial_balance': 0,
            'last_checked_balance': 0,
            'last_checked_time': int(time.time())
        })
        
        self.save_config()
        print(f"已添加代币 {token_name} ({token_address}) 到监控列表")
    
    def remove_token_from_monitor(self, token_address):
        """从监控列表中移除代币"""
        token_address = self.w3.to_checksum_address(token_address)
        
        self.config['monitored_tokens'] = [
            token for token in self.config['monitored_tokens'] 
            if token['address'].lower() != token_address.lower()
        ]
        
        self.save_config()
        print(f"已从监控列表中移除代币 {token_address}")
    
    def check_token_balances(self):
        """检查所有监控代币的余额"""
        if not self.wallet.account:
            print("请先导入钱包")
            return []
        
        results = []
        current_time = int(time.time())
        
        for token in self.config['monitored_tokens']:
            try:
                token_address = token['address']
                balance_info = self.wallet.get_token_balance(token_address)
                
                previous_balance = token['last_checked_balance']
                current_balance = balance_info['balance']
                
                # 更新代币信息
                token['last_checked_balance'] = current_balance
                token['last_checked_time'] = current_time
                
                # 如果是首次检查，设置初始余额
                if token['initial_balance'] == 0:
                    token['initial_balance'] = current_balance
                
                # 检查是否收到新代币
                if current_balance > previous_balance and previous_balance > 0:
                    received_amount = current_balance - previous_balance
                    received_token_amount = received_amount / (10 ** balance_info['decimals'])
                    
                    print(f"收到 {received_token_amount} 个 {token['name']} 代币!")
                    
                    results.append({
                        'token_address': token_address,
                        'token_name': token['name'],
                        'previous_balance': previous_balance,
                        'current_balance': current_balance,
                        'received_amount': received_amount,
                        'received_token_amount': received_token_amount,
                        'decimals': balance_info['decimals']
                    })
                
            except Exception as e:
                print(f"检查代币 {token['address']} 余额失败: {str(e)}")
        
        self.save_config()
        return results
    
    def monitor_new_airdrops(self, interval=60, max_runs=None):
        """持续监控新的空投"""
        if not self.wallet.account:
            print("请先导入钱包")
            return
        
        print(f"开始监控空投，地址: {self.wallet.account.address}")
        print(f"监控间隔: {interval} 秒")
        print(f"监控代币数量: {len(self.config['monitored_tokens'])}")
        
        run_count = 0
        try:
            while max_runs is None or run_count < max_runs:
                print(f"\n第 {run_count + 1} 次检查...")
                
                # 检查代币余额
                new_airdrops = self.check_token_balances()
                
                # 处理新的空投
                for airdrop in new_airdrops:
                    print(f"处理新空投: {airdrop['token_name']}")
                    
                    # 如果启用了自动认领，这里可以添加认领逻辑
                    if self.config['auto_claim']:
                        self.claim_airdrop(airdrop)
                    
                    # 如果启用了自动卖出，这里可以添加卖出逻辑
                    if self.config['auto_sell']:
                        self.sell_airdrop(airdrop)
                
                # 检查是否有新的代币转入（可能是未监控的空投）
                self.check_for_new_tokens()
                
                run_count += 1
                if max_runs is not None and run_count >= max_runs:
                    break
                
                print(f"等待 {interval} 秒后进行下一次检查...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n监控已停止")
        except Exception as e:
            print(f"监控过程中发生错误: {str(e)}")
        finally:
            self.save_config()
    
    def check_for_new_tokens(self):
        """检查是否有新的代币转入（未监控的空投）"""
        # 这里可以实现扫描钱包中所有代币的逻辑
        # 由于这需要特定的API或索引服务，这里只是一个占位符
        pass
    
    def claim_airdrop(self, airdrop_info):
        """认领空投（如果需要）"""
        print(f"尝试认领空投: {airdrop_info['token_name']}")
        # 大多数空投不需要认领，但有些可能需要调用特定的合约函数
        # 这里是一个示例实现
        try:
            # 这里可以添加特定空投的认领逻辑
            # 例如，调用特定合约的claim函数
            pass
        except Exception as e:
            print(f"认领空投失败: {str(e)}")
    
    def sell_airdrop(self, airdrop_info):
        """卖出空投代币"""
        print(f"尝试卖出空投: {airdrop_info['token_name']}")
        # 这里可以实现通过DEX（如PancakeSwap）卖出代币的逻辑
        # 由于这涉及到与DEX交互，这里只是一个占位符
        try:
            # 这里可以添加卖出代币的逻辑
            pass
        except Exception as e:
            print(f"卖出空投失败: {str(e)}")

# 示例用法
if __name__ == "__main__":
    # 导入钱包
    private_key = input("请输入您的私钥: ")
    use_testnet = input("是否使用测试网? (y/n): ").lower() == 'y'
    
    wallet = Wallet(use_testnet=use_testnet)
    wallet.import_wallet(private_key)
    
    # 创建空投监控器
    monitor = AirdropMonitor(wallet)
    
    # 添加要监控的代币
    token_address = input("请输入要监控的代币地址 (留空跳过): ")
    if token_address:
        monitor.add_token_to_monitor(token_address)
    
    # 开始监控
    interval = int(input("请输入监控间隔 (秒): ") or "60")
    monitor.monitor_new_airdrops(interval=interval)
