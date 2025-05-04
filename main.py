from flask import Flask, request, jsonify, render_template
from jager_app.wallet import Wallet
from dotenv import load_dotenv
import os
import json

# 加载环境变量
load_dotenv()

app = Flask(__name__, template_folder='jager_app/templates', static_folder='jager_app/static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')

# 全局钱包实例
wallet = None

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

if __name__ == '__main__':
    app.run(debug=True)
