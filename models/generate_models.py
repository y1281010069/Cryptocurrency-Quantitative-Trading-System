#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动生成数据库表模型类脚本
"""
import os
import logging
from typing import Dict, List
from db_connection import DatabaseConnection, db

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)

class ModelGenerator:
    """数据库表模型生成器"""
    
    def __init__(self, db_conn: DatabaseConnection):
        """初始化模型生成器
        
        Args:
            db_conn: 数据库连接对象
        """
        self.db = db_conn
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
    
    def generate_model_class(self, table_name: str) -> str:
        """为指定表生成模型类代码
        
        Args:
            table_name: 表名
            
        Returns:
            str: 模型类代码
        """
        # 获取表结构
        table_structure = self.db.get_table_structure(table_name)
        if not table_structure:
            logger.warning(f"无法获取表 '{table_name}' 的结构")
            return ""
        
        # 查找主键
        primary_key = "id"
        for field in table_structure:
            if field.get('Key') == 'PRI':
                primary_key = field['Field']
                break
        
        # 生成类注释
        class_comment = f'"""\n{table_name} 表模型类\n"""'
        
        # 生成字段注释
        fields_comment = []
        fields_comment.append("    # 表字段信息")
        for field in table_structure:
            field_info = f"    # {field['Field']}: {field['Type']}"
            if field.get('Null') == 'NO':
                field_info += " (NOT NULL)"
            if field.get('Key') == 'PRI':
                field_info += " (PRIMARY KEY)"
            if field.get('Default') is not None:
                field_info += f" DEFAULT {field['Default']}"
            fields_comment.append(field_info)
        
        fields_comment_str = "\n".join(fields_comment)
        
        # 生成驼峰命名的类名
        class_name = self.camel_case(table_name)
        
        # 检查是否是MySQL保留关键字
        mysql_reserved_words = {
            'order', 'select', 'from', 'where', 'insert', 'update', 'delete',
            'create', 'drop', 'alter', 'table', 'database', 'index', 'view',
            'procedure', 'function', 'trigger', 'event', 'case', 'when', 'then',
            'else', 'end', 'join', 'inner', 'outer', 'left', 'right', 'full',
            'on', 'group', 'by', 'having', 'order', 'limit', 'offset', 'union',
            'all', 'distinct', 'as', 'like', 'in', 'between', 'and', 'or',
            'not', 'exists', 'is', 'null', 'true', 'false', 'default', 'auto_increment'
        }
        
        # 如果表名是保留关键字，使用反引号包裹
        safe_table_name = f"`{table_name}`" if table_name.lower() in mysql_reserved_words else table_name
        
        # 生成模型类代码
        model_code = '''
#!/usr/bin/env python
# -*- coding: utf-8 -*-
{class_comment}
import os
import sys

# 添加当前目录到Python路径以便直接运行脚本
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 尝试相对导入，如果失败则使用绝对导入
try:
    from .base_model import BaseModel
except ImportError:
    from base_model import BaseModel


class {class_name}(BaseModel):
    """{table_name} 表模型"""
    
    table_name = "{table_name}"
    primary_key = "{primary_key}"
    
{fields_comment_str}

    def __init__(self, db_conn=None):
        """初始化模型
        
        Args:
            db_conn: 数据库连接对象, 如果为None则使用全局的db实例
        """
        super().__init__(db_conn)


# 创建模型实例供全局使用
{table_name}_model = {class_name}()
'''.format(
            class_comment=class_comment,
            class_name=class_name,
            table_name=table_name,
            primary_key=primary_key,
            fields_comment_str=fields_comment_str
        )
        
        return model_code.strip()
    
    def camel_case(self, table_name: str) -> str:
        """将下划线命名转换为驼峰命名（首字母大写）
        
        Args:
            table_name: 下划线命名的表名
            
        Returns:
            str: 驼峰命名的类名
        """
        # 处理表名前缀（如果有）
        parts = table_name.split('_')
        return ''.join(part.capitalize() for part in parts)
    
    def generate_all_models(self) -> List[str]:
        """为数据库中所有表生成模型类
        
        Returns:
            List[str]: 生成的文件名列表
        """
        # 获取所有表名
        tables = self.db.get_all_tables()
        if not tables:
            logger.error("没有找到任何表")
            return []
        
        generated_files = []
        
        for table in tables:
            # 生成模型类代码
            model_code = self.generate_model_class(table)
            if not model_code:
                continue
            
            # 生成文件名（小写，下划线分隔）
            file_name = f"{table}_model.py"
            file_path = os.path.join(self.output_dir, file_name)
            
            # 写入文件
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(model_code)
                logger.info(f"已生成模型文件: {file_name}")
                generated_files.append(file_name)
            except Exception as e:
                logger.error(f"写入文件 '{file_name}' 失败: {e}")
        
        # 生成__init__.py文件
        self.generate_init_file(generated_files)
        
        return generated_files
    
    def generate_init_file(self, model_files: List[str]):
        """生成__init__.py文件，导入所有模型
        
        Args:
            model_files: 模型文件名列表
        """
        init_content = ['#!/usr/bin/env python\\n# -*- coding: utf-8 -*-\\n"""自动生成的models包初始化文件"""']
        
        # 添加模型导入语句
        for file_name in model_files:
            # 从文件名中提取模型名（去除_model.py后缀）
            model_name = file_name.replace('_model.py', '')
            # 驼峰命名的类名
            class_name = self.camel_case(model_name)
            
            # 添加导入语句
            init_content.append(f"from .{file_name[:-3]} import {class_name}, {model_name}_model")
        
        # 写入__init__.py文件
        init_path = os.path.join(self.output_dir, "__init__.py")
        try:
            with open(init_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(init_content))
            logger.info(f"已生成__init__.py文件")
        except Exception as e:
            logger.error(f"写入__init__.py文件失败: {e}")


if __name__ == "__main__":
    try:
        # 使用全局的数据库连接实例
        if db:
            generator = ModelGenerator(db)
            generated_files = generator.generate_all_models()
            
            if generated_files:
                print(f"\n成功生成 {len(generated_files)} 个模型文件:")
                for file in generated_files:
                    print(f"- {file}")
                print("\n模型生成完成！")
            else:
                print("未生成任何模型文件。")
        else:
            print("数据库连接未初始化，无法生成模型。")
    except Exception as e:
        print(f"生成模型时出错: {e}")
    finally:
        if db:
            db.close()