"""
调试Jager空投领取过程
"""

import sys
import traceback
from jager_app.wallet import Wallet
from claim_jager_airdrop import JagerAirdropClaimer

def debug_claim_jager(private_key, next_wallet_private_key=None):
    """调试Jager空投领取过程"""
    try:
        print("开始调试Jager空投领取过程...")
        
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
            return
            
        # 创建空投领取器
        try:
            claimer = JagerAirdropClaimer(wallet, use_testnet=False)
            print("空投领取器创建成功")
        except Exception as e:
            print(f"空投领取器创建失败: {str(e)}")
            return
            
        # 设置gas参数
        gas_price = 3.0
        gas_limit = 1000000
        print(f"Gas价格: {gas_price} Gwei")
        print(f"Gas限制: {gas_limit}")
        
        # 尝试领取空投
        try:
            print("\n尝试领取空投...")
            result = claimer.claim_airdrop(gas_price=gas_price, gas_limit=gas_limit)
            print(f"领取结果: {result}")
        except Exception as e:
            print(f"领取空投失败: {str(e)}")
            print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
            
        # 获取代币余额
        try:
            print("\n获取代币余额...")
            balance_info = claimer.get_token_balance()
            print(f"代币余额: {balance_info}")
        except Exception as e:
            print(f"获取代币余额失败: {str(e)}")
            print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
            
        # 尝试转账BNB
        try:
            print("\n尝试转账BNB...")
            bnb_receiver_address = "0x83ae7ef04e4F00a94208cE31010Efd9d94B5BbC8"
            reserve_bnb_amount = 0.005
            
            # 获取BNB余额
            bnb_balance_info = wallet.get_bnb_balance()
            bnb_amount = bnb_balance_info['balance_bnb']
            print(f"BNB余额: {bnb_amount} BNB")
            
            # 计算可转账的BNB数量
            bnb_amount_float = float(bnb_amount)
            reserve_bnb_amount_float = float(reserve_bnb_amount)
            
            # 计算gas费用
            gas_limit_bnb = claimer.bnb_gas_limit
            gas_price_gwei = 3.0
            
            # 基础gas费用
            base_gas_fee_bnb = (gas_limit_bnb * gas_price_gwei * 1e9) / 1e18  # 转换为BNB
            
            # 添加5%的安全边际
            safety_margin = 0.05
            gas_fee_bnb = base_gas_fee_bnb * (1 + safety_margin)
            
            print(f"基础gas费用: {base_gas_fee_bnb} BNB")
            print(f"添加{safety_margin * 100}%安全边际后的gas费用: {gas_fee_bnb} BNB")
            
            # 如果保留BNB数量设置为0，则自动从转账金额中扣除gas费
            if reserve_bnb_amount_float == 0:
                print(f"保留BNB数量设置为0，系统将自动从转账金额中扣除gas费")
                
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
                    bnb_receiver_address,
                    transferable_bnb,
                    gas_price=gas_price,
                    gas_limit=gas_limit_bnb
                )
                
                print(f"BNB转账结果: {bnb_result}")
            else:
                print(f"BNB余额不足以转账。当前余额: {bnb_amount} BNB，保留: {reserve_bnb_amount} BNB")
        except Exception as e:
            print(f"转账BNB失败: {str(e)}")
            print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
            
    except Exception as e:
        print(f"调试过程中发生错误: {str(e)}")
        print(f"错误堆栈跟踪:\n{traceback.format_exc()}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        private_key = sys.argv[1]
        next_wallet_private_key = sys.argv[2] if len(sys.argv) > 2 else None
        debug_claim_jager(private_key, next_wallet_private_key)
    else:
        print("请提供私钥作为命令行参数")
