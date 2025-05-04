"""
修复错误处理的脚本
"""

import re

def fix_error_handling_in_file(file_path):
    """修复文件中的错误处理代码"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复异常处理代码
    pattern = r"""        except Exception as e:
            print\(f"发生错误: {str\(e\)}"\)
            jager_tasks\[task_id\]\['status'\] = 'failed'"""
    
    replacement = """        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"发生错误: {str(e)}")
            print(f"错误堆栈跟踪:\\n{error_trace}")
            jager_tasks[task_id]['status'] = 'failed'"""
    
    content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已修复 {file_path} 中的错误处理代码")

if __name__ == "__main__":
    fix_error_handling_in_file("app.py")
