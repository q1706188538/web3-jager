from jager_app.wallet import Wallet
from web3 import Web3
import argparse
import json
import time
import requests
import os
import sys
from dotenv import load_dotenv

# 不再尝试导入POA中间件，因为本地环境不需要也能正常工作

# 加载环境变量
load_dotenv()

# JagerHunter代币合约地址
JAGER_TOKEN_CONTRACT = "0x74836cc0e821a6be18e407e6388e430b689c66e9"  # 代币合约地址

# Jager空投合约地址
AIRDROP_CONTRACT = "0xDF6dbd6d4069bF0c9450538238A9643C72E4a6E4"  # 最新的空投合约地址

class JagerAirdropClaimer:
    def __init__(self, wallet, use_testnet=False):
        """初始化空投领取器"""
        self.wallet = wallet
        self.w3 = wallet.w3

        # 设置默认gas限制
        self.gas_limit = 300000  # Jager代币转账的默认gas限制
        self.bnb_gas_limit = 21000  # BNB转账的默认gas限制
        self.claim_gas_limit = 1000000  # 空投领取的默认gas限制

        # 不使用POA中间件
        print("不使用POA中间件，直接处理交易数据")

        # 初始化API数据
        self.api_amount = int(7300000000 * 10**18)  # 默认使用正确的空投数量
        self.api_deadline = None  # 将从API获取deadline值

        # 设置交易确认超时时间（如果支持）
        try:
            # 较新版本的Web3.py
            self.w3.eth.set_transaction_wait_timeout(120)
            print("已设置交易确认超时时间")
        except AttributeError:
            # 较旧版本的Web3.py不支持此方法
            print("注意: 您的Web3.py版本不支持设置交易确认超时时间")

        self.use_testnet = use_testnet

        # 加载空投合约ABI
        self.airdrop_abi = self.load_airdrop_abi()

        # 加载代币合约ABI
        self.token_abi = self.load_token_abi()

    def load_airdrop_abi(self):
        """加载空投合约ABI"""
        # 只使用Jager特定的claim函数 - 从BSC浏览器交易记录中提取
        return [
            {
                "inputs": [
                    {"type": "address", "name": "account"},
                    {"type": "uint256", "name": "amount"},
                    {"type": "uint256", "name": "deadline"},
                    {"type": "bytes", "name": "sign"},
                    {"type": "bool", "name": "instant"},
                    {"type": "address", "name": "invitor"}
                ],
                "name": "claim",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]

    def load_token_abi(self):
        """加载代币合约ABI"""
        return [
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
            },
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            },
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
                "inputs": [
                    {"name": "_owner", "type": "address"},
                    {"name": "_spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]

    def check_eligibility(self):
        """检查是否有资格领取空投"""
        if not AIRDROP_CONTRACT:
            print("错误: 未设置空投合约地址")
            return False

        try:
            # 首先检查代币余额，如果已经有代币，可能已经领取过
            balance_info = self.get_token_balance()
            if balance_info['balance'] > 0:
                print(f"警告: 钱包中已有 {balance_info['balance_token']} 个 {balance_info['symbol']} 代币，可能已经领取过空投")

                # 尝试查询API，检查是否已领取
                try:
                    # 获取钱包地址签名
                    wallet_signature = self.get_wallet_signature()

                    # 准备请求数据
                    data = {
                        "address": self.wallet.account.address,
                        "solAddress": "",
                        "signStr": wallet_signature,
                        "solSignStr": ""
                    }

                    # 发送请求到Jager API
                    url = "https://api.jager.meme/api/airdrop/claimAirdrop"
                    print(f"发送请求到: {url}")
                    print(f"请求数据: {json.dumps(data)}")

                    response = requests.post(url, json=data, timeout=30)
                    print(f"API响应状态码: {response.status_code}")

                    if response.status_code == 200:
                        result = response.json()
                        print(f"API响应: {json.dumps(result)}")

                        # 检查API响应中是否有已领取的提示
                        if "message" in result and ("claimed" in result["message"].lower() or "已领取" in result["message"]):
                            print(f"API确认: 已经领取过空投")
                            return False
                except Exception as api_error:
                    print(f"查询API时出错: {str(api_error)}")

            # 由于我们只有claim函数，无法直接检查资格
            # 我们假设用户有资格领取，直接尝试领取
            print(f"无法确定资格状态，将尝试领取空投。")
            print(f"钱包地址: {self.wallet.account.address}")
            print(f"预期空投数量: 7,300,000,000 JAGER")
            return True
        except Exception as e:
            print(f"检查资格时出错: {str(e)}")
            return False



    def claim_airdrop(self, gas_price=None, gas_limit=None):
        """领取空投"""
        if not AIRDROP_CONTRACT:
            print("错误: 未设置空投合约地址")
            return False

        # 如果提供了gas_limit，更新实例的claim_gas_limit
        if gas_limit:
            self.claim_gas_limit = int(gas_limit)
            print(f"使用自定义gas限制: {self.claim_gas_limit}")

        try:
            # 检查资格
            try:
                if not self.check_eligibility():
                    print("继续尝试领取，即使资格检查失败...")
            except Exception as e:
                print(f"资格检查失败，但将继续尝试领取: {str(e)}")

            # 创建空投合约实例
            airdrop_contract = self.w3.eth.contract(
                address=self.wallet.to_checksum_address(AIRDROP_CONTRACT),
                abi=self.airdrop_abi
            )

            # 获取当前代币余额（用于后续比较）
            initial_balance = self.get_token_balance()

            # 获取签名
            signature = self.get_claim_signature()
            if signature is None:
                print("错误: 无法获取有效的签名，无法继续")
                return False

            # 如果没有deadline值，无法继续
            if self.api_deadline is None:
                print("错误: 无法获取有效的deadline值，无法继续")
                return False

            # 只使用Jager特定的claim函数
            claim_functions = [
                {"name": "claim", "args": [
                    self.wallet.account.address,  # account
                    self.api_amount if self.api_amount else int(7300000000 * 10**18),  # 使用正确的空投数量
                    self.api_deadline,  # 使用API返回的原始deadline值
                    signature,  # 使用获取到的签名
                    True,  # instant
                    self.wallet.to_checksum_address("0x6f037D508A58227105B7ed1e450C7450867256DA")  # invitor (指定的邀请人地址)
                ]}
            ]

            success = False
            for func in claim_functions:
                try:
                    print(f"尝试调用 {func['name']}")
                    print(f"参数:")
                    print(f"  account: {func['args'][0]}")
                    print(f"  amount: {func['args'][1]}")
                    print(f"  deadline: {func['args'][2]}")
                    print(f"  sign: {func['args'][3]}")
                    print(f"  instant: {func['args'][4]}")
                    print(f"  invitor: {func['args'][5]}")

                    # 获取函数对象
                    contract_func = getattr(airdrop_contract.functions, func["name"])

                    # 准备交易数据
                    # 使用固定的Gas价格 3 Gwei
                    # 直接使用整数值，1 Gwei = 10^9 Wei，3 Gwei = 3 * 10^9 Wei
                    fixed_gas_price = 3 * 10**9  # 3 Gwei
                    current_gas_price = self.w3.eth.gas_price  # 仅用于日志输出
                    print(f"当前网络Gas价格: {current_gas_price} Wei ({self.w3.from_wei(current_gas_price, 'gwei')} Gwei)")
                    print(f"设置固定Gas价格: {fixed_gas_price} Wei (3 Gwei)")

                    # 如果用户指定了Gas价格，使用用户指定的价格
                    if gas_price:
                        user_gas_price = int(gas_price * 10**9)  # 转换为Wei
                        print(f"使用用户指定的Gas价格: {gas_price} Gwei ({user_gas_price} Wei)")
                        fixed_gas_price = user_gas_price

                    # 构建交易
                    tx_data = contract_func(*func["args"]).build_transaction({
                        'chainId': self.wallet.chain_id,
                        'gas': self.claim_gas_limit,  # 使用自定义gas限制
                        'gasPrice': fixed_gas_price,
                        'nonce': self.w3.eth.get_transaction_count(self.wallet.account.address)
                    })

                    # 确保value字段存在
                    if 'value' not in tx_data:
                        tx_data['value'] = 0

                    # 移除所有不必要的字段
                    essential_fields = ['chainId', 'gas', 'gasPrice', 'nonce', 'to', 'data', 'value']
                    for field in list(tx_data.keys()):
                        if field not in essential_fields:
                            print(f"移除非必要字段: {field}")
                            del tx_data[field]

                    print(f"交易数据: {tx_data}")

                    print(f"使用Gas限制: {self.claim_gas_limit}")
                    print(f"最终使用的Gas价格: {self.w3.from_wei(fixed_gas_price, 'gwei')} Gwei")

                    # 再次检查交易数据
                    print(f"交易数据中的gasPrice: {tx_data.get('gasPrice')} Wei ({self.w3.from_wei(tx_data.get('gasPrice', 0), 'gwei')} Gwei)")
                    print(f"交易数据中的字段: {list(tx_data.keys())}")
                    print(f"交易数据: {tx_data}")

                    # 确保gasPrice字段存在且值正确
                    if 'gasPrice' not in tx_data or tx_data['gasPrice'] != fixed_gas_price:
                        print(f"警告: gasPrice字段不存在或值不正确，强制设置为 {fixed_gas_price} Wei")
                        tx_data['gasPrice'] = fixed_gas_price

                    # 签名交易
                    try:
                        # 确保所有字段都是正确的类型
                        tx_data['chainId'] = int(tx_data['chainId'])
                        tx_data['gas'] = int(tx_data['gas'])
                        tx_data['gasPrice'] = int(tx_data['gasPrice'])
                        tx_data['nonce'] = int(tx_data['nonce'])
                        tx_data['value'] = int(tx_data['value'])

                        # 使用Web3.py的标准方法签名交易
                        signed_tx = self.w3.eth.account.sign_transaction(tx_data, self.wallet.account.key)
                        print(f"签名交易对象类型: {type(signed_tx)}")
                        print(f"签名交易对象属性: {dir(signed_tx)}")
                    except Exception as sign_error:
                        print(f"签名交易失败: {str(sign_error)}")
                        print(f"交易数据: {tx_data}")
                        raise

                    # 发送交易
                    try:
                        # 获取原始交易数据
                        if hasattr(signed_tx, 'rawTransaction'):
                            raw_tx = signed_tx.rawTransaction
                            print("使用rawTransaction属性")
                        elif hasattr(signed_tx, 'raw_transaction'):
                            raw_tx = signed_tx.raw_transaction
                            print("使用raw_transaction属性")
                        else:
                            # 尝试直接使用签名交易对象
                            print("无法获取原始交易数据，尝试直接使用签名交易对象")
                            raw_tx = signed_tx

                        # 使用Web3.py的标准方法发送交易
                        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
                        print(f"交易已提交，交易哈希: {tx_hash.hex()}")

                        # 等待交易确认
                        print("等待交易确认...")
                        try:
                            # 较新版本的Web3.py
                            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                        except TypeError:
                            # 较旧版本的Web3.py不支持timeout参数
                            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                    except Exception as tx_error:
                        # 处理交易错误
                        error_message = str(tx_error)
                        if "already known" in error_message:
                            # 交易已经提交，尝试从错误消息中提取交易哈希
                            print("交易已经提交，尝试获取交易哈希...")
                            import re
                            hash_match = re.search(r'0x[a-fA-F0-9]{64}', error_message)
                            if hash_match:
                                tx_hash = hash_match.group(0)
                                print(f"找到交易哈希: {tx_hash}")
                                try:
                                    # 较新版本的Web3.py
                                    receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                                except TypeError:
                                    # 较旧版本的Web3.py不支持timeout参数
                                    receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                            else:
                                raise Exception("无法获取交易哈希")
                        else:
                            raise

                    if receipt.status == 1:
                        print(f"交易成功! 函数: {func['name']}")
                        success = True
                        break
                    else:
                        print(f"交易失败! 函数: {func['name']}")

                        # 尝试获取失败原因
                        try:
                            # 获取交易详情
                            tx = self.w3.eth.get_transaction(tx_hash)
                            # 尝试模拟交易以获取失败原因
                            try:
                                self.w3.eth.call(
                                    {
                                        'to': tx['to'],
                                        'from': tx['from'],
                                        'data': tx['input'],
                                        'value': tx['value'],
                                        'gas': tx['gas'],
                                        'gasPrice': tx['gasPrice'],
                                    },
                                    tx['blockNumber']
                                )
                                print("交易模拟成功，但实际执行失败，可能是状态变化导致的")
                            except Exception as call_error:
                                error_message = str(call_error)
                                print(f"交易失败原因: {error_message}")

                                # 检查常见错误
                                if "TIME OUT" in error_message:
                                    print("错误原因: 交易截止时间已过期")
                                    print(f"当前使用的deadline: {func['args'][2]}")
                                    print(f"当前时间戳: {int(time.time())}")
                                elif "SIGN ERROR" in error_message:
                                    print("错误原因: 签名验证失败")
                                    print(f"当前使用的签名: {func['args'][3]}")
                                elif "CLAIMED" in error_message:
                                    print("错误原因: 已经领取过空投")
                                elif "NOT ELIGIBLE" in error_message:
                                    print("错误原因: 不符合领取条件")
                        except Exception as debug_error:
                            print(f"获取失败原因时出错: {str(debug_error)}")

                except Exception as e:
                    error_message = str(e)
                    print(f"调用 {func['name']} 失败: {error_message}")
                    continue

            if success:
                # 等待一段时间，确保代币余额已更新
                print("等待代币余额更新...")
                time.sleep(10)

                # 获取新的代币余额
                new_balance = self.get_token_balance()

                # 计算获得的代币数量
                received = new_balance['balance'] - initial_balance['balance']
                if received > 0:
                    received_tokens = received / (10 ** new_balance['decimals'])
                    print(f"成功领取 {received_tokens} 个 {new_balance['symbol']} 代币!")
                else:
                    print("交易成功，但未检测到代币余额变化。可能需要等待更长时间。")

                return True
            else:
                print("所有尝试都失败了!")
                return False

        except Exception as e:
            print(f"领取空投时出错: {str(e)}")
            return False



    def get_wallet_signature(self):
        """使用私钥对钱包地址进行签名"""
        try:
            print("使用私钥生成钱包地址签名...")

            # 要签名的消息就是钱包地址
            message = self.wallet.account.address
            print(f"签名消息: {message}")

            # 使用私钥签名消息
            try:
                # 较新版本的Web3.py
                signed = self.w3.eth.account.sign_message(
                    message={"text": message},
                    private_key=self.wallet.account.key
                )
            except TypeError:
                try:
                    # 另一种可能的方法
                    message_encoded = Web3.to_bytes(text=message)
                    signed = self.w3.eth.account.sign_message(
                        message_hash=Web3.keccak(b'\x19Ethereum Signed Message:\n' + str(len(message_encoded)).encode() + message_encoded),
                        private_key=self.wallet.account.key
                    )
                except TypeError:
                    # 最旧版本的Web3.py
                    from eth_account.messages import encode_defunct
                    message_encoded = encode_defunct(text=message)
                    signed = self.w3.eth.account.sign_message(
                        message_encoded,
                        private_key=self.wallet.account.key
                    )

            # 获取签名
            signature = signed.signature
            hex_signature = "0x" + signature.hex()
            print(f"生成的钱包地址签名: {hex_signature}")

            return hex_signature

        except Exception as e:
            print(f"生成钱包地址签名时出错: {str(e)}")
            # 签名失败，返回None
            return None

    def get_claim_signature(self):
        """从Jager API获取签名"""
        try:
            print("从Jager API获取签名数据...")

            # 获取钱包地址签名
            wallet_signature = self.get_wallet_signature()
            if wallet_signature is None:
                print("无法生成钱包地址签名，无法继续")
                return None

            # 准备请求数据
            data = {
                "address": self.wallet.account.address,
                "solAddress": "",
                "signStr": wallet_signature,
                "solSignStr": ""
            }

            # 发送请求到Jager API
            url = "https://api.jager.meme/api/airdrop/claimAirdrop"
            print(f"发送请求到: {url}")
            print(f"请求数据: {json.dumps(data)}")

            response = requests.post(url, json=data, timeout=30)
            print(f"API响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"API响应: {json.dumps(result)}")

                if result["code"] == 200 and "data" in result and "sign" in result["data"]:
                    api_signature = result["data"]["sign"]
                    api_amount = result["data"]["amount"]
                    deadline = result["data"]["deadline"]

                    print(f"获取到API签名: {api_signature}")
                    print(f"API返回的空投数量: {api_amount}")
                    print(f"截止时间: {deadline}")
                    print(f"API返回的完整数据: {result['data']}")

                    # 保存API返回的数据，供后续使用
                    # 确保使用正确的amount值 - 7300000000
                    self.api_amount = 7300000000 * 10**18  # 使用已知的正确值
                    print(f"使用固定的空投数量: {self.api_amount}")

                    # 直接使用API返回的deadline值，不进行任何修改
                    try:
                        # 尝试转换为整数，但仍然使用原始值
                        deadline_int = int(deadline)
                        print(f"API返回的deadline值 (整数): {deadline_int}")
                    except (ValueError, TypeError):
                        print(f"警告: API返回的deadline值 '{deadline}' 不是有效的整数，但仍将使用原始值")

                    # 无论如何，都使用API返回的原始值
                    self.api_deadline = deadline
                    print(f"使用API返回的原始deadline值: {self.api_deadline}")

                    # 移除0x前缀（如果有）
                    if api_signature.startswith("0x"):
                        clean_signature = api_signature[2:]
                    else:
                        clean_signature = api_signature

                    # 转换为字节
                    signature_bytes = bytes.fromhex(clean_signature)
                    return signature_bytes
                else:
                    print(f"API返回错误: {result.get('message', '未知错误')}")
            else:
                print(f"API请求失败: {response.text}")

            # API请求失败，无法继续
            print("API请求失败，无法获取签名数据")
            return None

        except Exception as e:
            print(f"获取签名数据时出错: {str(e)}")
            # 无法获取签名数据，返回None
            return None

    def get_token_balance(self):
        """获取代币余额"""
        try:
            balance_info = self.wallet.get_token_balance(JAGER_TOKEN_CONTRACT)
            print(f"当前 {balance_info['symbol']} 余额: {balance_info['balance_token']}")
            return balance_info
        except Exception as e:
            print(f"获取代币余额失败: {str(e)}")

            # 尝试直接使用合约调用获取余额
            try:
                print("尝试直接使用合约调用获取余额...")

                # 创建合约实例
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
                    }
                ]

                token_contract = self.w3.eth.contract(address=self.wallet.to_checksum_address(JAGER_TOKEN_CONTRACT), abi=abi)

                # 获取代币精度
                try:
                    decimals = token_contract.functions.decimals().call()
                    print(f"代币精度: {decimals}")
                except Exception as e2:
                    print(f"获取代币精度失败: {str(e2)}")
                    print("使用默认精度: 18")
                    decimals = 18

                # 获取余额
                try:
                    balance = token_contract.functions.balanceOf(self.wallet.account.address).call()
                    balance_token = balance / (10 ** decimals)
                    print(f"直接获取的余额: {balance} (最小单位)")
                    print(f"直接获取的余额: {balance_token} JAGER")

                    return {
                        'address': self.wallet.account.address,
                        'token_address': JAGER_TOKEN_CONTRACT,
                        'symbol': 'JAGER',
                        'balance': balance,
                        'balance_token': balance_token,
                        'decimals': decimals
                    }
                except Exception as e3:
                    print(f"直接获取余额失败: {str(e3)}")
            except Exception as e4:
                print(f"直接使用合约调用获取余额失败: {str(e4)}")

            # 如果所有方法都失败，返回默认值
            return {'balance': 0, 'decimals': 18, 'symbol': 'JAGER', 'balance_token': 0}

    def transfer_bnb(self, to_address, amount_bnb, gas_price=None, gas_limit=None):
        """转账BNB到指定地址"""
        try:
            print(f"准备转账 {amount_bnb} BNB 到地址: {to_address}")

            # 如果提供了gas_limit，更新实例的bnb_gas_limit
            if gas_limit:
                self.bnb_gas_limit = int(gas_limit)
                print(f"使用自定义gas限制: {self.bnb_gas_limit}")

            # 检查钱包是否已导入
            if not self.wallet.account:
                print("错误: 请先导入钱包")
                return False

            # 获取当前BNB余额
            balance_info = self.wallet.get_bnb_balance()
            print(f"当前BNB余额: {balance_info['balance_bnb']} BNB")

            # 检查余额是否足够
            if balance_info['balance_bnb'] < amount_bnb:
                print(f"错误: BNB余额不足. 当前余额: {balance_info['balance_bnb']} BNB, 需要: {amount_bnb} BNB")
                return False

            # 设置Gas价格
            if gas_price is None:
                gas_price = 3  # 默认使用3 Gwei
                print(f"使用默认Gas价格: {gas_price} Gwei")
            else:
                print(f"使用指定Gas价格: {gas_price} Gwei")

            # 执行转账
            try:
                result = self.wallet.transfer_bnb(to_address, amount_bnb, gas_price)

                print(f"BNB转账成功!")
                print(f"交易哈希: {result['transaction_hash']}")
                print(f"从: {result['from']}")
                print(f"到: {result['to']}")
                print(f"金额: {result['amount_bnb']} BNB")
            except Exception as e:
                print(f"使用wallet.transfer_bnb失败: {str(e)}")
                print("尝试直接构建和发送交易...")

                # 直接构建和发送交易
                try:
                    # 准备交易
                    tx = {
                        'nonce': self.w3.eth.get_transaction_count(self.wallet.account.address),
                        'to': self.wallet.to_checksum_address(to_address),
                        'value': self.w3.to_wei(amount_bnb, 'ether'),
                        'gas': self.bnb_gas_limit,  # 使用自定义gas限制
                        'chainId': self.wallet.chain_id
                    }

                    print(f"使用gas限制: {self.bnb_gas_limit}")

                    # 设置Gas价格
                    if gas_price:
                        tx['gasPrice'] = self.w3.to_wei(gas_price, 'gwei')
                    else:
                        tx['gasPrice'] = self.w3.to_wei(3, 'gwei')  # 默认3 Gwei

                    # 签名交易
                    signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet.account.key)

                    # 尝试获取原始交易数据
                    raw_tx = None
                    if hasattr(signed_tx, 'rawTransaction'):
                        raw_tx = signed_tx.rawTransaction
                        print("使用rawTransaction属性")
                    elif hasattr(signed_tx, 'raw_transaction'):
                        raw_tx = signed_tx.raw_transaction
                        print("使用raw_transaction属性")
                    elif hasattr(signed_tx, 'raw'):
                        raw_tx = signed_tx.raw
                        print("使用raw属性")
                    elif isinstance(signed_tx, dict) and 'raw' in signed_tx:
                        raw_tx = signed_tx['raw']
                        print("使用字典中的raw键")
                    elif isinstance(signed_tx, dict) and 'rawTransaction' in signed_tx:
                        raw_tx = signed_tx['rawTransaction']
                        print("使用字典中的rawTransaction键")
                    else:
                        # 尝试直接使用签名交易对象
                        print(f"无法获取原始交易数据，尝试直接使用签名交易对象")
                        print(f"签名交易对象类型: {type(signed_tx)}")
                        print(f"签名交易对象属性: {dir(signed_tx)}")

                        # 如果有signature属性，尝试使用其他方法
                        if hasattr(signed_tx, 'signature'):
                            print(f"签名交易对象有signature属性，但无法获取原始交易数据")
                            print(f"signature: {signed_tx.signature}")
                            print(f"v: {signed_tx.v if hasattr(signed_tx, 'v') else 'N/A'}")
                            print(f"r: {signed_tx.r if hasattr(signed_tx, 'r') else 'N/A'}")
                            print(f"s: {signed_tx.s if hasattr(signed_tx, 's') else 'N/A'}")

                            # 尝试使用__dict__属性
                            if hasattr(signed_tx, '__dict__'):
                                print(f"签名交易对象的__dict__: {signed_tx.__dict__}")
                                if 'rawTransaction' in signed_tx.__dict__:
                                    raw_tx = signed_tx.__dict__['rawTransaction']
                                    print("从__dict__中获取rawTransaction")
                                elif 'raw_transaction' in signed_tx.__dict__:
                                    raw_tx = signed_tx.__dict__['raw_transaction']
                                    print("从__dict__中获取raw_transaction")

                            # 如果仍然无法获取原始交易数据，尝试使用hex()方法
                            if raw_tx is None and hasattr(signed_tx, 'hex'):
                                try:
                                    raw_tx_hex = signed_tx.hex()
                                    raw_tx = bytes.fromhex(raw_tx_hex.replace('0x', ''))
                                    print("使用hex()方法获取原始交易数据")
                                except Exception as hex_error:
                                    print(f"使用hex()方法失败: {str(hex_error)}")

                            # 如果仍然无法获取原始交易数据，尝试使用str()方法
                            if raw_tx is None:
                                try:
                                    raw_tx_str = str(signed_tx)
                                    if raw_tx_str.startswith('0x'):
                                        raw_tx = bytes.fromhex(raw_tx_str.replace('0x', ''))
                                        print("使用str()方法获取原始交易数据")
                                except Exception as str_error:
                                    print(f"使用str()方法失败: {str(str_error)}")
                        else:
                            raise Exception("无法获取原始交易数据")

                    # 发送交易
                    tx_hash = self.w3.eth.send_raw_transaction(raw_tx)

                    # 构建结果
                    result = {
                        'transaction_hash': tx_hash.hex(),
                        'from': self.wallet.account.address,
                        'to': to_address,
                        'amount_bnb': amount_bnb,
                        'amount_wei': self.w3.to_wei(amount_bnb, 'ether')
                    }

                    print(f"BNB转账成功!")
                    print(f"交易哈希: {result['transaction_hash']}")
                    print(f"从: {result['from']}")
                    print(f"到: {result['to']}")
                    print(f"金额: {result['amount_bnb']} BNB")
                except Exception as e2:
                    print(f"直接构建和发送交易也失败: {str(e2)}")
                    return False

            return result
        except Exception as e:
            print(f"BNB转账失败: {str(e)}")
            return False

    def transfer_jager(self, to_address, amount, gas_price=None, gas_limit=None):
        """转账Jager代币到指定地址"""
        try:
            print(f"准备转账 {amount} JAGER 到地址: {to_address}")

            # 如果提供了gas_limit，更新实例的gas_limit
            if gas_limit:
                self.gas_limit = int(gas_limit)
                print(f"使用自定义gas限制: {self.gas_limit}")

            # 检查钱包是否已导入
            if not self.wallet.account:
                print("错误: 请先导入钱包")
                return False

            # 获取当前Jager代币余额
            balance_info = self.get_token_balance()
            print(f"当前JAGER余额: {balance_info['balance_token']} JAGER")

            # 检查余额是否足够
            if balance_info['balance_token'] < amount:
                print(f"错误: JAGER余额不足. 当前余额: {balance_info['balance_token']} JAGER, 需要: {amount} JAGER")
                return False

            # 设置Gas价格
            if gas_price is None:
                gas_price = 3  # 默认使用3 Gwei
                print(f"使用默认Gas价格: {gas_price} Gwei")
            else:
                print(f"使用指定Gas价格: {gas_price} Gwei")

            # 使用BNB转账的方式来处理Jager代币转账
            try:
                # 创建合约实例
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
                    }
                ]

                token_contract = self.w3.eth.contract(address=self.wallet.to_checksum_address(JAGER_TOKEN_CONTRACT), abi=abi)

                # 获取代币精度
                try:
                    decimals = token_contract.functions.decimals().call()
                    print(f"代币精度: {decimals}")
                except Exception as e:
                    print(f"获取代币精度失败: {str(e)}")
                    print("使用默认精度: 18")
                    decimals = 18

                # 获取代币符号
                try:
                    symbol = token_contract.functions.symbol().call()
                    print(f"代币符号: {symbol}")
                except Exception as e:
                    print(f"获取代币符号失败: {str(e)}")
                    print("使用默认符号: JAGER")
                    symbol = "JAGER"

                # 使用get_token_balance()返回的余额，而不是尝试再次调用balanceOf()
                balance_info = self.get_token_balance()
                # 转换为最小单位
                sender_balance = int(balance_info['balance_token'] * (10 ** decimals))
                print(f"发送方余额 (从get_token_balance获取): {balance_info['balance_token']} JAGER")
                print(f"发送方余额 (最小单位): {sender_balance}")

                # 直接使用整数值，添加适当数量的零
                # 例如，如果 amount = 3036800000.0，decimals = 18
                # 我们需要的是 3036800000 * 10^18 = 3036800000000000000000000000

                # 首先将浮点数转换为整数
                amount_integer = int(amount)
                print(f"转账金额 (整数部分): {amount_integer}")

                # 然后添加适当数量的零
                amount_in_smallest_unit = amount_integer * (10 ** decimals)
                print(f"转账金额: {amount} {symbol}")
                print(f"转账金额 (最小单位): {amount_in_smallest_unit}")

                # 检查余额是否足够
                if sender_balance < amount_in_smallest_unit:
                    print(f"警告: 余额不足! 当前余额: {sender_balance / (10 ** decimals)} {symbol}, 需要: {amount} {symbol}")
                    print("尝试使用可用的最大余额进行转账")
                    amount_in_smallest_unit = sender_balance
                    print(f"调整后的转账金额: {sender_balance / (10 ** decimals)} {symbol}")

                # 检查金额是否超出了uint256的范围
                if amount_in_smallest_unit >= 2**256:
                    print(f"警告: 金额 {amount_in_smallest_unit} 超出了uint256的范围，将被截断")
                    amount_in_smallest_unit = amount_in_smallest_unit % (2**256)
                    print(f"截断后的金额: {amount_in_smallest_unit}")

                # 获取transfer函数的调用数据
                print(f"转账金额（最小单位）: {amount_in_smallest_unit}")

                # 动态计算transfer函数的方法ID
                from eth_utils import function_signature_to_4byte_selector, to_hex

                # 计算方法ID
                function_signature = "transfer(address,uint256)"
                method_id_bytes = function_signature_to_4byte_selector(function_signature)
                method_id = to_hex(method_id_bytes)  # 转换为十六进制字符串

                # 将地址填充到32字节
                address_param = self.wallet.to_checksum_address(to_address).replace("0x", "").lower().zfill(64)

                # 将金额填充到32字节
                amount_hex = hex(amount_in_smallest_unit).replace("0x", "").zfill(64)

                # 组合方法ID和参数
                # 确保method_id不包含重复的0x前缀
                clean_method_id = method_id.replace("0x", "")
                transfer_data = "0x" + clean_method_id + address_param + amount_hex

                print(f"方法ID: {method_id}")
                print(f"地址参数: {address_param}")
                print(f"金额参数: {amount_hex}")
                print(f"完整调用数据: {transfer_data}")

                # 准备交易
                tx = {
                    'nonce': self.w3.eth.get_transaction_count(self.wallet.account.address),
                    'to': self.wallet.to_checksum_address(JAGER_TOKEN_CONTRACT),  # 代币合约地址
                    'value': 0,  # 代币转账不需要发送ETH
                    'gas': self.gas_limit,  # 使用自定义gas限制
                    'chainId': self.wallet.chain_id,
                    'data': transfer_data  # 调用transfer函数的数据
                }

                print(f"使用gas限制: {self.gas_limit}")

                # 设置Gas价格
                if gas_price:
                    tx['gasPrice'] = self.w3.to_wei(gas_price, 'gwei')
                else:
                    tx['gasPrice'] = self.w3.to_wei(3, 'gwei')  # 默认3 Gwei

                print(f"交易数据: {tx}")

                # 签名交易
                signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet.account.key)

                # 尝试获取原始交易数据
                raw_tx = None
                if hasattr(signed_tx, 'rawTransaction'):
                    raw_tx = signed_tx.rawTransaction
                    print("使用rawTransaction属性")
                elif hasattr(signed_tx, 'raw_transaction'):
                    raw_tx = signed_tx.raw_transaction
                    print("使用raw_transaction属性")
                elif hasattr(signed_tx, 'raw'):
                    raw_tx = signed_tx.raw
                    print("使用raw属性")
                elif isinstance(signed_tx, dict) and 'raw' in signed_tx:
                    raw_tx = signed_tx['raw']
                    print("使用字典中的raw键")
                elif isinstance(signed_tx, dict) and 'rawTransaction' in signed_tx:
                    raw_tx = signed_tx['rawTransaction']
                    print("使用字典中的rawTransaction键")
                else:
                    # 尝试直接使用签名交易对象
                    print(f"无法获取原始交易数据，尝试直接使用签名交易对象")
                    print(f"签名交易对象类型: {type(signed_tx)}")
                    print(f"签名交易对象属性: {dir(signed_tx)}")

                    # 尝试使用__dict__属性
                    if hasattr(signed_tx, '__dict__'):
                        print(f"签名交易对象的__dict__: {signed_tx.__dict__}")
                        if 'rawTransaction' in signed_tx.__dict__:
                            raw_tx = signed_tx.__dict__['rawTransaction']
                            print("从__dict__中获取rawTransaction")
                        elif 'raw_transaction' in signed_tx.__dict__:
                            raw_tx = signed_tx.__dict__['raw_transaction']
                            print("从__dict__中获取raw_transaction")

                    # 如果仍然无法获取原始交易数据，尝试使用hex()方法
                    if raw_tx is None and hasattr(signed_tx, 'hex'):
                        try:
                            raw_tx_hex = signed_tx.hex()
                            raw_tx = bytes.fromhex(raw_tx_hex.replace('0x', ''))
                            print("使用hex()方法获取原始交易数据")
                        except Exception as hex_error:
                            print(f"使用hex()方法失败: {str(hex_error)}")

                    # 如果仍然无法获取原始交易数据，尝试使用str()方法
                    if raw_tx is None:
                        try:
                            raw_tx_str = str(signed_tx)
                            if raw_tx_str.startswith('0x'):
                                raw_tx = bytes.fromhex(raw_tx_str.replace('0x', ''))
                                print("使用str()方法获取原始交易数据")
                        except Exception as str_error:
                            print(f"使用str()方法失败: {str(str_error)}")

                if raw_tx is None:
                    raise Exception("无法获取原始交易数据")

                # 发送交易
                tx_hash = self.w3.eth.send_raw_transaction(raw_tx)

                # 构建结果
                result = {
                    'transaction_hash': tx_hash.hex(),
                    'from': self.wallet.account.address,
                    'to': to_address,
                    'token_address': JAGER_TOKEN_CONTRACT,
                    'amount': amount,
                    'amount_in_smallest_unit': amount_in_smallest_unit
                }

                print(f"JAGER转账成功!")
                print(f"交易哈希: {result['transaction_hash']}")
                print(f"从: {result['from']}")
                print(f"到: {result['to']}")
                print(f"金额: {result['amount']} JAGER")

                return result
            except Exception as e:
                print(f"JAGER转账失败: {str(e)}")

                # 尝试使用直接JSON-RPC调用
                try:
                    print("尝试使用直接JSON-RPC调用...")

                    import requests
                    import json

                    # 创建合约实例
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
                        }
                    ]

                    token_contract = self.w3.eth.contract(address=self.wallet.to_checksum_address(JAGER_TOKEN_CONTRACT), abi=abi)

                    # 获取代币精度
                    try:
                        decimals = token_contract.functions.decimals().call()
                        print(f"代币精度: {decimals}")
                    except Exception as e:
                        print(f"获取代币精度失败: {str(e)}")
                        print("使用默认精度: 18")
                        decimals = 18

                    # 获取代币符号
                    try:
                        symbol = token_contract.functions.symbol().call()
                        print(f"代币符号: {symbol}")
                    except Exception as e:
                        print(f"获取代币符号失败: {str(e)}")
                        print("使用默认符号: JAGER")
                        symbol = "JAGER"

                    # 使用get_token_balance()返回的余额，而不是尝试再次调用balanceOf()
                    balance_info = self.get_token_balance()
                    # 转换为最小单位
                    sender_balance = int(balance_info['balance_token'] * (10 ** decimals))
                    print(f"发送方余额 (从get_token_balance获取): {balance_info['balance_token']} JAGER")
                    print(f"发送方余额 (最小单位): {sender_balance}")

                    # 直接使用整数值，添加适当数量的零
                    # 例如，如果 amount = 3036800000.0，decimals = 18
                    # 我们需要的是 3036800000 * 10^18 = 3036800000000000000000000000

                    # 首先将浮点数转换为整数
                    amount_integer = int(amount)
                    print(f"转账金额 (整数部分): {amount_integer}")

                    # 然后添加适当数量的零
                    amount_in_smallest_unit = amount_integer * (10 ** decimals)
                    print(f"转账金额: {amount} {symbol}")
                    print(f"转账金额 (最小单位): {amount_in_smallest_unit}")

                    # 检查余额是否足够
                    if sender_balance < amount_in_smallest_unit:
                        print(f"警告: 余额不足! 当前余额: {sender_balance / (10 ** decimals)} {symbol}, 需要: {amount} {symbol}")
                        print("尝试使用可用的最大余额进行转账")
                        amount_in_smallest_unit = sender_balance
                        print(f"调整后的转账金额: {sender_balance / (10 ** decimals)} {symbol}")

                    # 检查金额是否超出了uint256的范围
                    if amount_in_smallest_unit >= 2**256:
                        print(f"警告: 金额 {amount_in_smallest_unit} 超出了uint256的范围，将被截断")
                        amount_in_smallest_unit = amount_in_smallest_unit % (2**256)
                        print(f"截断后的金额: {amount_in_smallest_unit}")

                    # 获取transfer函数的调用数据
                    print(f"转账金额（最小单位）: {amount_in_smallest_unit}")

                    # 动态计算transfer函数的方法ID
                    from eth_utils import function_signature_to_4byte_selector, to_hex

                    # 计算方法ID
                    function_signature = "transfer(address,uint256)"
                    method_id_bytes = function_signature_to_4byte_selector(function_signature)
                    method_id = to_hex(method_id_bytes)  # 转换为十六进制字符串

                    # 将地址填充到32字节
                    address_param = self.wallet.to_checksum_address(to_address).replace("0x", "").lower().zfill(64)

                    # 将金额填充到32字节
                    amount_hex = hex(amount_in_smallest_unit).replace("0x", "").zfill(64)

                    # 组合方法ID和参数
                    # 确保method_id不包含重复的0x前缀
                    clean_method_id = method_id.replace("0x", "")
                    transfer_data = "0x" + clean_method_id + address_param + amount_hex

                    print(f"方法ID: {method_id}")
                    print(f"地址参数: {address_param}")
                    print(f"金额参数: {amount_hex}")
                    print(f"完整调用数据: {transfer_data}")

                    # 准备交易
                    tx = {
                        'nonce': self.w3.eth.get_transaction_count(self.wallet.account.address),
                        'to': self.wallet.to_checksum_address(JAGER_TOKEN_CONTRACT),  # 代币合约地址
                        'value': 0,  # 代币转账不需要发送ETH
                        'gas': self.gas_limit,  # 使用自定义gas限制
                        'chainId': self.wallet.chain_id,
                        'data': transfer_data  # 调用transfer函数的数据
                    }

                    print(f"使用gas限制: {self.gas_limit}")

                    # 设置Gas价格
                    if gas_price:
                        tx['gasPrice'] = self.w3.to_wei(gas_price, 'gwei')
                    else:
                        tx['gasPrice'] = self.w3.to_wei(3, 'gwei')  # 默认3 Gwei

                    print(f"交易数据: {tx}")

                    # 签名交易
                    signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet.account.key)

                    # 获取签名的十六进制表示
                    if hasattr(signed_tx, 'rawTransaction') and signed_tx.rawTransaction:
                        raw_tx_hex = '0x' + signed_tx.rawTransaction.hex()
                    elif hasattr(signed_tx, 'raw_transaction') and signed_tx.raw_transaction:
                        raw_tx_hex = '0x' + signed_tx.raw_transaction.hex()
                    else:
                        # 尝试使用__dict__属性
                        if hasattr(signed_tx, '__dict__'):
                            print(f"签名交易对象的__dict__: {signed_tx.__dict__}")
                            if 'rawTransaction' in signed_tx.__dict__ and signed_tx.__dict__['rawTransaction']:
                                raw_tx_hex = '0x' + signed_tx.__dict__['rawTransaction'].hex()
                            elif 'raw_transaction' in signed_tx.__dict__ and signed_tx.__dict__['raw_transaction']:
                                raw_tx_hex = '0x' + signed_tx.__dict__['raw_transaction'].hex()
                            else:
                                # 尝试使用其他属性
                                for attr_name in dir(signed_tx):
                                    if attr_name.startswith('_'):
                                        continue
                                    attr_value = getattr(signed_tx, attr_name)
                                    if isinstance(attr_value, bytes):
                                        print(f"找到字节属性: {attr_name}")
                                        raw_tx_hex = '0x' + attr_value.hex()
                                        break

                    if 'raw_tx_hex' not in locals():
                        raise Exception("无法获取签名交易的十六进制表示")

                    print(f"使用直接JSON-RPC调用发送交易: {raw_tx_hex}")

                    # 准备JSON-RPC请求
                    rpc_url = self.wallet.rpc_url
                    headers = {'Content-Type': 'application/json'}
                    payload = {
                        'jsonrpc': '2.0',
                        'method': 'eth_sendRawTransaction',
                        'params': [raw_tx_hex],
                        'id': 1
                    }

                    # 发送请求
                    response = requests.post(rpc_url, headers=headers, data=json.dumps(payload))
                    response_json = response.json()

                    print(f"JSON-RPC响应: {response_json}")

                    if 'error' in response_json:
                        raise Exception(f"JSON-RPC错误: {response_json['error']['message']}")

                    tx_hash = response_json['result']

                    # 构建结果
                    result = {
                        'transaction_hash': tx_hash,
                        'from': self.wallet.account.address,
                        'to': to_address,
                        'token_address': JAGER_TOKEN_CONTRACT,
                        'amount': amount,
                        'amount_in_smallest_unit': amount_in_smallest_unit
                    }

                    print(f"JAGER转账成功!")
                    print(f"交易哈希: {result['transaction_hash']}")
                    print(f"从: {result['from']}")
                    print(f"到: {result['to']}")
                    print(f"金额: {result['amount']} JAGER")

                    return result
                except Exception as e2:
                    print(f"直接JSON-RPC调用也失败: {str(e2)}")
                    return False

        except Exception as e:
            print(f"JAGER转账失败: {str(e)}")
            return False

    def monitor_and_claim(self, interval=60, duration=3600):
        """监控并尝试领取空投"""
        print(f"开始监控 Jager 空投...")
        print(f"钱包地址: {self.wallet.account.address}")
        print(f"监控间隔: {interval}秒")
        print(f"监控时长: {duration}秒")

        start_time = time.time()
        end_time = start_time + duration

        # 获取初始余额
        initial_balance = self.get_token_balance()

        # 监控循环
        try:
            while time.time() < end_time:
                current_time = time.time()
                elapsed = current_time - start_time
                remaining = end_time - current_time

                print(f"\n已监控: {int(elapsed)}秒, 剩余: {int(remaining)}秒")

                # 尝试领取空投
                if self.claim_airdrop():
                    print("空投已成功领取，停止监控。")
                    break

                # 等待下一次检查
                if time.time() < end_time:
                    print(f"等待 {interval} 秒后再次尝试...")
                    time.sleep(interval)

        except KeyboardInterrupt:
            print("\n监控已手动停止")

        # 最终余额检查
        final_balance = self.get_token_balance()
        total_received = final_balance['balance'] - initial_balance['balance']

        print("\n监控结束")
        print(f"最终 {final_balance['symbol']} 余额: {final_balance['balance_token']}")
        if total_received > 0:
            print(f"总共接收: {total_received / (10 ** final_balance['decimals'])} {final_balance['symbol']}")
        else:
            print("未接收任何代币")

def main():
    parser = argparse.ArgumentParser(description='Jager空投领取工具')
    parser.add_argument('--private-key', '-k', required=True, help='钱包私钥')
    parser.add_argument('--testnet', '-t', action='store_true', help='使用测试网')
    parser.add_argument('--gas-price', '-g', type=float, help='Gas价格（Gwei）')
    parser.add_argument('--interval', '-i', type=int, default=60, help='监控间隔（秒）')
    parser.add_argument('--duration', '-d', type=int, default=3600, help='监控时长（秒）')
    parser.add_argument('--monitor', '-m', action='store_true', help='启用监控模式')

    # 添加转账相关参数
    parser.add_argument('--transfer-bnb', action='store_true', help='转账BNB')
    parser.add_argument('--transfer-jager', action='store_true', help='转账Jager代币')
    parser.add_argument('--to-address', help='转账目标地址')
    parser.add_argument('--amount', type=float, help='转账金额')

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

    # 创建空投领取器
    claimer = JagerAirdropClaimer(wallet, use_testnet=args.testnet)

    # 获取当前代币余额
    claimer.get_token_balance()

    # 获取当前BNB余额
    wallet.get_bnb_balance()

    # 处理转账BNB请求
    if args.transfer_bnb:
        if not args.to_address:
            print("错误: 转账BNB需要指定目标地址 (--to-address)")
            return
        if not args.amount:
            print("错误: 转账BNB需要指定金额 (--amount)")
            return

        claimer.transfer_bnb(args.to_address, args.amount, args.gas_price)
        return

    # 处理转账Jager代币请求
    if args.transfer_jager:
        if not args.to_address:
            print("错误: 转账Jager代币需要指定目标地址 (--to-address)")
            return
        if not args.amount:
            print("错误: 转账Jager代币需要指定金额 (--amount)")
            return

        claimer.transfer_jager(args.to_address, args.amount, args.gas_price)
        return

    # 处理空投领取请求
    if args.monitor:
        # 监控模式
        claimer.monitor_and_claim(interval=args.interval, duration=args.duration)
    else:
        # 直接尝试领取
        claimer.claim_airdrop(gas_price=args.gas_price)

if __name__ == "__main__":
    main()
