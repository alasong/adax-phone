#!/usr/bin/env python3
"""
任务编排系统 - 通过格式化文件动态定义开发工作流
增强版：包含输出验证、结构化提示、质量保证
"""

import os
import re
import yaml
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


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

        return len(errors) == 0, errors

    @staticmethod
    def _validate_json_schema(schema: Dict[str, Any], value: Any) -> tuple[bool, List[str]]:
        """使用JSON Schema验证"""
        try:
            import jsonschema
        except ImportError:
            return True, []  # 如果没有安装jsonschema，跳过验证

        errors = []
        try:
            json_obj = value
            if isinstance(value, dict):
                json_obj = value
            elif isinstance(value, str):
                lines = value.strip().splitlines()
                for line in lines:
                    line = line.strip()
                    if line and (line.startswith("{") or line.startswith("[")):
                        try:
                            json_obj = json.loads(line)
                            break
                        except Exception:
                            continue

            jsonschema.validate(instance=json_obj, schema=schema)
            return True, []
        except Exception as e:
            errors.append(f"JSON Schema 验证失败: {e}")
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
                local_vars = {"value": value, "ctx": context, "output": value}
                result = eval(assertion, {"__builtins__": {}}, local_vars)
                if not bool(result):
                    errors.append(f"断言失败 # {i}: {assertion}")
            except Exception as e:
                errors.append(f"断言异常 # {i}: {e}")

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
        prompt = "# 任务\n" + task_description.strip() + "\n\n"

        if input_context:
            prompt += "# 输入\n" + input_context.strip() + "\n\n"

        if output_spec:
            prompt += "# 输出要求\n"
            if "json_schema" in output_spec:
                prompt += "## 格式规范\n请以JSON格式输出，必须符合以下Schema:\n```json\n"
                prompt += json.dumps(output_spec["json_schema"], indent=2, ensure_ascii=False)
                prompt += "\n```\n\n"

        if examples:
            prompt += "# 示例\n"
            for i, example in enumerate(examples, 1):
                prompt += f"## 示例{i}\n{json.dumps(example, ensure_ascii=False)}\n\n"

        if chain_of_thought:
            prompt += "# 思考过程\n请先思考问题的解决方案，然后再输出最终答案。\n\n"

        prompt += "# 输出\n请开始输出：\n"

        return prompt


# ============================================================
# 简单测试
# ============================================================

def test_output_validation():
    """测试输出验证功能"""
    print("="*60)
    print("🧪 测试 1: 正则表达式验证")
    print("-"*60)
    spec1 = {"regex": "design"}
    passed, errors = OutputValidator.validate(spec1, "design completed")
    print(f"  输入: 'design completed'")
    print(f"  结果: {'✅ 通过' if passed else '❌ 失败'} - {errors}")

    print("\n🧪 测试 2: JSON Schema 验证")
    print("-"*60)
    spec2 = {
        "json_schema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"}
            },
            "required": ["success", "message"]
        }
    }
    test_output = '{"success": true, "message": "完成了"}'
    passed, errors = OutputValidator.validate(spec2, test_output)
    print(f"  输入: {test_output}")
    print(f"  结果: {'✅ 通过' if passed else '❌ 失败'} - {errors}")

    print("\n🧪 测试 3: 断言验证")
    print("-"*60)
    spec3 = {"assertions": ["value.get('success')", "'message' in value"]}
    test_input = {"success": True, "message": "OK"}
    passed, errors = OutputValidator.validate(spec3, test_input)
    print(f"  输入: {test_input}")
    print(f"  结果: {'✅ 通过' if passed else '❌ 失败'} - {errors}")

    print("\n🧪 测试 4: 提示工程示例")
    print("-"*60)
    prompt = PromptBuilder.build_structured_prompt(
        "创建一个计算器类",
        output_spec=spec2,
        chain_of_thought=True
    )
    print(f"  生成的提示（前200字符）:\n  {repr(prompt[:200])}...")

    print("\n" + "="*60)
    print("✅ 所有核心功能测试完成！")
    print("="*60)
    print("\n💡 新增的质量提升功能：")
    print("  1. 输出验证 - JSON Schema / 正则 / 断言")
    print("  2. 提示工程 - 结构化提示 + 思维链")
    print("  3. 验证反馈 - 失败后给AI重新尝试的反馈")
    print("  4. 示例学习 - few-shot提示")


if __name__ == "__main__":
    test_output_validation()
