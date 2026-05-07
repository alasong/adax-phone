# 任务编排文件规范

## 概述

任务编排文件用于定义AI辅助开发的工作流程，支持YAML和JSON格式。系统包含：
1. **编排引擎** - 拓扑排序、并行执行、质量验证
2. **业务模板库** - 现成的软件工程方法论流程
3. **质量保证机制** - 输出验证、提示工程、反馈重试

## 📦 业务模板库（新增）

无需从零设计工作流！我们提供现成的、经过验证的业务流程模板：

| 模板名称 | 方法论支撑 | 使用场景 |
|----------|------------|----------|
| `feature_development` | 瀑布+敏捷最佳实践 | 标准功能开发 |
| `bug_fix` | RCA 根本原因分析 | Bug 修复 |
| `code_refactor` | Martin Fowler 重构方法论 | 代码重构 |
| `ci_cd` | 现代 DevOps 最佳实践 | CI/CD 流程 |
| `tdd` | Kent Beck TDD 测试驱动开发 | TDD 风格开发 |

### 使用业务模板

```bash
# 查看可用模板
python business_templates.py

# 生成并使用模板
python demo_business_orchestration.py feature_development

# 或者直接运行
python task_orchestrator.py workflows/feature_development.yaml
```

## 文件结构

### 根级字段

```yaml
id: 唯一标识符
name: 工作流名称
description: 描述
version: "1.0"
author: 作者
variables: 变量字典
max_parallel: 最大并行任务数 (默认: 4)
tasks: 任务列表
```

### 任务结构

```yaml
id: 任务ID
name: 任务名称
description: 描述
tool: 使用的工具 (aider|claude|codex|script)
instruction: 指令内容
files: 相关文件列表
inputs: 输入规范
outputs: 输出规范
depends_on: 依赖的任务ID列表
max_retries: 最大重试次数 (默认: 3)
retry_delay: 重试间隔秒数 (默认: 5)
timeout: 超时时间(秒) (默认: 300)
parallel: 是否允许并行执行 (默认: false)
quality_checks: 质量检查规则
chain_of_thought: 是否使用思维链提示 (默认: true)
few_shot_examples: few-shot示例列表
output_validation: 输出验证规范 (重要！见下方说明)
```

## 🎯 质量提升功能（新增）

### 1. 输出验证

确保AI输出完全符合预期格式和内容要求。支持多种验证方式：

#### JSON Schema 验证

```yaml
output_validation:
  json_schema:
    type: object
    properties:
      success:
        type: boolean
      message:
        type: string
    required:
      - success
      - message
```

#### 正则表达式验证

```yaml
output_validation:
  regex:
    - 'success'
    - 'completed'
```

#### 自定义断言验证

```yaml
output_validation:
  assertions:
    - value.get('success')
    - 'message' in value
    - len(value.get('message', '')) > 5
```

### 2. 提示工程增强

#### 结构化提示

使用 `PromptBuilder` 生成结构清晰的提示，包含：
- 任务描述
- 输入上下文
- 输出格式规范
- 示例
- 思维链引导

#### Few-shot 示例

```yaml
few_shot_examples:
  - input: "2 + 3"
    output: "5"
  - input: "5 * 4"
    output: "20"
```

#### 思维链（Chain-of-Thought）

```yaml
chain_of_thought: true  # 让AI先思考再输出答案
```

### 3. 验证反馈与自动重试

当验证失败时，系统会：
1. 生成详细的反馈信息
2. 告诉AI哪里出了问题
3. 提供正确格式的示例
4. 让AI重新尝试（基于 `max_retries`）

## 支持的工具

### aider

使用Aider AI编程助手进行代码修改。

### claude

使用Claude AI（待实现）。

### codex

使用OpenAI Codex（待实现）。

### script

执行Python脚本（支持超时控制）。

## 质量约束规则

| 规则 | 说明 | 值类型 |
|------|------|--------|
| required | 必填 | - |
| min_length | 最小长度 | 数字 |
| max_length | 最大长度 | 数字 |
| pattern | 正则匹配 | 字符串 |
| in_list | 在列表中 | 列表 |
| custom | 自定义 | - |

## 变量替换

工作流支持丰富的变量替换语法：

### 工作流变量

```yaml
variables:
  target_file: "app.py"

tasks:
  - id: task1
    files: ["${target_file}"]
```

### 环境变量

```yaml
tasks:
  - id: task1
    instruction: "用户: ${env.USER}"
```

### 任务间输出引用

引用前置任务的输出结果：

```yaml
tasks:
  - id: design
    instruction: "创建设计文档"
  - id: implement
    depends_on: ["design"]
    instruction: "根据设计实现: ${task.design.stdout}"
```

### 内置函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `${upper(val)}` | 转大写 | `${upper(${name})}` |
| `${lower(val)}` | 转小写 | `${lower(${name})}` |
| `${strip(val)}` | 去空白 | `${strip(${input})}` |
| `${len(val)}` | 字符串长度 | `${len(${name})}` |
| `${now}` | 当前时间戳 | `${now}` → `20260506_143000` |
| `${date}` | 当前日期 | `${date}` → `2026-05-06` |
| `${default(val, fb)}` | 默认值 | `${default(${missing}, N/A)}` |

### 运行时变量覆盖

通过命令行 `--set` 参数覆盖工作流变量：

```bash
python task_orchestrator.py workflow.yaml --set target_file=main.py feature_name=Login
```

## 执行功能

### 依赖分层

任务按依赖关系自动分层，同一层内无依赖的任务可以并行执行。

### 失败重试

任务失败后自动重试，支持指数退避策略：

```yaml
tasks:
  - id: unstable
    max_retries: 3
    retry_delay: 5  # 首次重试等5s，第二次10s，第三次15s
```

### 并行执行

标记 `parallel: true` 的任务会在线程池中并行执行：

```yaml
max_parallel: 4

tasks:
  - id: test_a
    parallel: true
  - id: test_b
    parallel: true
  - id: deploy
    depends_on: ["test_a", "test_b"]
```

### 暂停与恢复

工作流执行过程中会自动保存状态文件。支持从断点恢复：

```bash
# 恢复执行
python task_orchestrator.py workflow.yaml --resume .workflow_xxx_state.json
```

### 执行报告

工作流执行完成后自动生成详细报告，包含：
- 每个任务的状态、耗时、重试次数
- 总体摘要（完成/失败/跳过数量）
- 失败任务详情

## 完整示例

```yaml
id: example_workflow
name: 高质量开发工作流示例
description: 演示所有质量提升功能
version: 1.0
author: Super Coder
max_parallel: 3

variables:
  feature_name: PowerCalculator
  target_file: calculator.py

tasks:
  - id: design
    name: 功能设计
    tool: script
    instruction: |
      print('设计文档创建完成')
      output = {"status": "ok", "features": ["add", "subtract", "multiply", "power"]}
      print(json.dumps(output))
    parallel: true
    output_validation:
      regex: "完成"
      json_schema:
        type: object
        properties:
          status: { type: string }
          features: { type: array }
        required: ["status", "features"]
    chain_of_thought: true
    
  - id: implement
    name: 实现功能
    tool: aider
    instruction: |
      为 ${target_file} 添加幂运算功能
      请生成完整的代码和测试
    files: ["${target_file}"]
    depends_on: ["design"]
    max_retries: 2
    few_shot_examples:
      - input: "添加平方根功能"
        output: "def sqrt(x): return x ** 0.5"
```
