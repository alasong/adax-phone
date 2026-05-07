#!/usr/bin/env python3
"""
任务编排系统 - 通过格式化文件动态定义开发工作流
增强版：包含输出验证、结构化提示、质量保证
"""

import os
import re
import time
import yaml
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


# ============================================================
# 模板引擎 - 变量替换、环境变量、内置函数
# ============================================================

class TemplateEngine:
    """
    模板引擎，支持在工作流文件中使用变量替换。

    支持的语法：
      ${variable}           - 工作流变量
      ${env.VAR_NAME}       - 环境变量
      ${task.task_id.key}   - 前置任务的输出引用
      ${now}                - 当前时间戳
      ${upper(value)}       - 内置函数
      ${lower(value)}       - 内置函数
      ${default(val, fallback)} - 默认值
    """

    # 匹配 ${...} 模式（支持嵌套大括号）
    _PATTERN = re.compile(r'\$\{([^{}]+)\}')

    # 匹配最外层 ${...}，支持内部嵌套 ${...}
    _OUTER_PATTERN = re.compile(r'\$\{((?:[^{}]|\{[^{}]*\})*)\}')

    # 内置函数
    _BUILTIN_FUNCTIONS = {
        "upper": lambda args: args[0].upper() if args else "",
        "lower": lambda args: args[0].lower() if args else "",
        "strip": lambda args: args[0].strip() if args else "",
        "len": lambda args: str(len(args[0])) if args else "0",
        "now": lambda args: datetime.now().strftime("%Y%m%d_%H%M%S"),
        "date": lambda args: datetime.now().strftime("%Y-%m-%d"),
        "default": lambda args: args[0] if args and args[0] and not args[0].startswith("${") else (args[1] if len(args) > 1 else ""),
    }

    def __init__(self, variables: Dict[str, Any] = None,
                 env_prefix: str = "env.",
                 task_prefix: str = "task."):
        self.variables = variables or {}
        self.env_prefix = env_prefix
        self.task_prefix = task_prefix
        # 任务输出缓存，由执行器在运行时填充
        self.task_outputs: Dict[str, Dict] = {}

    def render(self, text: Any) -> Any:
        """
        渲染模板文本，替换所有 ${...} 占位符。
        支持字符串、列表、字典的递归渲染。
        """
        if isinstance(text, str):
            return self._render_string(text)
        elif isinstance(text, list):
            return [self.render(item) for item in text]
        elif isinstance(text, dict):
            return {k: self.render(v) for k, v in text.items()}
        else:
            return text

    def _render_string(self, text: str) -> str:
        """替换单个字符串中的所有占位符（支持嵌套）"""
        if "${" not in text:
            return text

        # 使用外层模式匹配，支持一层嵌套
        def _replace(match):
            expr = match.group(1)
            # 先递归渲染内层 ${...}
            rendered_expr = self._render_string(expr)
            return self._evaluate(rendered_expr)

        return self._OUTER_PATTERN.sub(_replace, text)

    def _evaluate(self, expr: str) -> str:
        """
        求值一个表达式。
        优先级：内置函数 > 环境变量 > 任务输出 > 工作流变量
        """
        expr = expr.strip()

        # 1. 内置函数: func(arg1, arg2, ...)
        func_match = re.match(r'^(\w+)\((.+)\)$', expr)
        if func_match:
            func_name = func_match.group(1)
            if func_name in self._BUILTIN_FUNCTIONS:
                # 解析参数（递归渲染参数中的变量）
                raw_args = func_match.group(2)
                args = [self._render_string(a.strip()) for a in self._split_args(raw_args)]
                return self._BUILTIN_FUNCTIONS[func_name](args)

        # 2. 环境变量: env.VAR_NAME
        if expr.startswith(self.env_prefix):
            env_key = expr[len(self.env_prefix):]
            return os.environ.get(env_key, "")

        # 3. 任务输出: task.task_id.output_key
        if expr.startswith(self.task_prefix):
            parts = expr[len(self.task_prefix):].split(".", 1)
            task_id = parts[0]
            output_key = parts[1] if len(parts) > 1 else None
            return self._get_task_output(task_id, output_key)

        # 4. 工作流变量
        if expr in self.variables:
            val = self.variables[expr]
            return str(val) if not isinstance(val, str) else val

        # 未找到变量，返回原始表达式
        return f"${{{expr}}}"

    def _get_task_output(self, task_id: str, key: str = None) -> str:
        """获取前置任务的输出"""
        output = self.task_outputs.get(task_id, {})
        if not output:
            return ""
        if key:
            # 支持嵌套key，如 "stdout" 或 "outputs.changed_files"
            val = output
            for k in key.split("."):
                if isinstance(val, dict):
                    val = val.get(k, "")
                else:
                    return ""
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val) if val else ""
        return json.dumps(output, ensure_ascii=False)

    @staticmethod
    def _split_args(raw: str) -> List[str]:
        """分割函数参数，处理逗号分隔"""
        args = []
        depth = 0
        current = []
        for ch in raw:
            if ch == '(':
                depth += 1
                current.append(ch)
            elif ch == ')':
                depth -= 1
                current.append(ch)
            elif ch == ',' and depth == 0:
                args.append("".join(current).strip())
                current = []
            else:
                current.append(ch)
        if current:
            args.append("".join(current).strip())
        return args

    def register_function(self, name: str, func):
        """注册自定义函数"""
        self._BUILTIN_FUNCTIONS[name] = func

    def update_variables(self, variables: Dict[str, Any]):
        """更新工作流变量"""
        self.variables.update(variables)


# ============================================================
# 输出验证器 - 确保AI输出符合预期规范
# ============================================================

class OutputValidator:
    """
    输出验证器 - 确保AI输出符合预期规范

    支持:
      - JSON Schema 验证
      - 正则表达式验证
      - 自定义断言脚本
      - 文件内容检查
    """

    @staticmethod
    def validate(output_spec: Dict[str, Any], actual_output: Any, context: Dict = None) -> tuple[bool, List[str]]:
        """
        验证输出

        Args:
            output_spec: 输出规范定义
            actual_output: 实际输出值
            context: 上下文数据，用于自定义断言

        Returns:
            (success, errors)
        """
        errors = []
        context = context or {}

        # 1. JSON Schema 验证
        if "json_schema" in output_spec:
            success, schema_errors = OutputValidator._validate_json_schema(
                output_spec["json_schema"], actual_output
            )
            errors.extend(schema_errors)

        # 2. 正则表达式验证
        if "regex" in output_spec:
            success, regex_errors = OutputValidator._validate_regex(
                output_spec["regex"], actual_output
            )
            errors.extend(regex_errors)

        # 3. 自定义断言
        if "assertions" in output_spec:
            success, assertion_errors = OutputValidator._validate_assertions(
                output_spec["assertions"], actual_output, context
            )
            errors.extend(assertion_errors)

        # 4. 文件内容验证
        if "file_checks" in output_spec:
            success, file_errors = OutputValidator._validate_files(
                output_spec["file_checks"], actual_output
            )
            errors.extend(file_errors)

        return len(errors) == 0, errors

    @staticmethod
    def get_validation_feedback(output_spec: Dict[str, Any], errors: List[str], attempts: int = 1) -> str:
        """
        生成验证失败的反馈提示，用于让AI修正输出

        Args:
            output_spec: 输出规范
            errors: 错误列表
            attempts: 重试次数

        Returns:
            反馈提示字符串
        """
        feedback = f"\n\n⚠️  验证失败 (尝试 #{attempts})，请修正以下问题：\n"

        for i, error in enumerate(errors, 1):
            feedback += f"  {i}. {error}\n"

        feedback += "\n📋 请严格按照以下输出规范：\n"

        if "json_schema" in output_spec:
            feedback += "  - 输出格式必须符合指定的JSON Schema\n"

        if "regex" in output_spec:
            feedback += f"  - 输出必须匹配正则: {output_spec['regex']}\n"

        if "examples" in output_spec:
            feedback += "  - 参考示例输出:\n"
            for i, example in enumerate(output_spec["examples"][:3], 1):
                feedback += f"    {i}. {json.dumps(example, ensure_ascii=False)[:200]}\n"

        feedback += "\n🔧 请重新输出正确的结果。"
        return feedback

    @staticmethod
    def _validate_json_schema(schema: Dict[str, Any], value: Any) -> tuple[bool, List[str]]:
        """使用JSON Schema验证"""
        try:
            import jsonschema
        except ImportError:
            return True, []  # 如果没有安装jsonschema，跳过验证

        errors = []
        try:
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except Exception:
                    value = value  # 保持原样
            jsonschema.validate(instance=value, schema=schema)
            return True, []
        except json.JSONDecodeError as e:
            errors.append(f"不是有效的JSON: {e}")
            return False, errors
        except jsonschema.exceptions.ValidationError as e:
            path = " -> ".join(map(str, e.path)) or "(root)"
            errors.append(f"JSON Schema 验证失败 (路径: {path}): {e.message}")
            return False, errors
        except Exception as e:
            errors.append(f"Schema验证异常: {e}")
            return False, errors

    @staticmethod
    def _validate_regex(regex_spec: Union[str, List[str]], value: Any) -> tuple[bool, List[str]]:
        """使用正则表达式验证"""
        errors = []
        if not isinstance(value, str):
            value = str(value)

        patterns = [regex_spec] if isinstance(regex_spec, str) else regex_spec

        for pattern in patterns:
            try:
                if not re.search(pattern, value):
                    errors.append(f"未匹配正则: {pattern}")
            except re.error as e:
                errors.append(f"正则表达式错误: {pattern} - {e}")

        return len(errors) == 0, errors

    @staticmethod
    def _validate_assertions(assertions: List[str], value: Any, context: Dict) -> tuple[bool, List[str]]:
        """使用自定义断言脚本验证"""
        errors = []

        for i, assertion in enumerate(assertions, 1):
            try:
                # 构建执行环境
                local_vars = {
                    "value": value,
                    "ctx": context,
                    "output": value,
                    "__builtins__": {
                        "len": len, "str": str, "int": int, "float": float,
                        "bool": bool, "list": list, "dict": dict, "set": set,
                        "any": any, "all": all, "isinstance": isinstance
                    }
                }

                # 执行断言脚本
                result = eval(assertion, {}, local_vars)
                if not bool(result):
                    errors.append(f"断言失败 # {i}: {assertion}")

            except Exception as e:
                errors.append(f"断言异常 # {i}: {e}")

        return len(errors) == 0, errors

    @staticmethod
    def _validate_files(file_checks: List[Dict], _: Any) -> tuple[bool, List[str]]:
        """验证文件内容"""
        errors = []

        for check in file_checks:
            path = check.get("path")
            if not path:
                continue

            file_path = Path(path)
            if not file_path.exists():
                errors.append(f"文件不存在: {path}")
                continue

            try:
                content = file_path.read_text(encoding="utf-8")

                # 检查文件大小
                if "min_size" in check and len(content) < check["min_size"]:
                    errors.append(f"文件 {path} 太小 (需要≥{check['min_size']}字符)")

                # 检查包含内容
                if "contains" in check and check["contains"] not in content:
                    errors.append(f"文件 {path} 不包含: {check['contains']}")

                # 检查正则
                if "regex" in check and not re.search(check["regex"], content):
                    errors.append(f"文件 {path} 未匹配: {check['regex']}")

            except Exception as e:
                errors.append(f"文件检查异常 {path}: {e}")

        return len(errors) == 0, errors


# ============================================================
# 提示工程 - 结构化提示模板
# ============================================================

class PromptBuilder:
    """
    结构化提示模板构建器
    提高AI输出质量的提示工程
    """

    @staticmethod
    def build_structured_prompt(
        task_description: str,
        input_context: str = "",
        output_spec: Dict = None,
        examples: List[Dict] = None,
        chain_of_thought: bool = True
    ) -> str:
        """
        构建结构化提示

        Args:
            task_description: 任务描述
            input_context: 输入上下文
            output_spec: 输出规范
            examples: 少量示例
            chain_of_thought: 是否要求思维链

        Returns:
            结构化提示字符串
        """
        prompt = "# 任务\n" + task_description.strip() + "\n\n"

        if input_context:
            prompt += "# 输入\n" + input_context.strip() + "\n\n"

        if output_spec:
            prompt += "# 输出要求\n"
            if "json_schema" in output_spec:
                prompt += "## 格式规范\n请以JSON格式输出，必须符合以下Schema:\n```json\n"
                prompt += json.dumps(output_spec["json_schema"], indent=2, ensure_ascii=False)
                prompt += "\n```\n\n"

            if "regex" in output_spec:
                regex = output_spec["regex"]
                if isinstance(regex, list):
                    regex = "\n".join(f"  - {r}" for r in regex)
                prompt += f"## 内容格式要求\n{regex}\n\n"

            if "constraints" in output_spec:
                prompt += "## 约束条件\n"
                for i, c in enumerate(output_spec["constraints"], 1):
                    prompt += f"{i}. {c}\n"
                prompt += "\n"

        if examples:
            prompt += "# 示例\n"
            for i, example in enumerate(examples, 1):
                if isinstance(example, dict):
                    prompt += f"## 示例{i}\n输入: {example.get('input', '')}\n输出: {json.dumps(example.get('output', ''), ensure_ascii=False)}\n\n"
                else:
                    prompt += f"## 示例{i}\n{example}\n\n"

        if chain_of_thought:
            prompt += "# 思考过程\n请先思考问题的解决方案，然后再输出最终答案。\n\n"

        prompt += "# 输出\n请开始输出：\n"

        return prompt


# ============================================================
# 数据模型
# ============================================================

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ValidationRule(Enum):
    """验证规则类型"""
    REQUIRED = "required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    IN_LIST = "in_list"
    CUSTOM = "custom"


@dataclass
class QualityConstraint:
    """质量约束"""
    rule: ValidationRule
    value: Any = None
    message: str = ""


@dataclass
class TaskInput:
    """任务输入"""
    type: str  # "file", "text", "prompt"
    value: Any = None
    path: Optional[Path] = None


@dataclass
class TaskOutput:
    """任务输出规范"""
    type: str  # "file", "text", "diff", "commit"
    format: str = ""  # "json", "yaml", "text"
    constraints: List[QualityConstraint] = field(default_factory=list)
    path: Optional[Path] = None
    validation: Optional[Dict] = None  # 输出验证规范


@dataclass
class Task:
    """单个任务"""
    id: str
    name: str
    description: str = ""
    tool: str = "aider"  # 使用的工具
    instruction: str = ""
    files: List[Path] = field(default_factory=list)
    inputs: List[TaskInput] = field(default_factory=list)
    outputs: List[TaskOutput] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    max_retries: int = 3
    retry_delay: int = 5  # 重试间隔秒数
    timeout: int = 300
    quality_checks: List[QualityConstraint] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0  # 已重试次数
    parallel: bool = False  # 是否可并行执行
    # 新增字段
    output_validation: Optional[Dict] = None  # 输出验证规则
    few_shot_examples: List[Dict] = field(default_factory=list)  # 少量示例
    chain_of_thought: bool = True  # 是否使用思维链


@dataclass
class Workflow:
    """工作流"""
    id: str
    name: str
    description: str = ""
    version: str = "1.0"
    author: str = ""
    tasks: List[Task] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    project_path: Path = field(default_factory=Path.cwd)
    _engine: Optional[TemplateEngine] = field(default=None, repr=False)
    # 执行配置
    max_parallel: int = 4  # 最大并行任务数
    state_file: Optional[str] = None  # 状态文件路径（用于暂停/恢复）


@dataclass
class IterationResult:
    """迭代结果"""
    tool: str
    success: bool
    changes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    commit_hash: Optional[str] = None


# ============================================================
# 任务解析器
# ============================================================

class TaskParser:
    """任务解析器"""

    @staticmethod
    def parse_yaml(file_path: Path, extra_variables: Dict[str, Any] = None) -> Workflow:
        """从YAML文件解析工作流"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return TaskParser._parse_workflow(data, extra_variables)

    @staticmethod
    def parse_json(file_path: Path, extra_variables: Dict[str, Any] = None) -> Workflow:
        """从JSON文件解析工作流"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return TaskParser._parse_workflow(data, extra_variables)

    @staticmethod
    def _parse_workflow(data: Dict[str, Any], extra_variables: Dict[str, Any] = None) -> Workflow:
        """解析工作流数据，并应用变量替换"""
        raw_variables = data.get("variables", {})
        if extra_variables:
            raw_variables.update(extra_variables)

        # 用模板引擎渲染整个工作流数据（任务间引用在执行阶段处理）
        engine = TemplateEngine(variables=raw_variables)
        rendered = engine.render(data)

        workflow = Workflow(
            id=rendered.get("id", ""),
            name=rendered.get("name", ""),
            description=rendered.get("description", ""),
            version=rendered.get("version", "1.0"),
            author=rendered.get("author", ""),
            variables=raw_variables,  # 保留原始变量供执行阶段使用
            _engine=engine  # 传递引擎实例给执行器
        )

        if "max_parallel" in rendered:
            workflow.max_parallel = rendered["max_parallel"]

        for task_data in rendered.get("tasks", []):
            task = TaskParser._parse_task(task_data)
            workflow.tasks.append(task)

        return workflow

    @staticmethod
    def _parse_task(data: Dict[str, Any]) -> Task:
        """解析单个任务"""
        files = [Path(f) for f in data.get("files", [])]

        inputs = []
        for input_data in data.get("inputs", []):
            input_obj = TaskInput(
                type=input_data.get("type", "text"),
                value=input_data.get("value"),
                path=Path(input_data["path"]) if input_data.get("path") else None
            )
            inputs.append(input_obj)

        outputs = []
        for output_data in data.get("outputs", []):
            constraints = []
            for c in output_data.get("constraints", []):
                constraints.append(QualityConstraint(
                    rule=ValidationRule(c["rule"]),
                    value=c.get("value"),
                    message=c.get("message", "")
                ))

            output_obj = TaskOutput(
                type=output_data.get("type", "text"),
                format=output_data.get("format", "text"),
                constraints=constraints,
                path=Path(output_data["path"]) if output_data.get("path") else None,
                validation=output_data.get("validation")
            )
            outputs.append(output_obj)

        quality_checks = []
        for q in data.get("quality_checks", []):
            quality_checks.append(QualityConstraint(
                rule=ValidationRule(q["rule"]),
                value=q.get("value"),
                message=q.get("message", "")
            ))

        return Task(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tool=data.get("tool", "aider"),
            instruction=data.get("instruction", ""),
            files=files,
            inputs=inputs,
            outputs=outputs,
            depends_on=data.get("depends_on", []),
            max_retries=data.get("max_retries", 3),
            retry_delay=data.get("retry_delay", 5),
            timeout=data.get("timeout", 300),
            quality_checks=quality_checks,
            parallel=data.get("parallel", False),
            output_validation=data.get("output_validation"),
            few_shot_examples=data.get("few_shot_examples", []),
            chain_of_thought=data.get("chain_of_thought", True)
        )


# ============================================================
# 质量验证器（向后兼容）
# ============================================================

class QualityValidator:
    """质量验证器"""

    @staticmethod
    def validate(value: Any, constraints: List[QualityConstraint]) -> tuple[bool, List[str]]:
        """验证值是否满足约束"""
        errors = []

        for constraint in constraints:
            if constraint.rule == ValidationRule.REQUIRED:
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.append(constraint.message or "值不能为空")

            elif constraint.rule == ValidationRule.MIN_LENGTH:
                if isinstance(value, str) and len(value) < constraint.value:
                    errors.append(constraint.message or f"长度不能小于{constraint.value}")

            elif constraint.rule == ValidationRule.MAX_LENGTH:
                if isinstance(value, str) and len(value) > constraint.value:
                    errors.append(constraint.message or f"长度不能大于{constraint.value}")

            elif constraint.rule == ValidationRule.PATTERN:
                if isinstance(value, str) and not re.match(constraint.value, value):
                    errors.append(constraint.message or "格式不正确")

            elif constraint.rule == ValidationRule.IN_LIST:
                if value not in constraint.value:
                    errors.append(constraint.message or f"必须是以下之一: {constraint.value}")

        return len(errors) == 0, errors


# ============================================================
# 工具适配器
# ============================================================

class ToolAdapter:
    """工具适配器基类"""

    def __init__(self, config: Workflow):
        self.config = config

    def execute(self, instruction: str, files: List[Path]) -> IterationResult:
        """执行指令"""
        raise NotImplementedError

    def is_available(self) -> bool:
        """检查工具是否可用"""
        raise NotImplementedError


class AiderAdapter(ToolAdapter):
    """Aider适配器"""

    def __init__(self, config: Workflow, tool_config: Dict = None):
        super().__init__(config)
        self.tool_config = tool_config or {}

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["aider", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def execute(self, instruction: str, files: List[Path]) -> IterationResult:
        result = IterationResult(tool="aider", success=False)

        try:
            cmd = [
                "aider",
                "--message", instruction,
                "--yes-always",
                "--no-stream",
                "--no-pretty",
                "--no-check-update",
                "--no-analytics"
            ]

            if not (self.config.variables.get("auto_commit", True)):
                cmd.append("--no-auto-commits")

            for f in files:
                cmd.append(str(f))

            proc = subprocess.run(
                cmd,
                cwd=str(self.config.project_path),
                capture_output=True,
                text=True
            )

            if proc.returncode == 0:
                result.success = True

                for line in proc.stdout.splitlines():
                    if "Applied edit to" in line:
                        result.changes.append(line.split("Applied edit to ")[1].strip())
                    elif "Commit" in line and len(line.split()) > 1:
                        result.commit_hash = line.split()[1]
            else:
                result.errors = proc.stderr.splitlines()

        except Exception as e:
            result.errors.append(str(e))

        return result


# ============================================================
# 任务执行器
# ============================================================

class TaskExecutor:
    """任务执行器 - 支持重试、并行、暂停/恢复、详细报告、输出验证"""

    def __init__(self, workflow: Workflow, coder_instance=None):
        self.workflow = workflow
        self.coder = coder_instance
        self.task_results: Dict[str, Dict] = {}
        # 使用工作流携带的模板引擎，或创建新的
        self.engine: TemplateEngine = workflow._engine or TemplateEngine(
            variables=workflow.variables
        )
        self._stop_requested = False  # 用于暂停

    # ============================================================
    # 公共接口
    # ============================================================

    def execute(self) -> Dict:
        """执行整个工作流"""
        start_time = datetime.now()
        print(f"🚀 开始执行工作流: {self.workflow.name} (v{self.workflow.version})")
        print(f"📋 任务数量: {len(self.workflow.tasks)}")
        print(f"🔧 变量: {self.workflow.variables}")
        print(f"⚡ 最大并行数: {self.workflow.max_parallel}")
        print("=" * 60)

        results = {
            "workflow": self.workflow.id,
            "workflow_name": self.workflow.name,
            "started_at": start_time.isoformat(),
            "tasks": [],
            "success": True,
            "summary": {
                "total": len(self.workflow.tasks),
                "completed": 0,
                "failed": 0,
                "skipped": 0,
            }
        }

        # 按依赖层分组执行（同层内可并行）
        layers = self._get_dependency_layers()
        for layer_idx, layer in enumerate(layers):
            if self._stop_requested:
                print("\n⏸️  工作流已暂停")
                self._save_state(results)
                break

            layer_num = layer_idx + 1
            print(f"\n{'─' * 40}")
            print(f"📦 执行第 {layer_num} 层（共 {len(layer)} 个任务）")
            print(f"{'─' * 40}")

            if len(layer) == 1:
                # 单任务直接执行
                task_result = self._execute_task_with_retry(layer[0])
                results["tasks"].append(task_result)
                self._update_summary(results, task_result)
            else:
                # 多任务并行执行
                layer_results = self._execute_layer_parallel(layer)
                for task_result in layer_results:
                    results["tasks"].append(task_result)
                    self._update_summary(results, task_result)

            # 保存中间状态
            self._save_state(results)

            # 如果有任务失败且不是跳过，标记整体失败
            for r in results["tasks"]:
                if not r["success"] and r["status"] != "skipped":
                    results["success"] = False

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        results["completed_at"] = end_time.isoformat()
        results["elapsed_seconds"] = elapsed
        results["summary"]["elapsed"] = f"{elapsed:.1f}s"

        # 打印摘要报告
        self._print_summary(results)

        return results

    def stop(self):
        """请求暂停工作流（在下次任务执行前生效）"""
        self._stop_requested = True
        print("⏸️  已请求暂停，将在当前任务完成后停止...")

    # ============================================================
    # 依赖分析和任务排序
    # ============================================================

    def _get_dependency_layers(self) -> List[List[Task]]:
        """
        将任务按依赖关系分层。
        同一层的任务无相互依赖，可以并行执行。
        """
        task_map = {t.id: t for t in self.workflow.tasks}
        completed = set()
        layers = []

        while len(completed) < len(task_map):
            # 找出所有依赖已满足的任务
            ready = []
            for task in self.workflow.tasks:
                if task.id in completed:
                    continue
                if all(dep in completed for dep in task.depends_on):
                    ready.append(task)

            if not ready:
                # 存在循环依赖
                remaining = [t.id for t in self.workflow.tasks if t.id not in completed]
                raise RuntimeError(f"检测到循环依赖或无法满足的依赖: {remaining}")

            layers.append(ready)
            completed.update(t.id for t in ready)

        return layers

    def _get_task_order(self) -> List[Task]:
        """获取任务执行顺序（拓扑排序，向后兼容）"""
        layers = self._get_dependency_layers()
        return [task for layer in layers for task in layer]

    # ============================================================
    # 重试机制（含输出验证）
    # ============================================================

    def _execute_task_with_retry(self, task: Task) -> Dict:
        """执行任务，支持失败重试和输出验证"""
        last_result = None

        for attempt in range(task.max_retries + 1):
            if attempt > 0:
                task.retry_count = attempt
                delay = task.retry_delay * attempt  # 指数退避
                print(f"   🔄 第 {attempt} 次重试（等待 {delay}s）...")
                time.sleep(delay)

            result = self._execute_task(task, attempt)
            last_result = result

            if result["success"] or result["status"] == "skipped":
                return result

            # 失败但还有重试机会
            if attempt < task.max_retries:
                print(f"   ⚠️  任务失败，准备重试 ({attempt + 1}/{task.max_retries})")
                task.status = TaskStatus.PENDING  # 重置状态

        # 所有重试都失败
        return last_result

    # ============================================================
    # 并行执行
    # ============================================================

    def _execute_layer_parallel(self, tasks: List[Task]) -> List[Dict]:
        """并行执行同一层的多个任务"""
        max_workers = min(self.workflow.max_parallel, len(tasks))
        results = []

        # 检查是否有任务标记为不可并行
        serial_tasks = [t for t in tasks if not t.parallel]
        parallel_tasks = [t for t in tasks if t.parallel]

        # 串行任务先执行
        for task in serial_tasks:
            result = self._execute_task_with_retry(task)
            results.append(result)
            # 注册输出供同层后续任务引用
            if result["success"]:
                self.engine.task_outputs[task.id] = result.get("outputs", {})

        # 并行任务使用线程池
        if parallel_tasks:
            print(f"   ⚡ 并行执行 {len(parallel_tasks)} 个任务（线程数: {max_workers}）")
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                future_to_task = {
                    pool.submit(self._execute_task_with_retry, task): task
                    for task in parallel_tasks
                }

                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        results.append(result)
                        if result["success"]:
                            self.engine.task_outputs[task.id] = result.get("outputs", {})
                    except Exception as e:
                        error_result = {
                            "id": task.id,
                            "name": task.name,
                            "status": "failed",
                            "success": False,
                            "errors": [f"并行执行异常: {e}"],
                            "outputs": {},
                        }
                        results.append(error_result)

        return results

    # ============================================================
    # 暂停/恢复
    # ============================================================

    def _save_state(self, results: Dict):
        """保存当前执行状态到文件"""
        state_file = self.workflow.state_file
        if not state_file:
            state_file = str(
                self.workflow.project_path / f".workflow_{self.workflow.id}_state.json"
            )

        state = {
            "workflow_id": self.workflow.id,
            "saved_at": datetime.now().isoformat(),
            "task_statuses": {},
            "task_outputs": {},
        }

        for task in self.workflow.tasks:
            state["task_statuses"][task.id] = task.status.value
            if task.id in self.engine.task_outputs:
                state["task_outputs"][task.id] = self._summarize_output(
                    self.engine.task_outputs[task.id]
                )

        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # 状态保存失败不影响主流程

    def resume_from_state(self, state_file: str):
        """从状态文件恢复执行状态"""
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)

        for task_id, status_str in state["task_statuses"].items():
            for task in self.workflow.tasks:
                if task.id == task_id:
                    task.status = TaskStatus(status_str)
                    if task.status == TaskStatus.COMPLETED:
                        # 恢复任务输出
                        output = state["task_outputs"].get(task_id, {})
                        self.engine.task_outputs[task.id] = output

        print(f"✅ 已从状态文件恢复: {state_file}")
        completed = sum(1 for t in self.workflow.tasks if t.status == TaskStatus.COMPLETED)
        print(f"   已完成任务: {completed}/{len(self.workflow.tasks)}")

    # ============================================================
    # 报告
    # ============================================================

    @staticmethod
    def _summarize_output(output: Dict) -> Dict:
        """生成输出摘要（截断长文本）"""
        summary = {}
        for key, val in output.items():
            if isinstance(val, str) and len(val) > 500:
                summary[key] = val[:500] + f"... (截断，共{len(val)}字符)"
            elif isinstance(val, list):
                summary[key] = val
            else:
                summary[key] = val
        return summary

    @staticmethod
    def _update_summary(results: Dict, task_result: Dict):
        """更新结果摘要"""
        status = task_result["status"]
        summary = results["summary"]
        if status in summary:
            summary[status] = summary.get(status, 0) + 1
        else:
            summary[status] = 1

    @staticmethod
    def _print_summary(results: Dict):
        """打印执行摘要报告"""
        print(f"\n{'=' * 60}")
        print(f"📊 执行摘要")
        print(f"{'=' * 60}")
        s = results["summary"]
        print(f"   总任务数: {s['total']}")
        print(f"   ✅ 完成:   {s.get('completed', 0)}")
        print(f"   ❌ 失败:   {s.get('failed', 0)}")
        print(f"   ⏭️  跳过:   {s.get('skipped', 0)}")
        print(f"   ⏱️  耗时:   {s.get('elapsed', 'N/A')}")
        print(f"   🎯 结果:   {'成功' if results['success'] else '有任务失败'}")

        # 打印失败任务详情
        failed = [t for t in results["tasks"] if t["status"] == "failed"]
        if failed:
            print(f"\n❌ 失败任务详情:")
            for t in failed:
                retries = t.get("retry_count", 0)
                retry_info = f" (重试{retries}次)" if retries > 0 else ""
                print(f"   - [{t['id']}] {t['name']}{retry_info}")
                for err in t.get("errors", [])[:3]:
                    print(f"     ⚠️ {err}")

        print(f"{'=' * 60}")

    # ============================================================
    # 单任务执行（核心逻辑，含输出验证）
    # ============================================================

    def _execute_task(self, task: Task, attempt: int = 0) -> Dict:
        """执行单个任务，支持输出验证"""
        print(f"\n📍 执行任务: [{task.id}] {task.name}")
        print(f"📝 描述: {task.description}")

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        result = {
            "id": task.id,
            "name": task.name,
            "status": "failed",
            "success": False,
            "errors": [],
            "outputs": {},
            "started_at": task.started_at.isoformat(),
            "retry_count": task.retry_count,
        }

        try:
            # 检查依赖
            for dep_id in task.depends_on:
                dep_task = next(t for t in self.workflow.tasks if t.id == dep_id)
                if dep_task.status != TaskStatus.COMPLETED:
                    task.status = TaskStatus.SKIPPED
                    result["status"] = "skipped"
                    print(f"⏭️  跳过（依赖 {dep_id} 未完成）")
                    return result

            # 构建增强提示
            instruction = self._build_enhanced_instruction(task, attempt)

            # 渲染指令和文件
            rendered_instruction = self.engine.render(instruction)
            rendered_files = self.engine.render([str(f) for f in task.files])

            # 执行任务
            if task.tool == "aider":
                task_result = self._execute_with_aider(task, rendered_instruction, rendered_files)
            elif task.tool == "claude":
                task_result = self._execute_with_claude(task, rendered_instruction)
            elif task.tool == "script":
                task_result = self._execute_script(task, rendered_instruction)
            else:
                raise ValueError(f"不支持的工具: {task.tool}")

            # 将任务输出注册到模板引擎，供后续任务引用
            self.engine.task_outputs[task.id] = task_result

            # 输出验证
            if task.output_validation:
                passed, validation_errors = OutputValidator.validate(
                    task.output_validation,
                    task_result.get("stdout", "") or task_result,
                    context={"task": task.__dict__}
                )

                if not passed:
                    task.status = TaskStatus.FAILED
                    task.errors = validation_errors
                    result["errors"] = validation_errors
                    result["validation_errors"] = validation_errors
                    print(f"❌ 输出验证失败: {validation_errors}")
                    return result

            # 基本质量检查
            passed, errors = self._check_quality(task, task_result)

            if passed:
                task.status = TaskStatus.COMPLETED
                result["status"] = "completed"
                result["success"] = True
                result["outputs"] = self._summarize_output(task_result)
                changed = task_result.get("changed_files", [])
                if changed:
                    print(f"✅ 任务完成 (变更文件: {changed})")
                else:
                    print(f"✅ 任务完成")
            else:
                task.status = TaskStatus.FAILED
                task.errors = errors
                result["errors"] = errors
                print(f"❌ 质量检查失败: {errors}")

        except subprocess.TimeoutExpired:
            task.status = TaskStatus.FAILED
            msg = f"任务超时 ({task.timeout}s)"
            task.errors = [msg]
            result["errors"] = [msg]
            print(f"⏰ {msg}")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.errors = [str(e)]
            result["errors"] = [str(e)]
            print(f"❌ 执行失败: {e}")

        task.completed_at = datetime.now()
        result["completed_at"] = task.completed_at.isoformat()
        result["duration_seconds"] = (task.completed_at - task.started_at).total_seconds()
        task.result = result
        self.task_results[task.id] = result

        return result

    def _build_enhanced_instruction(self, task: Task, attempt: int) -> str:
        """构建增强提示（含验证反馈、结构化提示）"""
        base_instruction = task.instruction

        # 如果有之前的验证错误，加上反馈
        if attempt > 0 and task.errors:
            feedback = OutputValidator.get_validation_feedback(
                task.output_validation or {},
                task.errors,
                attempt
            )
            base_instruction += feedback

        # 构建结构化提示
        if task.output_validation or task.few_shot_examples:
            base_instruction = PromptBuilder.build_structured_prompt(
                task_description=base_instruction,
                output_spec=task.output_validation,
                examples=task.few_shot_examples,
                chain_of_thought=task.chain_of_thought
            )

        return base_instruction

    def _execute_with_aider(self, task: Task, instruction: str, files: List[str]) -> Dict:
        """使用Aider执行任务"""
        print(f"🔧 调用 Aider 执行任务")

        cmd = [
            "aider",
            "--message", instruction,
            "--yes-always",
            "--no-stream",
            "--no-check-update",
            "--no-analytics"
        ]

        for f in files:
            cmd.append(str(f))

        proc = subprocess.run(
            cmd,
            cwd=str(self.workflow.project_path),
            capture_output=True,
            text=True,
            timeout=task.timeout
        )

        result = {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "changed_files": []
        }

        # 解析变更文件
        for line in proc.stdout.splitlines():
            if "Applied edit to" in line:
                result["changed_files"].append(line.split("Applied edit to ")[1].strip())

        return result

    def _execute_with_claude(self, task: Task, instruction: str) -> Dict:
        """使用Claude执行任务（框架）"""
        print(f"🔧 调用 Claude 执行任务")
        # TODO: 实现Claude集成
        return {"message": "Claude集成尚未实现", "instruction": instruction}

    def _execute_script(self, task: Task, instruction: str) -> Dict:
        """执行脚本任务（支持超时）"""
        print(f"🔧 执行脚本")
        result = {"status": "executed", "returncode": 0}
        if instruction:
            import threading

            exception_holder = [None]

            def _run():
                try:
                    exec(instruction)
                except Exception as e:
                    exception_holder[0] = e

            thread = threading.Thread(target=_run)
            thread.start()
            thread.join(timeout=task.timeout)

            if thread.is_alive():
                # 超时
                raise subprocess.TimeoutExpired(
                    cmd="script", timeout=task.timeout
                )

            if exception_holder[0]:
                raise exception_holder[0]

        return result

    def _check_quality(self, task: Task, output: Dict) -> tuple[bool, List[str]]:
        """检查输出质量"""
        if not task.quality_checks:
            return True, []

        errors = []

        if output.get("returncode", 0) != 0:
            errors.append(f"命令执行失败: {output.get('stderr', '')}")

        if "changed_files" in output and not output["changed_files"]:
            errors.append("没有文件被修改")

        return len(errors) == 0, errors


# ============================================================
# 任务编排器
# ============================================================

class TaskOrchestrator:
    """任务编排器"""

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()

    def run_workflow(self, workflow_file: Path,
                     extra_variables: Dict[str, Any] = None,
                     resume: str = None,
                     max_parallel: int = 4) -> Dict:
        """运行工作流文件"""
        # 解析工作流
        if workflow_file.suffix in [".yaml", ".yml"]:
            workflow = TaskParser.parse_yaml(workflow_file, extra_variables)
        elif workflow_file.suffix == ".json":
            workflow = TaskParser.parse_json(workflow_file, extra_variables)
        else:
            raise ValueError(f"不支持的文件格式: {workflow_file.suffix}")

        workflow.project_path = self.project_path
        workflow.max_parallel = max_parallel

        # 执行工作流
        executor = TaskExecutor(workflow)

        # 从状态文件恢复
        if resume:
            executor.resume_from_state(resume)

        results = executor.execute()

        # 保存结果
        result_file = self.project_path / f"workflow_{workflow.id}_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n📊 工作流结果已保存到: {result_file}")

        return results


# ============================================================
# 主函数
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="任务编排系统 - 通过格式化文件动态定义开发工作流"
    )
    parser.add_argument(
        "workflow",
        nargs="?",
        help="工作流文件 (YAML或JSON)"
    )
    parser.add_argument(
        "--path",
        default=".",
        help="项目路径"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="仅验证工作流文件，不执行"
    )
    parser.add_argument(
        "--init-example",
        action="store_true",
        help="创建示例工作流文件"
    )
    parser.add_argument(
        "--set",
        nargs="+",
        metavar="KEY=VALUE",
        help="覆盖或添加工作流变量，如 --set target_file=main.py feature_name=Login"
    )
    parser.add_argument(
        "--resume",
        metavar="STATE_FILE",
        help="从状态文件恢复执行（断点续跑）"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=4,
        metavar="N",
        help="最大并行任务数 (默认: 4)"
    )

    args = parser.parse_args()

    if args.init_example:
        _create_example_workflow()
        return

    if not args.workflow:
        parser.print_help()
        print("\n💡 使用示例:")
        print("  # 创建示例工作流")
        print("  python task_orchestrator.py --init-example")
        print("\n  # 验证工作流")
        print("  python task_orchestrator.py example_workflow.yaml --validate")
        print("\n  # 执行工作流")
        print("  python task_orchestrator.py example_workflow.yaml")
        print("\n  # 带变量执行")
        print("  python task_orchestrator.py workflows/feature_dev.yaml --set target_file=app.py")
        return

    # 解析 --set 参数
    extra_vars = None
    if args.set:
        extra_vars = {}
        for item in args.set:
            if "=" not in item:
                print(f"⚠️  忽略无效的变量设置: {item}（格式应为 KEY=VALUE）")
                continue
            key, value = item.split("=", 1)
            extra_vars[key] = value

    orchestrator = TaskOrchestrator(args.path)

    if args.validate:
        workflow_file = Path(args.workflow)
        if workflow_file.suffix in [".yaml", ".yml"]:
            workflow = TaskParser.parse_yaml(workflow_file, extra_vars)
        else:
            workflow = TaskParser.parse_json(workflow_file, extra_vars)
        print(f"✅ 工作流验证通过: {workflow.name}")
        print(f"📋 包含 {len(workflow.tasks)} 个任务")
        print(f"🔧 变量: {workflow.variables}")
    else:
        orchestrator.run_workflow(
            Path(args.workflow),
            extra_vars,
            args.resume,
            args.parallel
        )


def _create_example_workflow():
    """创建示例工作流（展示所有功能）"""
    example_data = {
        "id": "example_workflow",
        "name": "示例开发工作流（展示所有功能）",
        "description": "演示任务编排系统的变量替换、输出验证、结构化提示等功能",
        "version": "1.0",
        "author": "Super Coder",
        "max_parallel": 3,
        "variables": {
            "feature_name": "PowerCalculator",
            "target_file": "example.py",
            "author_name": "${env.USER}",
            "created_at": "${now}"
        },
        "tasks": [
            {
                "id": "design",
                "name": "设计功能规格",
                "description": "分析需求，创建设计文档",
                "tool": "script",
                "instruction": "print('设计完成'); import json; output = {'status': 'ok'}",
                "parallel": True,
                "output_validation": {
                    "regex": "设计完成",
                    "assertions": [
                        "True"
                    ]
                }
            },
            {
                "id": "lint_check",
                "name": "代码风格检查",
                "description": "运行代码质量检查（并行任务）",
                "tool": "script",
                "instruction": "print('代码检查通过')",
                "parallel": True
            },
            {
                "id": "implement",
                "name": "实现功能",
                "description": "根据设计实现功能",
                "tool": "script",
                "instruction": "import json; print('实现完成'); result = {'success': True, 'message': 'PowerCalculator implemented'}",
                "depends_on": ["design", "lint_check"],
                "output_validation": {
                    "json_schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "message": {"type": "string"}
                        },
                        "required": ["success", "message"]
                    },
                    "assertions": [
                        "value.get('success')"
                    ]
                },
                "max_retries": 2,
                "chain_of_thought": True
            }
        ]
    }

    with open("example_workflow.yaml", "w", encoding="utf-8") as f:
        yaml.dump(example_data, f, allow_unicode=True, sort_keys=False)

    print("✅ 示例工作流已创建: example_workflow.yaml")
    print("📋 这个示例展示了以下功能：")
    print("   - 变量替换 (${env.USER}, ${now})")
    print("   - JSON Schema 验证")
    print("   - 断言验证")
    print("   - 并行任务执行")
    print("   - 任务依赖关系")
    print("   - 重试机制")
    print("   - 链式任务输出引用")


if __name__ == "__main__":
    main()
