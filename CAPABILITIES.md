# 项目能力点清单

> 最后更新：2026-05-07

---

## 1. 工作流编排

### 当前能力

- [x] 拓扑排序与依赖管理
- [x] 分层执行（按依赖关系自动分层）
- [x] YAML/JSON 格式支持
- [x] 变量替换（工作流变量、环境变量、任务输出引用）
- [x] 内置函数（upper/lower/len/now/date/default）
- [x] 执行报告生成（状态、耗时、重试次数）
- [x] 失败重试机制（可配置重试次数和间隔）
- [x] 循环依赖检测

### 不足

- [ ] 并行执行是串行模拟（层内任务串行遍历）
- [ ] 无真正的线程池并行执行
- [ ] 核心引擎无任务超时控制
- [ ] 核心引擎无断点续跑功能
- [ ] 无任务优先级支持
- [ ] 无条件分支（if/else 根据前置结果决定执行路径）

### 提升方案

- 使用 `concurrent.futures.ThreadPoolExecutor` 实现真正的并行执行
- 添加任务超时配置与超时中断
- 实现状态序列化与恢复执行（断点续跑）
- 添加任务优先级字段，高优先级任务优先调度
- 支持条件分支语法，如 `condition: "${task.previous.success}"`

---

## 2. AI 工具适配

### 当前能力

- [x] Aider 适配器完整实现（支持模型、编辑格式配置）
- [x] 工具可用性检测
- [x] 迭代开发模式（多轮迭代优化）
- [x] 变更文件追踪
- [x] Commit hash 记录

### 不足

- [ ] Claude 适配器为空壳（返回"尚未实现"）
- [ ] Codex 适配器为空壳（返回"尚未实现"）
- [ ] 无 API 密钥管理
- [ ] 无 token 用量统计与成本追踪
- [ ] 无流式输出支持
- [ ] 无模型切换热更新
- [ ] 无工具健康检查与自动降级

### 提升方案

- 实现 Claude Code CLI 适配器（调用 `claude` 命令）
- 实现 OpenAI API 适配器（直接调用 API）
- 添加 `.env` 文件管理 API 密钥
- 添加 token 计数器与成本计算
- 实现工具不可用时的自动降级策略

---

## 3. 质量验证

### 当前能力

- [x] JSON Schema 验证
- [x] 正则表达式验证
- [x] 自定义断言验证
- [x] 文件内容验证（大小、包含内容、正则匹配）
- [x] 验证失败反馈生成（用于 AI 重试）
- [x] 质量约束规则（required/min_length/max_length/pattern/in_list）

### 不足

- [ ] 无预定义验证规则库
- [ ] 断言使用 `eval` 有安全风险
- [ ] 无验证结果缓存
- [ ] 无验证覆盖率统计
- [ ] 无自定义验证插件注册

### 提升方案

- 创建预定义验证规则库（代码规范、文档完整性、测试覆盖率等）
- 用 AST 解析或安全沙箱替代 `eval`
- 添加验证插件注册接口，支持自定义验证逻辑
- 生成验证覆盖率报告

---

## 4. 提示工程

### 当前能力

- [x] 结构化提示构建（任务/输入/输出/示例/思考过程）
- [x] 思维链（Chain-of-Thought）支持
- [x] Few-shot 示例支持

### 不足

- [ ] 提示模板过于简单，缺少角色设定
- [ ] 无 system prompt 配置
- [ ] 无上下文窗口管理（超长指令截断）
- [ ] 无提示优化建议
- [ ] 无提示版本管理
- [ ] 无项目上下文自动注入

### 提升方案

- 添加 system prompt 配置（角色、风格、约束）
- 实现上下文窗口自动管理（超出时摘要压缩）
- 添加提示模板版本管理
- 自动注入项目结构、相关文件内容作为上下文
- 提供提示质量评分与优化建议

---

## 5. 可观测性

### 当前能力

- [x] 结构化日志（按模块、级别记录）
- [x] 审计日志（JSONL 格式，记录关键事件）
- [x] 指标追踪（workflows_total、tasks_success 等）
- [x] 工作流历史记录（JSON 文件保存）
- [x] 日志文件输出（`logs/orchestration.log`）

### 不足

- [ ] 无日志轮转（日志会无限增长）
- [ ] 无日志级别配置（固定 DEBUG）
- [ ] 无指标可视化
- [ ] 无告警机制
- [ ] 无分布式追踪 ID
- [ ] 无日志聚合与检索

### 提升方案

- 使用 `logging.handlers.RotatingFileHandler` 实现日志轮转
- 支持通过配置设置日志级别
- 集成 Prometheus 指标导出
- 添加关键事件告警（连续失败、超时等）
- 添加 trace_id 实现全链路追踪

---

## 6. 业务模板

### 当前能力

- [x] 5 个模板（功能开发、Bug 修复、重构、CI/CD、TDD）
- [x] 模板依赖关系定义
- [x] 模板列表与加载
- [x] 模板生成可执行工作流文件

### 不足

- [ ] 所有模板 instruction 都是 print 占位符
- [ ] 无真实 AI 指令
- [ ] 无模板参数化（无法传入具体需求）
- [ ] 无模板组合能力（多个模板串联）
- [ ] 无模板市场/共享机制
- [ ] 无模板版本管理

### 提升方案

- 填充真实的 AI 指令（如需求分析、代码生成、测试编写等）
- 支持模板参数化，如 `${feature_description}`、`${target_file}`
- 支持模板组合，如 `bug_fix + code_refactor`
- 添加模板版本管理
- 提供模板导入/导出功能

---

## 7. 测试框架

### 当前能力

- [x] 断言引擎（状态、成功、输出、耗时、错误）
- [x] 测试用例定义
- [x] 测试套件管理
- [x] 测试报告生成
- [x] pytest 配置（`pyproject.toml`）
- [x] 核心引擎单元测试（`tests/test_core_engine.py`）

### 不足

- [ ] 无 mock 支持
- [ ] 无测试数据工厂
- [ ] 无性能基准测试
- [ ] 测试覆盖率低（仅核心引擎）
- [ ] 无 CI 集成

### 提升方案

- 添加 mock 工具支持（模拟 AI 工具响应）
- 添加测试数据工厂（快速生成测试工作流）
- 添加性能基准测试（并行执行、大规模工作流）
- 补充各模块单元测试
- 集成 GitHub Actions CI

---

## 8. 模板引擎

### 当前能力

- [x] 变量替换（`${variable}`）
- [x] 环境变量（`${env.VAR}`）
- [x] 任务输出引用（`${task.id.output}`）
- [x] 内置函数（upper/lower/len/now/date/default/strip）
- [x] 嵌套变量解析
- [x] 自定义函数注册

### 不足

- [ ] 无条件判断（if/else）
- [ ] 无循环（for/while）
- [ ] 无模板继承
- [ ] 无错误处理（变量不存在时返回原始字符串）
- [ ] 无模板语法检查

### 提升方案

- 添加条件语法：`${if condition}...${else}...${end}`
- 添加循环语法：`${for item in list}...${end}`
- 添加模板继承（基础模板 + 子模板覆盖）
- 添加严格模式（变量不存在时报错）
- 添加模板语法检查与预览

---

## 9. Git 集成

### 当前能力

- [x] Aider 自动 commit
- [x] Commit hash 记录
- [x] 变更文件追踪
- [x] 可配置自动提交开关

### 不足

- [ ] 无分支管理
- [ ] 无 tag 创建
- [ ] 无 PR/MR 创建
- [ ] 无变更 diff 预览
- [ ] 无回滚功能
- [ ] 无 Git 钩子集成

### 提升方案

- 添加 GitPython 依赖
- 实现分支创建/切换/合并
- 实现自动 tag（版本发布时）
- 实现工作流失败自动回滚（git revert）
- 添加变更 diff 预览（执行前确认）

---

## 10. 配置管理

### 当前能力

- [x] JSON 配置文件（`config.json`）
- [x] 命令行参数覆盖
- [x] 配置示例（`config.example.json`）
- [x] 配置加载与保存
- [x] pyproject.toml 项目配置

### 不足

- [ ] 无配置 schema 验证
- [ ] 无配置加密（API 密钥明文）
- [ ] 无多环境配置（dev/staging/prod）
- [ ] 无配置热更新
- [ ] 无配置继承（基础配置 + 环境覆盖）

### 提升方案

- 添加 JSON Schema 验证配置文件
- 支持从 `.env` 或密钥管理服务读取敏感配置
- 支持多环境配置文件（`config.dev.json`、`config.prod.json`）
- 支持配置继承（`base.json` + `env.json` 覆盖）

---

## 11. 项目工程化

### 当前能力

- [x] 虚拟环境支持（`.venv`）
- [x] 依赖管理（`requirements.txt`）
- [x] Makefile 常用命令
- [x] .gitignore 配置
- [x] .editorconfig 代码风格
- [x] LICENSE（MIT）
- [x] README.md 使用说明
- [x] ARCHITECTURE.md 架构文档
- [x] WORKFLOW_SPEC.md 工作流规范

### 不足

- [ ] 无 CI/CD 配置
- [ ] 无代码格式化自动检查
- [ ] 无类型注解（mypy）
- [ ] 无文档站点
- [ ] 无 Docker 支持

### 提升方案

- 添加 GitHub Actions CI 配置
- 集成 black/ruff 自动格式化
- 添加类型注解，通过 mypy 检查
- 添加 Dockerfile 与 docker-compose
- 使用 MkDocs 生成文档站点

---

## 能力成熟度总览

| 能力点 | 成熟度 | 优先级 |
|--------|--------|--------|
| 工作流编排 | ⭐⭐⭐ | P0 |
| AI 工具适配 | ⭐⭐ | P0 |
| 质量验证 | ⭐⭐⭐ | P1 |
| 提示工程 | ⭐⭐ | P1 |
| Critic Agent | ⭐⭐⭐ | P0 |
| 可观测性 | ⭐⭐⭐ | P2 |
| 业务模板 | ⭐⭐ | P0 |
| 测试框架 | ⭐⭐⭐ | P1 |
| 模板引擎 | ⭐⭐⭐ | P2 |
| Git 集成 | ⭐⭐ | P2 |
| 配置管理 | ⭐⭐⭐ | P2 |
| 项目工程化 | ⭐⭐⭐ | P1 |

---

## 12. Critic Agent（AI 审查代理）

### 当前能力

- [x] CriticAgent 类（[critic_agent.py](file:///Users/song/1github/adax-phone/critic_agent.py)）
- [x] 多维度审查（correctness/completeness/safety/style/performance）
- [x] 审查结果结构化输出（ReviewResult/ReviewIssue）
- [x] 自动修正循环（review_and_fix，支持多轮修正）
- [x] 规则验证 + Critic Agent 混合验证器（RulePlusCriticValidator）
- [x] 集成到任务编排系统（工作流配置 `critic` 字段）
- [x] 审查统计与历史记录
- [x] 单元测试（19 个用例通过）

### 不足

- [ ] 默认使用 subprocess 调用 aider，未直接调用 LLM API
- [ ] 无审查结果缓存（相同输出重复审查浪费 token）
- [ ] 无审查置信度评估
- [ ] 无领域专用审查器（如安全审查器、性能审查器）

### 提升方案

- 添加直接 LLM API 调用（OpenAI/Anthropic）
- 实现审查结果缓存（基于输出 hash）
- 添加领域专用审查器子类
- 支持审查规则自定义（用户可定义审查 prompt）

### 工作流配置示例

```yaml
tasks:
  - id: implement
    name: 代码实现
    tool: aider
    instruction: "为计算器添加幂运算功能"
    files: ["calculator.py"]
    critic:
      enabled: true
      dimensions: ["correctness", "completeness", "safety"]
      domain: "code"
      max_rounds: 2
      min_score: 70
```
