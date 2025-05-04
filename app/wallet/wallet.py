from web3 import Web3
from eth_account import Account
import os
import json
import secrets
from web3.exceptions import InvalidAddress

class Wallet:
    def __init__(self, rpc_url=None, chain_id=None, use_testnet=False):
        """初始化钱包，连接到BSC网络"""
        if use_testnet:
            self.rpc_url = os.getenv('BSC_TESTNET_RPC_URL')
            self.chain_id = int(os.getenv('BSC_TESTNET_CHAIN_ID'))
        else:
            self.rpc_url = rpc_url or os.getenv('BSC_RPC_URL')
            self.chain_id = chain_id or int(os.getenv('BSC_CHAIN_ID'))

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"无法连接到BSC网络: {self.rpc_url}")

        self.account = None
        self.wallet_file = 'wallet.json'

    def to_checksum_address(self, address):
        """将地址转换为校验和地址格式"""
        try:
            # 如果地址已经是校验和格式，直接返回
            if self.w3.is_checksum_address(address):
                return address
            # 否则转换为校验和格式
            return self.w3.to_checksum_address(address)
        except InvalidAddress:
            raise ValueError(f"无效的地址格式: {address}")

    def create_wallet(self):
        """创建新钱包"""
        # 生成随机私钥
        private_key = "0x" + secrets.token_hex(32)
        self.account = Account.from_key(private_key)
        return {
            'address': self.account.address,
            'private_key': private_key
        }

    def import_wallet(self, private_key):
        """通过私钥导入钱包"""
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key

        try:
            self.account = Account.from_key(private_key)
            return {
                'address': self.account.address,
                'private_key': private_key
            }
        except Exception as e:
            raise ValueError(f"导入钱包失败: {str(e)}")

    def get_bnb_balance(self, address=None):
        """获取BNB余额"""
        if not address and not self.account:
            raise ValueError("请提供地址或先导入钱包")

        # 转换为校验和地址格式
        addr = address or self.account.address
        addr = self.to_checksum_address(addr)

        balance_wei = self.w3.eth.get_balance(addr)
        balance_bnb = self.w3.from_wei(balance_wei, 'ether')

        return {
            'address': addr,
            'balance_wei': balance_wei,
            'balance_bnb': balance_bnb
        }

    def get_token_balance(self, token_address, address=None):
        """获取代币余额"""
        if not address and not self.account:
            raise ValueError("请提供地址或先导入钱包")

        # 转换为校验和地址格式
        addr = address or self.account.address
        addr = self.to_checksum_address(addr)
        token_address = self.to_checksum_address(token_address)

        # ERC20代币ABI
        abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
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

        # 创建合约实例
        token_contract = self.w3.eth.contract(address=token_address, abi=abi)

        # 获取代币信息
        try:
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
            balance = token_contract.functions.balanceOf(addr).call()
            balance_token = balance / (10 ** decimals)

            return {
                'address': addr,
                'token_address': token_address,
                'symbol': symbol,
                'balance': balance,
                'balance_token': balance_token,
                'decimals': decimals
            }
        except Exception as e:
            raise ValueError(f"获取代币余额失败: {str(e)}")

    def transfer_bnb(self, to_address, amount_bnb, gas_price=None, gas_limit=21000):
        """转账BNB"""
        if not self.account:
            raise ValueError("请先导入钱包")

        # 转换为校验和地址格式
        to_address = self.to_checksum_address(to_address)

        amount_wei = self.w3.to_wei(amount_bnb, 'ether')

        # 检查余额
        balance = self.w3.eth.get_balance(self.account.address)
        if balance < amount_wei:
            raise ValueError(f"余额不足. 当前余额: {self.w3.from_wei(balance, 'ether')} BNB")

        # 准备交易
        tx = {
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'to': to_address,
            'value': amount_wei,
            'gas': gas_limit,
            'chainId': self.chain_id
        }

        if gas_price:
            tx['gasPrice'] = self.w3.to_wei(gas_price, 'gwei')
        else:
            tx['gasPrice'] = self.w3.eth.gas_price

        # 签名交易
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)

        # 发送交易
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return {
            'transaction_hash': tx_hash.hex(),
            'from': self.account.address,
            'to': to_address,
            'amount_bnb': amount_bnb,
            'amount_wei': amount_wei
        }

    def transfer_token(self, token_address, to_address, amount, gas_price=None, gas_limit=100000):
        """转账代币"""
        if not self.account:
            raise ValueError("请先导入钱包")

        # 转换为校验和地址格式
        to_address = self.to_checksum_address(to_address)
        token_address = self.to_checksum_address(token_address)

        # ERC20代币ABI
        abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]

        # 创建合约实例
        token_contract = self.w3.eth.contract(address=token_address, abi=abi)

        # 获取代币精度
        decimals = token_contract.functions.decimals().call()

        # 转换金额为代币最小单位
        amount_in_smallest_unit = int(amount * (10 ** decimals))

        # 检查代币余额
        token_balance = token_contract.functions.balanceOf(self.account.address).call()
        if token_balance < amount_in_smallest_unit:
            raise ValueError(f"代币余额不足. 当前余额: {token_balance / (10 ** decimals)}")

        # 准备交易数据
        tx_data = token_contract.functions.transfer(
            to_address,
            amount_in_smallest_unit
        ).build_transaction({
            'chainId': self.chain_id,
            'gas': gas_limit,
            'nonce': self.w3.eth.get_transaction_count(self.account.address)
        })

        if gas_price:
            tx_data['gasPrice'] = self.w3.to_wei(gas_price, 'gwei')
        else:
            tx_data['gasPrice'] = self.w3.eth.gas_price

        # 签名交易
        signed_tx = self.w3.eth.account.sign_transaction(tx_data, self.account.key)

        # 发送交易
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return {
            'transaction_hash': tx_hash.hex(),
            'from': self.account.address,
            'to': to_address,
            'token_address': token_address,
            'amount': amount,
            'amount_in_smallest_unit': amount_in_smallest_unit
        }

    def interact_with_contract(self, contract_address, contract_abi, function_name, function_args=None, value=0):
        """与智能合约交互"""
        if not self.account:
            raise ValueError("请先导入钱包")

        if function_args is None:
            function_args = []

        # 转换为校验和地址格式
        contract_address = self.to_checksum_address(contract_address)

        # 处理函数参数中的地址
        processed_args = []
        for arg in function_args:
            if isinstance(arg, str) and arg.startswith('0x') and len(arg) == 42:
                # 如果参数看起来像是地址，则转换为校验和格式
                try:
                    processed_args.append(self.to_checksum_address(arg))
                except ValueError:
                    # 如果转换失败，保持原样
                    processed_args.append(arg)
            else:
                processed_args.append(arg)

        # 创建合约实例
        contract = self.w3.eth.contract(address=contract_address, abi=contract_abi)

        # 获取合约函数
        contract_function = getattr(contract.functions, function_name)

        # 检查函数是否为只读函数
        try:
            # 尝试调用函数（只读）
            result = contract_function(*processed_args).call()
            return {
                'type': 'read',
                'result': result
            }
        except Exception:
            # 如果调用失败，则尝试发送交易
            try:
                # 准备交易数据
                tx_data = contract_function(*processed_args).build_transaction({
                    'chainId': self.chain_id,
                    'gas': 200000,  # 默认gas限制
                    'nonce': self.w3.eth.get_transaction_count(self.account.address),
                    'value': self.w3.to_wei(value, 'ether') if value > 0 else 0
                })

                # 签名交易
                signed_tx = self.w3.eth.account.sign_transaction(tx_data, self.account.key)

                # 发送交易
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

                return {
                    'type': 'write',
                    'transaction_hash': tx_hash.hex(),
                    'from': self.account.address,
                    'to': contract_address,
                    'function': function_name,
                    'args': function_args,
                    'value': value
                }
            except Exception as e:
                raise ValueError(f"合约交互失败: {str(e)}")
