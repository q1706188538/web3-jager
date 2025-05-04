"""
修复gas_price处理的脚本
"""

import re

def fix_gas_price_in_file(file_path):
    """修复文件中的gas_price处理代码"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复transfer_bnb方法中的gas_price处理
    pattern1 = r"""            # 设置Gas价格
            if gas_price is None:
                gas_price = 3  # 默认使用3 Gwei
                print\(f"使用默认Gas价格: {gas_price} Gwei"\)
            else:
                print\(f"使用指定Gas价格: {gas_price} Gwei"\)"""
    
    replacement1 = """            # 设置Gas价格
            gas_price_value = 3  # 默认使用3 Gwei
            if gas_price is None:
                print(f"使用默认Gas价格: {gas_price_value} Gwei")
            else:
                try:
                    gas_price_value = float(gas_price)
                    print(f"使用指定Gas价格: {gas_price_value} Gwei")
                except (ValueError, TypeError) as e:
                    print(f"警告: 无法将gas_price '{gas_price}' 转换为数字: {str(e)}")
                    print(f"使用默认Gas价格: {gas_price_value} Gwei")"""
    
    content = re.sub(pattern1, replacement1, content)
    
    # 修复wallet.transfer_bnb调用中的gas_price参数
    pattern2 = r"result = self\.wallet\.transfer_bnb\(to_address, amount_bnb, gas_price\)"
    replacement2 = "result = self.wallet.transfer_bnb(to_address, amount_bnb, gas_price_value)"
    
    content = re.sub(pattern2, replacement2, content)
    
    # 修复直接构建交易中的gas_price处理
    pattern3 = r"""                    # 设置Gas价格
                    if gas_price:
                        tx\['gasPrice'\] = self\.w3\.to_wei\(gas_price, 'gwei'\)
                    else:
                        tx\['gasPrice'\] = self\.w3\.to_wei\(3, 'gwei'\)  # 默认3 Gwei"""
    
    replacement3 = """                    # 设置Gas价格
                    tx['gasPrice'] = self.w3.to_wei(gas_price_value, 'gwei')"""
    
    content = re.sub(pattern3, replacement3, content)
    
    # 修复transfer_jager方法中的gas_price处理
    pattern4 = r"""            # 设置Gas价格
            if gas_price is None:
                gas_price = 3  # 默认使用3 Gwei
                print\(f"使用默认Gas价格: {gas_price} Gwei"\)
            else:
                print\(f"使用指定Gas价格: {gas_price} Gwei"\)"""
    
    replacement4 = """            # 设置Gas价格
            gas_price_value = 3  # 默认使用3 Gwei
            if gas_price is None:
                print(f"使用默认Gas价格: {gas_price_value} Gwei")
            else:
                try:
                    gas_price_value = float(gas_price)
                    print(f"使用指定Gas价格: {gas_price_value} Gwei")
                except (ValueError, TypeError) as e:
                    print(f"警告: 无法将gas_price '{gas_price}' 转换为数字: {str(e)}")
                    print(f"使用默认Gas价格: {gas_price_value} Gwei")"""
    
    content = re.sub(pattern4, replacement4, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已修复 {file_path} 中的gas_price处理代码")

if __name__ == "__main__":
    fix_gas_price_in_file("claim_jager_airdrop.py")
