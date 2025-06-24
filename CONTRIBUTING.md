# 贡献指南 | Contributing Guide

欢迎为专业量化交易系统贡献代码！🎉

## 🚀 开始贡献

### 环境设置
```bash
# 1. Fork 并克隆仓库
git clone https://github.com/yourusername/quantitative-trading-system.git
cd quantitative-trading-system

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 4. 设置pre-commit hooks
pre-commit install
```

### 开发流程
```bash
# 1. 创建功能分支
git checkout -b feature/your-feature-name

# 2. 进行开发
# 编写代码、测试、文档

# 3. 提交代码
git add .
git commit -m "feat: 添加新功能描述"

# 4. 推送分支
git push origin feature/your-feature-name

# 5. 创建Pull Request
```

## 📋 贡献类型

### 🐛 Bug修复
- 修复已知问题
- 改进错误处理
- 性能优化

### ✨ 新功能
- 新的交易策略
- 技术指标扩展
- 用户界面改进

### 📖 文档
- API文档
- 使用指南
- 代码注释

### 🧪 测试
- 单元测试
- 集成测试
- 性能测试

## 🔄 提交规范

### Commit Message格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型(type)
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变动

### 示例
```bash
feat(trading): 添加新的RSI策略

- 实现RSI超买超卖策略
- 添加动态参数调整
- 增加回测功能

Closes #123
```

## 🧪 测试指南

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_trading_system.py

# 运行覆盖率测试
pytest --cov=src tests/
```

### 测试要求
- 新功能必须包含测试
- 测试覆盖率 > 80%
- 所有测试必须通过

### 测试类型
```python
# 单元测试示例
def test_calculate_rsi():
    """测试RSI计算"""
    data = pd.DataFrame({'close': [100, 102, 101, 103, 102]})
    rsi = calculate_rsi(data)
    assert 0 <= rsi <= 100

# 集成测试示例
def test_trading_system_integration():
    """测试交易系统集成"""
    system = TradingSystem(test_mode=True)
    signals = system.generate_signals()
    assert len(signals) > 0
```

## 📐 代码规范

### Python代码风格
```python
# 使用Black格式化
black .

# 使用flake8检查
flake8 .

# 使用isort排序导入
isort .
```

### 代码质量
- 遵循PEP 8规范
- 使用类型提示
- 编写清晰的注释
- 保持函数简短

### 代码示例
```python
from typing import List, Optional
import pandas as pd

class TradingStrategy:
    """交易策略基类"""
    
    def __init__(self, name: str, parameters: dict) -> None:
        """
        初始化策略
        
        Args:
            name: 策略名称
            parameters: 策略参数
        """
        self.name = name
        self.parameters = parameters
    
    def generate_signals(self, data: pd.DataFrame) -> List[dict]:
        """
        生成交易信号
        
        Args:
            data: 市场数据
            
        Returns:
            交易信号列表
        """
        raise NotImplementedError("子类必须实现此方法")
```

## 📚 文档规范

### 代码文档
```python
def calculate_indicators(data: pd.DataFrame) -> dict:
    """
    计算技术指标
    
    Args:
        data: 包含OHLCV数据的DataFrame
        
    Returns:
        包含各种技术指标的字典
        
    Raises:
        ValueError: 当数据不足时抛出
        
    Examples:
        >>> data = pd.DataFrame({'close': [100, 102, 101]})
        >>> indicators = calculate_indicators(data)
        >>> assert 'rsi' in indicators
    """
    pass
```

### Markdown文档
- 使用清晰的标题层次
- 包含代码示例
- 添加表格和图表
- 提供链接和引用

## 🔍 Pull Request指南

### PR检查清单
- [ ] 代码遵循项目规范
- [ ] 包含适当的测试
- [ ] 文档已更新
- [ ] 没有合并冲突
- [ ] CI/CD检查通过

### PR模板
```markdown
## 🔄 变更类型
- [ ] Bug修复
- [ ] 新功能
- [ ] 文档更新
- [ ] 性能优化

## 📝 变更描述
简要描述此PR的目的和内容

## 🧪 测试
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试完成

## 📋 检查清单
- [ ] 代码风格检查通过
- [ ] 文档已更新
- [ ] 变更日志已更新
```

### 代码审查
- 所有PR需要至少一次代码审查
- 审查者会检查代码质量、测试和文档
- 请耐心等待审查反馈

## 🎯 开发优先级

### 高优先级
1. **安全性**: API密钥管理、数据安全
2. **稳定性**: 错误处理、异常情况
3. **性能**: 数据处理速度、内存使用

### 中优先级
1. **功能性**: 新策略、新指标
2. **易用性**: 用户界面、文档
3. **测试**: 测试覆盖率、测试质量

### 低优先级
1. **优化**: 代码重构、性能微调
2. **美化**: 界面美化、输出格式

## 🏆 贡献者认可

### 贡献者列表
所有贡献者都会在README.md中得到认可

### 贡献统计
- GitHub Contributors页面
- 定期发布贡献者报告
- 特殊贡献者徽章

### 激励机制
- 优秀贡献者可获得Maintainer权限
- 重大贡献会在发布说明中特别提及
- 定期举办贡献者活动

## 📞 获取帮助

### 联系方式
- **GitHub Issues**: 技术问题和bug报告
- **Discussions**: 功能讨论和建议
- **Email**: contribute@trading-system.com

### 社区资源
- [开发者文档](docs/development.md)
- [API参考](docs/api-reference.md)
- [架构设计](docs/architecture.md)

## 📄 许可证

通过贡献代码，您同意您的贡献将在与项目相同的[MIT许可证](LICENSE)下授权。

---

**感谢您的贡献！让我们一起打造更好的量化交易系统！** 🚀 