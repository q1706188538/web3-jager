"""
调试api_deadline是否为None
"""

import sys
import traceback
from jager_app.wallet import Wallet
from claim_jager_airdrop import JagerAirdropClaimer

def debug_api_deadline(private_key):
    """调试api_deadline是否为None"""
    try:
        print("开始调试api_deadline是否为None...")
        
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
            
        # 获取签名
        try:
            print("\n获取签名...")
            signature = claimer.get_claim_signature()
            print(f"签名: {signature}")
            print(f"签名类型: {type(signature)}")
            
            # 检查api_deadline
            print(f"\napi_deadline: {claimer.api_deadline}")
            print(f"api_deadline类型: {type(claimer.api_deadline)}")
            
            if claimer.api_deadline is None:
                print("错误: api_deadline为None")
            else:
                print("api_deadline不为None")
                
            # 检查api_amount
            print(f"\napi_amount: {claimer.api_amount}")
            print(f"api_amount类型: {type(claimer.api_amount)}")
            
            if claimer.api_amount is None:
                print("错误: api_amount为None")
            else:
                print("api_amount不为None")
                
        except Exception as e:
            print(f"获取签名失败: {str(e)}")
            print(f"错误堆栈跟踪:\n{traceback.format_exc()}")
            
    except Exception as e:
        print(f"调试过程中发生错误: {str(e)}")
        print(f"错误堆栈跟踪:\n{traceback.format_exc()}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        private_key = sys.argv[1]
        debug_api_deadline(private_key)
    else:
        print("请提供私钥作为命令行参数")
