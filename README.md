# 超级Coding工具

基于aider，支持多种AI工具的迭代开发和任务编排平台。

## 功能特点

- 🚀 **迭代设计/开发工作流** - 支持多轮迭代完善代码
- 📋 **任务编排系统** - 通过YAML/JSON文件定义和执行工作流
- 🔧 **可插拔工具适配器** - 支持集成aider、claude、codex等工具
- 📝 **Git集成** - 自动提交和记录变更
- 🎮 **交互式模式** - 方便的命令行交互
- 🔄 **多工具协作** - 支持多种AI工具协同工作
- ⚙️ **配置文件支持** - 灵活的JSON配置
- ✅ **质量约束检查** - 可配置的质量验证规则

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化配置和示例

```bash
# 初始化配置文件
python super_coder.py --init-config

# 创建示例工作流
python super_coder.py --init-example
```

### 3. 使用工具

```bash
# 交互式模式
python super_coder.py

# 直接执行指令
python super_coder.py --instruction "为计算器添加幂运算功能" --files example.py

# 运行工作流
python super_coder.py --workflow example_workflow.yaml
```

## 使用方法

### 交互式模式

```bash
python super_coder.py
```

在交互式模式下，你可以：
- 输入开发指令，指定文件进行迭代开发
- 输入 `workflows` 查看可用工作流
- 输入 `run <workflow>` 运行工作流
- 输入 `quit` 或 `exit` 退出

### 直接执行指令

```bash
python super_coder.py --instruction "重构登录功能" --files app.py auth.py
```

### 任务编排（工作流）

```bash
# 列出可用工作流
python super_coder.py --list-workflows

# 运行工作流
python super_coder.py --workflow workflows/feature_development.yaml

# 验证工作流（不执行）
python task_orchestrator.py workflows/feature_development.yaml --validate
```

### 配置选项

```bash
# 指定迭代次数
python super_coder.py --iterations 5 --instruction "优化性能" --files main.py

# 禁用自动提交
python super_coder.py --no-auto-commit --instruction "添加测试" --files test.py

# 详细输出
python super_coder.py -v --instruction "重构代码" --files utils.py

# 使用配置文件
python super_coder.py --config my-config.json --instruction "开发新功能" --files main.py

# 指定使用的工具
python super_coder.py --tools aider claude --instruction "协作开发" --files app.py
```

## 项目结构

```
super-coding-tool/
├── super_coder.py       # 主程序 - 超级Coding工具
├── task_orchestrator.py # 任务编排系统
├── requirements.txt     # 依赖
├── config.example.json  # 配置文件示例
├── WORKFLOW_SPEC.md     # 工作流格式规范
├── example.py           # 示例代码
├── workflows/           # 工作流示例目录
│   ├── feature_development.yaml
│   ├── bug_fix.yaml
│   └── refactor.yaml
└── README.md           # 说明文档
```

## 配置文件说明

### 超级Coding配置 (config.json)

复制 `config.example.json` 为 `config.json` 并按需修改：

```json
{
  "project": {
    "path": ".",
    "auto_commit": true,
    "iterations": 3,
    "verbose": false
  },
  "tools": {
    "aider": {
      "enabled": true,
      "model": "gpt-4",
      "edit_format": "diff"
    },
    "claude": {
      "enabled": false,
      "model": "claude-3-sonnet-20240229"
    }
  },
  "git": {
    "auto_push": false,
    "commit_prefix": "super-coder:"
  }
}
```

### 任务编排工作流文件

工作流文件支持YAML和JSON格式，用于定义完整的开发流程：

```yaml
id: feature_dev
name: 完整功能开发工作流
description: 从需求分析到测试部署的完整开发流程
version: "1.0"
author: Super Coder

variables:
  feature_name: "NewFeature"
  target_file: "app.py"

tasks:
  - id: requirements
    name: 需求分析
    tool: aider
    instruction: |
      分析功能需求，创建需求文档
    files: []
    quality_checks:
      - rule: required
        message: 需求文档必须创建
  
  - id: design
    name: 架构设计
    tool: aider
    depends_on: ["requirements"]
    # ...
```

详细规范请参考 `WORKFLOW_SPEC.md`。

## 扩展新工具

在 `super_coder.py` 中添加新的适配器：

1. 继承 `ToolAdapter` 基类
2. 实现 `is_available()` 和 `execute()` 方法
3. 在 `SuperCoder._init_adapters()` 中注册

示例：
```python
class YourToolAdapter(ToolAdapter):
    def is_available(self) -> bool:
        # 检查工具是否可用
        return True
    
    def execute(self, instruction: str, files: List[Path]) -> IterationResult:
        # 执行指令并返回结果
        pass
```

## 迭代工作流

### 简单迭代模式

1. 指定初始指令
2. 第一轮迭代 - 实现基础功能
3. 第二轮迭代 - 完善和优化
4. 第三轮迭代 - 测试和修复
5. ...继续迭代直到满意

### 工作流编排模式

通过工作流文件定义更复杂的流程，如：
- 功能开发：需求 → 设计 → 实现 → 测试
- Bug修复：复现 → 诊断 → 修复 → 验证
- 代码重构：分析 → 备份 → 分步重构 → 验证

## 架构概述

### 超级Coding工具

- **ToolType**: 枚举，定义支持的工具类型
- **ProjectConfig**: 数据类，项目配置
- **ConfigManager**: 配置文件管理
- **ToolAdapter**: 工具适配器基类
- **SuperCoder**: 主控制器，协调迭代流程

### 任务编排系统

- **Workflow**: 工作流数据类
- **Task**: 单个任务定义
- **TaskParser**: 解析工作流文件
- **TaskExecutor**: 执行工作流
- **QualityValidator**: 质量验证
- **TaskOrchestrator**: 编排器入口

## 开发计划

- [ ] 实现Claude完整适配器
- [ ] 实现Codex完整适配器
- [ ] 添加更多工具支持
- [ ] 工作流变量替换和模板
- [ ] 并行任务执行
- [ ] Web界面
- [ ] 插件系统
