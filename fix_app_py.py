"""
修复app.py文件中的语法错误
"""

def fix_app_py():
    """修复app.py文件中的语法错误"""
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复字符串文本未终止的问题
    content = content.replace('print(f"错误堆栈跟踪:\n{error_trace}")', 'print(f"错误堆栈跟踪:\\n{error_trace}")')
    
    # 确保文件以换行符结束
    if not content.endswith('\n'):
        content += '\n'
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("已修复app.py文件中的语法错误")

if __name__ == "__main__":
    fix_app_py()
