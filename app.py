from flask import Flask, request, jsonify, render_template
from app.wallet import Wallet
from dotenv import load_dotenv
import os
import json
import threading
import time
import io
import sys
from contextlib import redirect_stdout
from claim_jager_airdrop import JagerAirdropClaimer

# 不再尝试导入POA中间件，因为本地环境不需要也能正常工作
# 这样可以避免在服务器环境中因导入失败而产生警告

# 加载环境变量
load_dotenv()

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')

# 全局钱包实例
wallet = None

# 存储任务状态
jager_tasks = {}

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/api/create-wallet', methods=['POST'])
def create_wallet():
    """创建新钱包"""
    global wallet
    try:
        use_testnet = request.json.get('use_testnet', False)
        wallet = Wallet(use_testnet=use_testnet)
        wallet_data = wallet.create_wallet()
        return jsonify({'success': True, 'wallet': wallet_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/import-wallet', methods=['POST'])
def import_wallet():
    """导入钱包"""
    global wallet
    try:
        private_key = request.json.get('private_key')
        use_testnet = request.json.get('use_testnet', False)

        if not private_key:
            return jsonify({'success': False, 'error': '请提供私钥'}), 400

        wallet = Wallet(use_testnet=use_testnet)
        wallet_data = wallet.import_wallet(private_key)
        return jsonify({'success': True, 'wallet': wallet_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-bnb-balance', methods=['GET'])
def get_bnb_balance():
    """获取BNB余额"""
    try:
        address = request.args.get('address')

        if not wallet:
            use_testnet = request.args.get('use_testnet', 'false').lower() == 'true'
            temp_wallet = Wallet(use_testnet=use_testnet)
            balance = temp_wallet.get_bnb_balance(address)
        else:
            balance = wallet.get_bnb_balance(address)

        return jsonify({'success': True, 'balance': balance})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-token-balance', methods=['GET'])
def get_token_balance():
    """获取代币余额"""
    try:
        address = request.args.get('address')
        token_address = request.args.get('token_address')

        if not token_address:
            return jsonify({'success': False, 'error': '请提供代币合约地址'}), 400

        if not wallet:
            use_testnet = request.args.get('use_testnet', 'false').lower() == 'true'
            temp_wallet = Wallet(use_testnet=use_testnet)
            balance = temp_wallet.get_token_balance(token_address, address)
        else:
            balance = wallet.get_token_balance(token_address, address)

        return jsonify({'success': True, 'balance': balance})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/transfer-bnb', methods=['POST'])
def transfer_bnb():
    """转账BNB"""
    try:
        if not wallet:
            return jsonify({'success': False, 'error': '请先创建或导入钱包'}), 400

        to_address = request.json.get('to_address')
        amount = float(request.json.get('amount', 0))
        gas_price = request.json.get('gas_price')

        if not to_address:
            return jsonify({'success': False, 'error': '请提供接收地址'}), 400

        if amount <= 0:
            return jsonify({'success': False, 'error': '请提供有效的转账金额'}), 400

        if gas_price:
            gas_price = float(gas_price)

        result = wallet.transfer_bnb(to_address, amount, gas_price)
        return jsonify({'success': True, 'transaction': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/transfer-token', methods=['POST'])
def transfer_token():
    """转账代币"""
    try:
        if not wallet:
            return jsonify({'success': False, 'error': '请先创建或导入钱包'}), 400

        token_address = request.json.get('token_address')
        to_address = request.json.get('to_address')
        amount = float(request.json.get('amount', 0))
        gas_price = request.json.get('gas_price')

        if not token_address:
            return jsonify({'success': False, 'error': '请提供代币合约地址'}), 400

        if not to_address:
            return jsonify({'success': False, 'error': '请提供接收地址'}), 400

        if amount <= 0:
            return jsonify({'success': False, 'error': '请提供有效的转账金额'}), 400

        if gas_price:
            gas_price = float(gas_price)

        result = wallet.transfer_token(token_address, to_address, amount, gas_price)
        return jsonify({'success': True, 'transaction': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/interact-with-contract', methods=['POST'])
def interact_with_contract():
    """与智能合约交互"""
    try:
        if not wallet:
            return jsonify({'success': False, 'error': '请先创建或导入钱包'}), 400

        contract_address = request.json.get('contract_address')
        contract_abi = request.json.get('contract_abi')
        function_name = request.json.get('function_name')
        function_args = request.json.get('function_args', [])
        value = float(request.json.get('value', 0))

        if not contract_address:
            return jsonify({'success': False, 'error': '请提供合约地址'}), 400

        if not contract_abi:
            return jsonify({'success': False, 'error': '请提供合约ABI'}), 400

        if not function_name:
            return jsonify({'success': False, 'error': '请提供函数名称'}), 400

        result = wallet.interact_with_contract(
            contract_address,
            contract_abi,
            function_name,
            function_args,
            value
        )
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def claim_jager_airdrop_task(task_id, private_key, gas_price=None, gas_limit=None,
                       enable_auto_transfer=False, jager_receiver_address=None,
                       bnb_receiver_address=None, reserve_bnb_amount=0.0,
                       enable_bnb_chain_transfer=False, transfer_bnb_on_failure=False,
                       next_wallet_private_key=None):
    """后台任务，用于领取Jager空投"""
    # 捕获输出
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer):
        try:
            # 创建钱包实例
            wallet = Wallet(use_testnet=False)

            # 导入钱包
            try:
                wallet_data = wallet.import_wallet(private_key)
                print(f"钱包导入成功，地址: {wallet_data['address']}")
                jager_tasks[task_id]['wallet_address'] = wallet_data['address']
            except Exception as e:
                print(f"钱包导入失败: {str(e)}")
                jager_tasks[task_id]['status'] = 'failed'
                jager_tasks[task_id]['output'] = output_buffer.getvalue()
                return

            # 创建空投领取器
            claimer = JagerAirdropClaimer(wallet, use_testnet=False)

            # 输出 gas 限制信息
            if gas_limit:
                print(f"使用自定义 Gas 限制: {gas_limit}")
            else:
                print("使用默认 Gas 限制: 1000000")

            # 输出链式转账配置信息
            if enable_auto_transfer:
                print("\n自动转账功能已启用:")
                print(f"- Jager 代币接收地址: {jager_receiver_address}")
                print(f"- BNB 接收地址: {bnb_receiver_address}")
                print(f"- 保留 BNB 数量: {reserve_bnb_amount}")

                if enable_bnb_chain_transfer:
                    if next_wallet_private_key:
                        try:
                            # 创建临时钱包实例，获取下一个钱包的地址
                            temp_wallet = Wallet(use_testnet=False)
                            next_wallet_data = temp_wallet.import_wallet(next_wallet_private_key)
                            next_wallet_address = next_wallet_data['address']
                            print(f"- 链式转账已启用: BNB 将转给下一个钱包 ({next_wallet_address})")
                        except:
                            print(f"- 链式转账已启用: BNB 将转给下一个钱包 (地址获取失败)")
                    else:
                        print(f"- 链式转账已启用，但当前是最后一个钱包，BNB 将转给指定地址: {bnb_receiver_address}")
                else:
                    print(f"- 链式转账未启用: BNB 将转给指定地址: {bnb_receiver_address}")

                if transfer_bnb_on_failure:
                    print("- 领取失败时也转移 BNB: 是")
                else:
                    print("- 领取失败时也转移 BNB: 否")

            # 获取当前代币余额
            initial_balance = claimer.get_token_balance()

            # 尝试领取空投
            result = claimer.claim_airdrop(gas_price=gas_price, gas_limit=gas_limit)

            if result:
                # 获取新的代币余额
                new_balance = claimer.get_token_balance()

                # 计算获得的代币数量
                received = new_balance['balance'] - initial_balance['balance']
                if received > 0:
                    received_tokens = received / (10 ** new_balance['decimals'])
                    print(f"成功领取 {received_tokens} 个 {new_balance['symbol']} 代币!")
                    jager_tasks[task_id]['received_tokens'] = received_tokens

                    # 如果启用了自动转账功能，执行自动转账
                    if enable_auto_transfer:
                        print("\n========== 自动转账功能已启用 ==========")

                        # 1. 转出 Jager 代币
                        print(f"\n正在将 Jager 代币转出到地址: {jager_receiver_address}")
                        try:
                            # 获取最新的 Jager 代币余额
                            latest_jager_balance = claimer.get_token_balance()
                            jager_amount = latest_jager_balance['balance_token']

                            if jager_amount > 0:
                                print(f"转出 {jager_amount} Jager 代币...")
                                jager_result = claimer.transfer_jager(
                                    jager_receiver_address,
                                    jager_amount,
                                    gas_price=gas_price,
                                    gas_limit=gas_limit
                                )

                                if jager_result:
                                    print(f"Jager 代币转账成功! 交易哈希: {jager_result['transaction_hash']}")
                                    # 等待一段时间，确保交易确认
                                    print("等待 5 秒，确保交易确认...")
                                    time.sleep(5)
                                else:
                                    print("Jager 代币转账失败!")
                            else:
                                print("没有可转账的 Jager 代币余额")
                        except Exception as e:
                            print(f"Jager 代币转账过程中出错: {str(e)}")

                        # 2. 转出 BNB
                        # 确定 BNB 接收地址
                        actual_bnb_receiver = None
                        if enable_bnb_chain_transfer:
                            if next_wallet_private_key:
                                # 如果启用了链式转账，并且有下一个钱包，则将 BNB 转给下一个钱包
                                try:
                                    # 创建临时钱包实例，获取下一个钱包的地址
                                    temp_wallet = Wallet(use_testnet=False)
                                    next_wallet_data = temp_wallet.import_wallet(next_wallet_private_key)
                                    actual_bnb_receiver = next_wallet_data['address']
                                    print(f"\n启用链式转账: 将 BNB 转出到下一个钱包地址: {actual_bnb_receiver}")
                                except Exception as e:
                                    print(f"获取下一个钱包地址失败: {str(e)}")
                                    # 如果获取下一个钱包地址失败，则使用指定的 BNB 接收地址
                                    actual_bnb_receiver = bnb_receiver_address
                                    print(f"获取下一个钱包地址失败，回退到指定的 BNB 接收地址: {actual_bnb_receiver}")
                            else:
                                # 如果没有下一个钱包（当前是最后一个钱包），则使用指定的 BNB 接收地址
                                actual_bnb_receiver = bnb_receiver_address
                                print(f"\n链式转账已启用，但当前是最后一个钱包，将 BNB 转出到指定地址: {actual_bnb_receiver}")
                        else:
                            # 如果未启用链式转账，则使用指定的 BNB 接收地址
                            actual_bnb_receiver = bnb_receiver_address
                            print(f"\n链式转账未启用，将 BNB 转出到指定地址: {actual_bnb_receiver}")

                        try:
                            # 获取最新的 BNB 余额
                            bnb_balance_info = wallet.get_bnb_balance()
                            bnb_amount = bnb_balance_info['balance_bnb']

                            # 计算可转账的 BNB 数量
                            # 确保 bnb_amount 和 reserve_bnb_amount 都是浮点数
                            bnb_amount_float = float(bnb_amount)
                            reserve_bnb_amount_float = float(reserve_bnb_amount)

                            # 计算 gas 费用
                            gas_limit = claimer.bnb_gas_limit
                            gas_price_gwei = 3 if gas_price is None else float(gas_price)

                            # 基础 gas 费用
                            base_gas_fee_bnb = (gas_limit * gas_price_gwei * 1e9) / 1e18  # 转换为 BNB

                            # 添加 5% 的安全边际，确保有足够的 gas 费用
                            safety_margin = 0.05  # 5% 的安全边际
                            gas_fee_bnb = base_gas_fee_bnb * (1 + safety_margin)

                            print(f"基础 gas 费用: {base_gas_fee_bnb} BNB")
                            print(f"添加 {safety_margin * 100}% 安全边际后的 gas 费用: {gas_fee_bnb} BNB")

                            # 如果保留 BNB 数量设置为 0，则自动从转账金额中扣除 gas 费
                            if reserve_bnb_amount_float == 0:
                                # 转出全部 BNB，但扣除 gas 费
                                print(f"保留 BNB 数量设置为 0，系统将自动从转账金额中扣除 gas 费")
                                print(f"估计 gas 费用: {gas_fee_bnb} BNB")

                                # 确保有足够的 BNB 支付 gas 费
                                if bnb_amount_float <= gas_fee_bnb:
                                    print(f"错误: BNB 余额不足以支付 gas 费用。当前余额: {bnb_amount_float} BNB，需要: {gas_fee_bnb} BNB")
                                    transferable_bnb = 0
                                else:
                                    # 从总金额中扣除 gas 费
                                    transferable_bnb = bnb_amount_float - gas_fee_bnb
                                    print(f"将转出 {transferable_bnb} BNB (总余额 {bnb_amount_float} BNB 减去 gas 费 {gas_fee_bnb} BNB)")
                            else:
                                # 使用用户设置的保留金额
                                # 确保保留的 BNB 至少能支付 gas 费用
                                actual_reserve = max(reserve_bnb_amount_float, gas_fee_bnb)

                                if actual_reserve > reserve_bnb_amount_float:
                                    print(f"注意: 您设置的保留 BNB 数量 ({reserve_bnb_amount_float}) 不足以支付 gas 费用")
                                    print(f"系统将自动保留 {actual_reserve} BNB 用于支付 gas 费用")

                                transferable_bnb = max(0, bnb_amount_float - actual_reserve)

                            if transferable_bnb > 0:
                                print(f"当前 BNB 余额: {bnb_amount} BNB")
                                print(f"保留 {reserve_bnb_amount} BNB 用于 Gas")
                                print(f"转出 {transferable_bnb} BNB...")

                                bnb_result = claimer.transfer_bnb(
                                    actual_bnb_receiver,
                                    transferable_bnb,
                                    gas_price=gas_price,
                                    gas_limit=claimer.bnb_gas_limit
                                )

                                if bnb_result:
                                    print(f"BNB 转账成功! 交易哈希: {bnb_result['transaction_hash']}")
                                else:
                                    print("BNB 转账失败!")
                            else:
                                print(f"BNB 余额不足以转账。当前余额: {bnb_amount} BNB，保留: {reserve_bnb_amount} BNB")
                        except Exception as e:
                            print(f"BNB 转账过程中出错: {str(e)}")

                        print("\n========== 自动转账完成 ==========")
                else:
                    print("交易成功，但未检测到代币余额变化。可能需要等待更长时间。")

                jager_tasks[task_id]['status'] = 'completed'
            else:
                print("领取空投失败")
                jager_tasks[task_id]['status'] = 'failed'

                # 如果启用了自动转账和失败时转移 BNB 的功能
                if enable_auto_transfer and transfer_bnb_on_failure:
                    print("\n========== 领取失败，但启用了失败时转移 BNB 功能 ==========")

                    # 确定 BNB 接收地址
                    actual_bnb_receiver = None
                    if enable_bnb_chain_transfer:
                        if next_wallet_private_key:
                            # 如果启用了链式转账，并且有下一个钱包，则将 BNB 转给下一个钱包
                            try:
                                # 创建临时钱包实例，获取下一个钱包的地址
                                temp_wallet = Wallet(use_testnet=False)
                                next_wallet_data = temp_wallet.import_wallet(next_wallet_private_key)
                                actual_bnb_receiver = next_wallet_data['address']
                                print(f"\n启用链式转账: 将 BNB 转出到下一个钱包地址: {actual_bnb_receiver}")
                            except Exception as e:
                                print(f"获取下一个钱包地址失败: {str(e)}")
                                # 如果获取下一个钱包地址失败，则使用指定的 BNB 接收地址
                                actual_bnb_receiver = bnb_receiver_address
                                print(f"获取下一个钱包地址失败，回退到指定的 BNB 接收地址: {actual_bnb_receiver}")
                        else:
                            # 如果没有下一个钱包（当前是最后一个钱包），则使用指定的 BNB 接收地址
                            actual_bnb_receiver = bnb_receiver_address
                            print(f"\n链式转账已启用，但当前是最后一个钱包，将 BNB 转出到指定地址: {actual_bnb_receiver}")
                    else:
                        # 如果未启用链式转账，则使用指定的 BNB 接收地址
                        actual_bnb_receiver = bnb_receiver_address
                        print(f"\n链式转账未启用，将 BNB 转出到指定地址: {actual_bnb_receiver}")

                    try:
                        # 获取最新的 BNB 余额
                        bnb_balance_info = wallet.get_bnb_balance()
                        bnb_amount = bnb_balance_info['balance_bnb']

                        # 计算可转账的 BNB 数量
                        # 确保 bnb_amount 和 reserve_bnb_amount 都是浮点数
                        bnb_amount_float = float(bnb_amount)
                        reserve_bnb_amount_float = float(reserve_bnb_amount)

                        # 计算 gas 费用
                        gas_limit = claimer.bnb_gas_limit
                        gas_price_gwei = 3 if gas_price is None else float(gas_price)

                        # 基础 gas 费用
                        base_gas_fee_bnb = (gas_limit * gas_price_gwei * 1e9) / 1e18  # 转换为 BNB

                        # 添加 5% 的安全边际，确保有足够的 gas 费用
                        safety_margin = 0.05  # 5% 的安全边际
                        gas_fee_bnb = base_gas_fee_bnb * (1 + safety_margin)

                        print(f"基础 gas 费用: {base_gas_fee_bnb} BNB")
                        print(f"添加 {safety_margin * 100}% 安全边际后的 gas 费用: {gas_fee_bnb} BNB")

                        # 如果保留 BNB 数量设置为 0，则自动从转账金额中扣除 gas 费
                        if reserve_bnb_amount_float == 0:
                            # 转出全部 BNB，但扣除 gas 费
                            print(f"保留 BNB 数量设置为 0，系统将自动从转账金额中扣除 gas 费")
                            print(f"估计 gas 费用: {gas_fee_bnb} BNB")

                            # 确保有足够的 BNB 支付 gas 费
                            if bnb_amount_float <= gas_fee_bnb:
                                print(f"错误: BNB 余额不足以支付 gas 费用。当前余额: {bnb_amount_float} BNB，需要: {gas_fee_bnb} BNB")
                                transferable_bnb = 0
                            else:
                                # 从总金额中扣除 gas 费
                                transferable_bnb = bnb_amount_float - gas_fee_bnb
                                print(f"将转出 {transferable_bnb} BNB (总余额 {bnb_amount_float} BNB 减去 gas 费 {gas_fee_bnb} BNB)")
                        else:
                            # 使用用户设置的保留金额
                            # 确保保留的 BNB 至少能支付 gas 费用
                            actual_reserve = max(reserve_bnb_amount_float, gas_fee_bnb)

                            if actual_reserve > reserve_bnb_amount_float:
                                print(f"注意: 您设置的保留 BNB 数量 ({reserve_bnb_amount_float}) 不足以支付 gas 费用")
                                print(f"系统将自动保留 {actual_reserve} BNB 用于支付 gas 费用")

                            transferable_bnb = max(0, bnb_amount_float - actual_reserve)

                        if transferable_bnb > 0:
                            print(f"当前 BNB 余额: {bnb_amount} BNB")
                            print(f"保留 {reserve_bnb_amount} BNB 用于 Gas")
                            print(f"转出 {transferable_bnb} BNB...")

                            bnb_result = claimer.transfer_bnb(
                                actual_bnb_receiver,
                                transferable_bnb,
                                gas_price=gas_price,
                                gas_limit=claimer.bnb_gas_limit
                            )

                            if bnb_result:
                                print(f"BNB 转账成功! 交易哈希: {bnb_result['transaction_hash']}")
                            else:
                                print("BNB 转账失败!")
                        else:
                            print(f"BNB 余额不足以转账。当前余额: {bnb_amount} BNB，保留: {reserve_bnb_amount} BNB")
                    except Exception as e:
                        print(f"BNB 转账过程中出错: {str(e)}")

                    print("\n========== 失败后 BNB 转账完成 ==========")

        except Exception as e:
            print(f"发生错误: {str(e)}")
            jager_tasks[task_id]['status'] = 'failed'

        # 保存输出
        jager_tasks[task_id]['output'] = output_buffer.getvalue()

def transfer_bnb_task(task_id, private_key, to_address, amount, gas_price=None, gas_limit=None, transfer_all=False):
    """后台任务，用于转账BNB"""
    # 捕获输出
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer):
        try:
            # 创建钱包实例
            wallet = Wallet(use_testnet=False)

            # 导入钱包
            try:
                wallet_data = wallet.import_wallet(private_key)
                print(f"钱包导入成功，地址: {wallet_data['address']}")
                jager_tasks[task_id]['wallet_address'] = wallet_data['address']
            except Exception as e:
                print(f"钱包导入失败: {str(e)}")
                jager_tasks[task_id]['status'] = 'failed'
                jager_tasks[task_id]['output'] = output_buffer.getvalue()
                return

            # 创建空投领取器
            claimer = JagerAirdropClaimer(wallet, use_testnet=False)

            # 输出 gas 限制信息
            if gas_limit:
                print(f"使用自定义 Gas 限制: {gas_limit}")
            else:
                print("使用默认 Gas 限制: 21000")
                gas_limit = 21000  # 设置默认值

            # 检查是否要转出全部 BNB
            if transfer_all or amount == 0:
                # 获取当前 BNB 余额
                bnb_balance_info = wallet.get_bnb_balance()
                bnb_amount = float(bnb_balance_info['balance_bnb'])

                # 计算 gas 费用
                gas_price_gwei = 3 if gas_price is None else float(gas_price)

                # 基础 gas 费用
                base_gas_fee_bnb = (gas_limit * gas_price_gwei * 1e9) / 1e18  # 转换为 BNB

                # 添加 5% 的安全边际，确保有足够的 gas 费用
                safety_margin = 0.05  # 5% 的安全边际
                gas_fee_bnb = base_gas_fee_bnb * (1 + safety_margin)

                print(f"基础 gas 费用: {base_gas_fee_bnb} BNB")
                print(f"添加 {safety_margin * 100}% 安全边际后的 gas 费用: {gas_fee_bnb} BNB")

                print(f"当前 BNB 余额: {bnb_amount} BNB")
                print(f"估计 gas 费用: {gas_fee_bnb} BNB")

                # 确保有足够的 BNB 支付 gas 费
                if bnb_amount <= gas_fee_bnb:
                    print(f"错误: BNB 余额不足以支付 gas 费用。当前余额: {bnb_amount} BNB，需要: {gas_fee_bnb} BNB")
                    jager_tasks[task_id]['status'] = 'failed'
                    jager_tasks[task_id]['output'] = output_buffer.getvalue()
                    return

                # 从总金额中扣除 gas 费
                amount = bnb_amount - gas_fee_bnb
                print(f"将转出 {amount} BNB (总余额 {bnb_amount} BNB 减去 gas 费 {gas_fee_bnb} BNB)")

            # 转账BNB
            result = claimer.transfer_bnb(to_address, amount, gas_price, gas_limit)

            if result:
                print(f"BNB转账成功!")
                print(f"交易哈希: {result['transaction_hash']}")
                jager_tasks[task_id]['transaction_hash'] = result['transaction_hash']
                jager_tasks[task_id]['status'] = 'completed'
            else:
                print("BNB转账失败")
                jager_tasks[task_id]['status'] = 'failed'
        except Exception as e:
            print(f"发生错误: {str(e)}")
            jager_tasks[task_id]['status'] = 'failed'

        # 保存输出
        jager_tasks[task_id]['output'] = output_buffer.getvalue()

def transfer_jager_task(task_id, private_key, to_address, amount, gas_price=None, gas_limit=None):
    """后台任务，用于转账Jager代币"""
    # 捕获输出
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer):
        try:
            # 创建钱包实例
            wallet = Wallet(use_testnet=False)

            # 导入钱包
            try:
                wallet_data = wallet.import_wallet(private_key)
                print(f"钱包导入成功，地址: {wallet_data['address']}")
                jager_tasks[task_id]['wallet_address'] = wallet_data['address']
            except Exception as e:
                print(f"钱包导入失败: {str(e)}")
                jager_tasks[task_id]['status'] = 'failed'
                jager_tasks[task_id]['output'] = output_buffer.getvalue()
                return

            # 创建空投领取器
            claimer = JagerAirdropClaimer(wallet, use_testnet=False)

            # 输出 gas 限制信息
            if gas_limit:
                print(f"使用自定义 Gas 限制: {gas_limit}")
            else:
                print("使用默认 Gas 限制: 300000")

            # 转账Jager代币
            result = claimer.transfer_jager(to_address, amount, gas_price, gas_limit)

            if result:
                print(f"Jager代币转账成功!")
                print(f"交易哈希: {result['transaction_hash']}")
                jager_tasks[task_id]['transaction_hash'] = result['transaction_hash']
                jager_tasks[task_id]['status'] = 'completed'
            else:
                print("Jager代币转账失败")
                jager_tasks[task_id]['status'] = 'failed'
        except Exception as e:
            print(f"发生错误: {str(e)}")
            jager_tasks[task_id]['status'] = 'failed'

        # 保存输出
        jager_tasks[task_id]['output'] = output_buffer.getvalue()

@app.route('/jager')
def jager_index():
    """渲染Jager空投领取页面"""
    return render_template('jager.html')

@app.route('/transfer')
def transfer_index():
    """渲染代币转账页面"""
    return render_template('transfer.html')

@app.route('/api/claim-jager', methods=['POST'])
def claim_jager():
    """领取Jager空投"""
    try:
        private_key = request.json.get('private_key')
        gas_price = request.json.get('gas_price')
        gas_limit = request.json.get('gas_limit')

        # 获取自动转账相关参数
        enable_auto_transfer = request.json.get('enable_auto_transfer', False)
        jager_receiver_address = request.json.get('jager_receiver_address')
        bnb_receiver_address = request.json.get('bnb_receiver_address')
        reserve_bnb_amount = request.json.get('reserve_bnb_amount')

        # 获取链式转账相关参数
        enable_bnb_chain_transfer = request.json.get('enable_bnb_chain_transfer', False)
        transfer_bnb_on_failure = request.json.get('transfer_bnb_on_failure', False)
        next_wallet_private_key = request.json.get('next_wallet_private_key')

        if not private_key:
            return jsonify({'success': False, 'error': '请提供私钥'}), 400

        # 如果启用了自动转账，检查接收地址
        if enable_auto_transfer:
            if not jager_receiver_address:
                return jsonify({'success': False, 'error': '请提供 Jager 代币接收地址'}), 400
            if not enable_bnb_chain_transfer and not bnb_receiver_address:
                return jsonify({'success': False, 'error': '请提供 BNB 接收地址或启用链式转账'}), 400

            # 如果启用了链式转账，检查下一个钱包私钥
            if enable_bnb_chain_transfer and not next_wallet_private_key:
                # 这不是错误，只是意味着这是最后一个钱包，将使用指定的 BNB 接收地址
                enable_bnb_chain_transfer = False

        # 转换gas_price为浮点数（如果有）
        if gas_price:
            try:
                gas_price = float(gas_price)
            except ValueError:
                return jsonify({'success': False, 'error': 'Gas价格必须是数字'}), 400
        else:
            gas_price = None

        # 转换gas_limit为整数（如果有）
        if gas_limit:
            try:
                gas_limit = int(gas_limit)
            except ValueError:
                return jsonify({'success': False, 'error': 'Gas限制必须是整数'}), 400
        else:
            gas_limit = None

        # 转换reserve_bnb_amount为浮点数（如果有）
        if reserve_bnb_amount is not None:
            try:
                reserve_bnb_amount = float(reserve_bnb_amount)
                # 确保值不为负数
                if reserve_bnb_amount < 0:
                    reserve_bnb_amount = 0.0
            except ValueError:
                return jsonify({'success': False, 'error': '保留 BNB 数量必须是数字'}), 400
        else:
            reserve_bnb_amount = 0.0  # 默认值为 0

        # 创建任务ID
        task_id = str(int(time.time()))

        # 初始化任务状态
        jager_tasks[task_id] = {
            'status': 'running',
            'output': '',
            'wallet_address': '',
            'received_tokens': 0,
            'enable_auto_transfer': enable_auto_transfer,
            'jager_receiver_address': jager_receiver_address,
            'bnb_receiver_address': bnb_receiver_address,
            'reserve_bnb_amount': reserve_bnb_amount,
            'enable_bnb_chain_transfer': enable_bnb_chain_transfer,
            'transfer_bnb_on_failure': transfer_bnb_on_failure,
            'next_wallet_private_key': next_wallet_private_key
        }

        # 启动后台任务
        thread = threading.Thread(
            target=claim_jager_airdrop_task,
            args=(
                task_id,
                private_key,
                gas_price,
                gas_limit,
                enable_auto_transfer,
                jager_receiver_address,
                bnb_receiver_address,
                reserve_bnb_amount,
                enable_bnb_chain_transfer,
                transfer_bnb_on_failure,
                next_wallet_private_key
            )
        )
        thread.daemon = True
        thread.start()

        return jsonify({'success': True, 'task_id': task_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/jager-task-status/<task_id>')
def jager_task_status(task_id):
    """获取Jager空投领取任务状态"""
    if task_id not in jager_tasks:
        return jsonify({'success': False, 'error': '任务不存在'}), 404

    return jsonify({
        'success': True,
        'task': jager_tasks[task_id]
    })

@app.route('/api/transfer-bnb-async', methods=['POST'])
def transfer_bnb_async():
    """异步转账BNB到指定地址"""
    try:
        private_key = request.json.get('private_key')
        to_address = request.json.get('to_address')
        amount = request.json.get('amount')
        gas_price = request.json.get('gas_price')
        gas_limit = request.json.get('gas_limit')
        transfer_all = request.json.get('transfer_all', False)  # 新增参数，是否转出全部 BNB

        if not private_key:
            return jsonify({'success': False, 'error': '请提供私钥'}), 400
        if not to_address:
            return jsonify({'success': False, 'error': '请提供目标地址'}), 400

        # 如果不是转出全部 BNB，则需要提供转账金额
        if not transfer_all and not amount:
            return jsonify({'success': False, 'error': '请提供转账金额或选择转出全部 BNB'}), 400

        # 转换amount为浮点数（如果有）
        if amount:
            try:
                amount = float(amount)
            except ValueError:
                return jsonify({'success': False, 'error': '转账金额必须是数字'}), 400
        else:
            # 如果是转出全部 BNB，则设置 amount 为 0，后续会自动计算
            amount = 0

        # 转换gas_price为浮点数（如果有）
        if gas_price:
            try:
                gas_price = float(gas_price)
            except ValueError:
                return jsonify({'success': False, 'error': 'Gas价格必须是数字'}), 400
        else:
            gas_price = None

        # 转换gas_limit为整数（如果有）
        if gas_limit:
            try:
                gas_limit = int(gas_limit)
            except ValueError:
                return jsonify({'success': False, 'error': 'Gas限制必须是整数'}), 400
        else:
            gas_limit = None

        # 创建任务ID
        task_id = str(int(time.time()))

        # 初始化任务状态
        jager_tasks[task_id] = {
            'status': 'running',
            'output': '',
            'wallet_address': '',
            'transaction_hash': ''
        }

        # 启动后台任务
        thread = threading.Thread(target=transfer_bnb_task, args=(task_id, private_key, to_address, amount, gas_price, gas_limit, transfer_all))
        thread.daemon = True
        thread.start()

        return jsonify({'success': True, 'task_id': task_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/transfer-jager-async', methods=['POST'])
def transfer_jager_async():
    """异步转账Jager代币到指定地址"""
    try:
        private_key = request.json.get('private_key')
        to_address = request.json.get('to_address')
        amount = request.json.get('amount')
        gas_price = request.json.get('gas_price')
        gas_limit = request.json.get('gas_limit')

        if not private_key:
            return jsonify({'success': False, 'error': '请提供私钥'}), 400
        if not to_address:
            return jsonify({'success': False, 'error': '请提供目标地址'}), 400
        if not amount:
            return jsonify({'success': False, 'error': '请提供转账金额'}), 400

        # 转换amount为浮点数
        try:
            amount = float(amount)
        except ValueError:
            return jsonify({'success': False, 'error': '转账金额必须是数字'}), 400

        # 转换gas_price为浮点数（如果有）
        if gas_price:
            try:
                gas_price = float(gas_price)
            except ValueError:
                return jsonify({'success': False, 'error': 'Gas价格必须是数字'}), 400
        else:
            gas_price = None

        # 转换gas_limit为整数（如果有）
        if gas_limit:
            try:
                gas_limit = int(gas_limit)
            except ValueError:
                return jsonify({'success': False, 'error': 'Gas限制必须是整数'}), 400
        else:
            gas_limit = None

        # 创建任务ID
        task_id = str(int(time.time()))

        # 初始化任务状态
        jager_tasks[task_id] = {
            'status': 'running',
            'output': '',
            'wallet_address': '',
            'transaction_hash': ''
        }

        # 启动后台任务
        thread = threading.Thread(target=transfer_jager_task, args=(task_id, private_key, to_address, amount, gas_price, gas_limit))
        thread.daemon = True
        thread.start()

        return jsonify({'success': True, 'task_id': task_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
