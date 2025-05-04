"""
调试app.py中的claim_jager_airdrop_task函数
"""

import io
import time
import traceback
from contextlib import redirect_stdout
from jager_app.wallet import Wallet
from claim_jager_airdrop import JagerAirdropClaimer

def debug_claim_jager_airdrop_task(private_key, gas_price=None, gas_limit=None,
                       enable_auto_transfer=False, jager_receiver_address=None,
                       bnb_receiver_address=None, reserve_bnb_amount=0.0,
                       enable_bnb_chain_transfer=False, transfer_bnb_on_failure=False,
                       next_wallet_private_key=None):
    """调试claim_jager_airdrop_task函数"""
    # 捕获输出
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer):
        try:
            # 记录参数信息（不包含私钥内容）
            print(f"开始调试Jager空投领取任务")
            print(f"参数信息:")
            print(f"- gas_price: {gas_price}")
            print(f"- gas_limit: {gas_limit}")
            print(f"- enable_auto_transfer: {enable_auto_transfer}")
            print(f"- jager_receiver_address: {jager_receiver_address}")
            print(f"- bnb_receiver_address: {bnb_receiver_address}")
            print(f"- reserve_bnb_amount: {reserve_bnb_amount}")
            print(f"- enable_bnb_chain_transfer: {enable_bnb_chain_transfer}")
            print(f"- transfer_bnb_on_failure: {transfer_bnb_on_failure}")
            
            # 输出私钥信息（只显示前6位和后6位）
            if private_key:
                masked_key = private_key[:6] + "..." + private_key[-6:]
                print(f"私钥: {masked_key}")
                print(f"私钥类型: {type(private_key)}")
                print(f"私钥长度: {len(private_key)}")
            else:
                print("错误: 私钥为空")
                return
                
            # 输出下一个钱包私钥信息
            if next_wallet_private_key:
                masked_next_key = next_wallet_private_key[:6] + "..." + next_wallet_private_key[-6:]
                print(f"下一个钱包私钥: {masked_next_key}")
                print(f"下一个钱包私钥类型: {type(next_wallet_private_key)}")
                print(f"下一个钱包私钥长度: {len(next_wallet_private_key)}")
            
            # 创建钱包实例
            wallet = Wallet(use_testnet=False)
            
            # 导入钱包
            try:
                wallet_data = wallet.import_wallet(private_key)
                print(f"钱包导入成功，地址: {wallet_data['address']}")
            except Exception as e:
                print(f"钱包导入失败: {str(e)}")
                print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
                return
                
            # 创建空投领取器
            try:
                claimer = JagerAirdropClaimer(wallet, use_testnet=False)
                print("空投领取器创建成功")
            except Exception as e:
                print(f"空投领取器创建失败: {str(e)}")
                print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
                return
                
            # 输出gas限制信息
            if gas_limit:
                print(f"使用自定义Gas限制: {gas_limit}")
            else:
                print("使用默认Gas限制: 1000000")
                gas_limit = 1000000  # 设置默认值
                
            # 输出gas价格信息
            if gas_price is not None:
                try:
                    gas_price_float = float(gas_price)
                    print(f"使用自定义Gas价格: {gas_price_float} Gwei")
                except (ValueError, TypeError) as e:
                    print(f"警告: 无法将gas_price '{gas_price}' 转换为数字: {str(e)}")
                    gas_price = None
                    print("使用默认Gas价格: 3 Gwei")
            else:
                print("使用默认Gas价格: 3 Gwei")
                
            # 输出自动转账信息
            if enable_auto_transfer:
                print("\n========== 自动转账功能已启用 ==========")
                print(f"- Jager接收地址: {jager_receiver_address}")
                print(f"- BNB接收地址: {bnb_receiver_address}")
                print(f"- 保留BNB数量: {reserve_bnb_amount}")
                
                if enable_bnb_chain_transfer:
                    print("- 链式转账: 启用")
                    if next_wallet_private_key:
                        print("- 下一个钱包私钥: 已提供")
                    else:
                        print("- 下一个钱包私钥: 未提供")
                else:
                    print("- 链式转账: 禁用")
                    
                if transfer_bnb_on_failure:
                    print("- 领取失败时也转移BNB: 是")
                else:
                    print("- 领取失败时也转移BNB: 否")
                    
            # 获取当前代币余额
            try:
                print("\n获取当前代币余额...")
                initial_balance = claimer.get_token_balance()
                print(f"当前代币余额: {initial_balance}")
            except Exception as e:
                print(f"获取当前代币余额失败: {str(e)}")
                print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
                
            # 尝试领取空投
            try:
                print("\n尝试领取空投...")
                result = claimer.claim_airdrop(gas_price=gas_price, gas_limit=gas_limit)
                print(f"领取结果: {result}")
            except Exception as e:
                print(f"领取空投失败: {str(e)}")
                print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
                
            # 如果启用了自动转账功能，执行自动转账
            if enable_auto_transfer:
                print("\n========== 自动转账功能已启用 ==========")
                
                # 1. 转出Jager代币
                try:
                    print(f"\n正在将Jager代币转出到地址: {jager_receiver_address}")
                    
                    # 获取最新的Jager代币余额
                    latest_jager_balance = claimer.get_token_balance()
                    jager_amount = latest_jager_balance['balance_token']
                    
                    if jager_amount > 0:
                        print(f"转出{jager_amount} Jager代币...")
                        jager_result = claimer.transfer_jager(
                            jager_receiver_address,
                            jager_amount,
                            gas_price=gas_price,
                            gas_limit=gas_limit
                        )
                        
                        print(f"Jager代币转账结果: {jager_result}")
                    else:
                        print("没有可转账的Jager代币余额")
                except Exception as e:
                    print(f"Jager代币转账过程中出错: {str(e)}")
                    print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
                    
                # 2. 转出BNB
                try:
                    print("\n正在转出BNB...")
                    
                    # 确定BNB接收地址
                    actual_bnb_receiver = None
                    if enable_bnb_chain_transfer:
                        if next_wallet_private_key:
                            # 如果启用了链式转账，并且有下一个钱包，则将BNB转给下一个钱包
                            try:
                                # 创建临时钱包实例，获取下一个钱包的地址
                                temp_wallet = Wallet(use_testnet=False)
                                next_wallet_data = temp_wallet.import_wallet(next_wallet_private_key)
                                actual_bnb_receiver = next_wallet_data['address']
                                print(f"\n启用链式转账: 将BNB转出到下一个钱包地址: {actual_bnb_receiver}")
                            except Exception as e:
                                print(f"获取下一个钱包地址失败: {str(e)}")
                                print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
                                # 如果获取下一个钱包地址失败，则使用指定的BNB接收地址
                                actual_bnb_receiver = bnb_receiver_address
                                print(f"获取下一个钱包地址失败，回退到指定的BNB接收地址: {actual_bnb_receiver}")
                        else:
                            # 如果没有下一个钱包（当前是最后一个钱包），则使用指定的BNB接收地址
                            actual_bnb_receiver = bnb_receiver_address
                            print(f"\n链式转账已启用，但当前是最后一个钱包，将BNB转出到指定地址: {actual_bnb_receiver}")
                    else:
                        # 如果未启用链式转账，则使用指定的BNB接收地址
                        actual_bnb_receiver = bnb_receiver_address
                        print(f"\n链式转账未启用，将BNB转出到指定地址: {actual_bnb_receiver}")
                        
                    # 获取最新的BNB余额
                    bnb_balance_info = wallet.get_bnb_balance()
                    bnb_amount = bnb_balance_info['balance_bnb']
                    
                    # 计算可转账的BNB数量
                    # 确保bnb_amount和reserve_bnb_amount都是浮点数
                    bnb_amount_float = float(bnb_amount)
                    reserve_bnb_amount_float = float(reserve_bnb_amount)
                    
                    # 计算gas费用
                    gas_limit_bnb = claimer.bnb_gas_limit
                    gas_price_gwei = 3  # 默认值
                    if gas_price is not None:
                        try:
                            gas_price_gwei = float(gas_price)
                        except (ValueError, TypeError) as e:
                            print(f"警告: 无法将gas_price '{gas_price}' 转换为数字: {str(e)}")
                            print(f"使用默认Gas价格: {gas_price_gwei} Gwei")
                            
                    # 基础gas费用
                    base_gas_fee_bnb = (gas_limit_bnb * gas_price_gwei * 1e9) / 1e18  # 转换为BNB
                    
                    # 添加5%的安全边际，确保有足够的gas费用
                    safety_margin = 0.05  # 5%的安全边际
                    gas_fee_bnb = base_gas_fee_bnb * (1 + safety_margin)
                    
                    print(f"基础gas费用: {base_gas_fee_bnb} BNB")
                    print(f"添加{safety_margin * 100}%安全边际后的gas费用: {gas_fee_bnb} BNB")
                    
                    # 如果保留BNB数量设置为0，则自动从转账金额中扣除gas费
                    if reserve_bnb_amount_float == 0:
                        # 转出全部BNB，但扣除gas费
                        print(f"保留BNB数量设置为0，系统将自动从转账金额中扣除gas费")
                        print(f"估计gas费用: {gas_fee_bnb} BNB")
                        
                        # 确保有足够的BNB支付gas费
                        if bnb_amount_float <= gas_fee_bnb:
                            print(f"错误: BNB余额不足以支付gas费用。当前余额: {bnb_amount_float} BNB，需要: {gas_fee_bnb} BNB")
                            transferable_bnb = 0
                        else:
                            # 从总金额中扣除gas费
                            transferable_bnb = bnb_amount_float - gas_fee_bnb
                            print(f"将转出{transferable_bnb} BNB (总余额{bnb_amount_float} BNB减去gas费{gas_fee_bnb} BNB)")
                    else:
                        # 使用用户设置的保留金额
                        # 确保保留的BNB至少能支付gas费用
                        actual_reserve = max(reserve_bnb_amount_float, gas_fee_bnb)
                        
                        if actual_reserve > reserve_bnb_amount_float:
                            print(f"注意: 您设置的保留BNB数量({reserve_bnb_amount_float})不足以支付gas费用")
                            print(f"系统将自动保留{actual_reserve} BNB用于支付gas费用")
                            
                        transferable_bnb = max(0, bnb_amount_float - actual_reserve)
                        
                    if transferable_bnb > 0:
                        print(f"当前BNB余额: {bnb_amount} BNB")
                        print(f"保留{reserve_bnb_amount} BNB用于Gas")
                        print(f"转出{transferable_bnb} BNB...")
                        
                        bnb_result = claimer.transfer_bnb(
                            actual_bnb_receiver,
                            transferable_bnb,
                            gas_price=gas_price,
                            gas_limit=gas_limit_bnb
                        )
                        
                        print(f"BNB转账结果: {bnb_result}")
                    else:
                        print(f"BNB余额不足以转账。当前余额: {bnb_amount} BNB，保留: {reserve_bnb_amount} BNB")
                except Exception as e:
                    print(f"BNB转账过程中出错: {str(e)}")
                    print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
                    
                print("\n========== 自动转账完成 ==========")
                
        except Exception as e:
            print(f"调试过程中发生错误: {str(e)}")
            print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
            
    # 返回输出
    return output_buffer.getvalue()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        private_key = sys.argv[1]
        next_wallet_private_key = sys.argv[2] if len(sys.argv) > 2 else None
        
        output = debug_claim_jager_airdrop_task(
            private_key,
            gas_price=3.0,
            gas_limit=1000000,
            enable_auto_transfer=True,
            jager_receiver_address="0x83ae7ef04e4F00a94208cE31010Efd9d94B5BbC8",
            bnb_receiver_address="0x83ae7ef04e4F00a94208cE31010Efd9d94B5BbC8",
            reserve_bnb_amount=0.005,
            enable_bnb_chain_transfer=True,
            transfer_bnb_on_failure=True,
            next_wallet_private_key=next_wallet_private_key
        )
        
        print(output)
    else:
        print("请提供私钥作为命令行参数")
