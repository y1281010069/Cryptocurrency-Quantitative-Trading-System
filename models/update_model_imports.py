#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量更新所有模型文件的导入语句，使其支持相对导入和直接运行"""
import os
import re
import sys

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 新的导入模板
new_import_template = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
{docstring}
import os
import sys

# 添加当前目录到Python路径以便直接运行脚本
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 尝试相对导入，如果失败则使用绝对导入
try:
    from .base_model import BaseModel
except ImportError:
    from base_model import BaseModel'''


def update_file(file_path):
    """更新单个文件的导入语句"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取文档字符串
        match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if match:
            docstring = match.group(0)
        else:
            # 如果没有文档字符串，使用默认的
            file_name = os.path.basename(file_path)
            table_name = file_name.replace('_model.py', '')
            docstring = f"""\n{table_name} 表模型类\n"""
        
        # 替换旧的导入语句
        # 先找到旧的导入语句的位置
        old_import_pattern = r'from base_model import BaseModel'
        match = re.search(old_import_pattern, content)
        
        if match:
            # 提取文件开头到导入语句前的内容
            header_end = match.start()
            header = content[:header_end]
            
            # 提取导入语句后的内容
            body_start = match.end()
            body = content[body_start:]
            
            # 构建新的文件内容
            new_content = header + new_import_template.format(docstring=docstring) + body
            
            # 写入更新后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"已更新文件: {file_path}")
        else:
            print(f"跳过文件（未找到匹配的导入模式）: {file_path}")
            
    except Exception as e:
        print(f"处理文件时出错 {file_path}: {str(e)}")


def main():
    """主函数"""
    # 获取所有模型文件
    model_files = []
    for file_name in os.listdir(current_dir):
        if file_name.endswith('_model.py') and file_name != 'update_model_imports.py':
            model_files.append(os.path.join(current_dir, file_name))
    
    print(f"找到 {len(model_files)} 个模型文件需要更新")
    
    # 更新每个模型文件
    for file_path in model_files:
        update_file(file_path)
    
    print("所有模型文件更新完成！")


if __name__ == "__main__":
    main()