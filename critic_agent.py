#!/usr/bin/env python3
"""
Critic Agent - AI 审查代理

用 LLM 审查 Worker 输出，发现规则验证无法捕获的语义层面问题：
- 逻辑错误
- 事实错误
- 代码 Bug
- 需求未对齐
- 安全隐患

设计原则：
1. 规则验证（快速拦截格式错误） + Critic Agent（深度审查语义问题）
2. 支持多维度审查
3. 支持多轮修正循环
"""

import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ReviewStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_IMPROVEMENT = "needs_improvement"


class ReviewDimension(Enum):
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    SAFETY = "safety"
    STYLE = "style"
    PERFORMANCE = "performance"


@dataclass
class ReviewIssue:
    """审查发现的问题"""
    dimension: ReviewDimension
    severity: str  # critical / warning / info
    description: str
    suggestion: str
    location: str = ""  # 问题位置（如行号、字段名）


@dataclass
class ReviewResult:
    """审查结果"""
    status: ReviewStatus
    score: float  # 0-100
    issues: List[ReviewIssue] = field(default_factory=list)
    summary: str = ""
    raw_review: str = ""


class CriticAgent:
    """
    Critic Agent - 用 AI 审查 Worker 输出
    
    使用方式：
        critic = CriticAgent()
        result = critic.review(
            task_description="创建一个计算器类",
            worker_output="class Calculator: ...",
            dimensions=["correctness", "completeness"]
        )
    """
    
    DEFAULT_REVIEW_PROMPT = """你是一位资深 {domain} 专家。请严格审查以下输出。

## 任务描述
{task_description}

## Worker 输出
{worker_output}

## 审查维度
{dimensions}

## 审查要求
1. 逐项检查每个维度
2. 发现具体问题，不要泛泛而谈
3. 对每个问题给出：
   - 严重程度（critical/warning/info）
   - 问题描述
   - 改进建议
   - 问题位置（如行号、函数名、字段名）

## 输出格式（严格 JSON）
```json
{{
  "status": "pass|fail|needs_improvement",
  "score": 0-100,
  "summary": "一句话总结",
  "issues": [
    {{
      "dimension": "correctness|completeness|safety|style|performance",
      "severity": "critical|warning|info",
      "description": "问题描述",
      "suggestion": "改进建议",
      "location": "问题位置"
    }}
  ]
}}
```

注意：
- 只输出 JSON，不要其他内容
- 如果没有问题，issues 为空数组
- score 要客观，不要给满分"""

    DIMENSION_DESCRIPTIONS = {
        "correctness": "正确性：代码逻辑是否正确？有无 Bug？边界情况是否处理？",
        "completeness": "完整性：是否满足所有需求？有无遗漏功能？",
        "safety": "安全性：有无安全漏洞？输入是否验证？敏感信息是否保护？",
        "style": "规范性：是否符合编码规范？命名是否清晰？注释是否充分？",
        "performance": "性能：有无性能问题？算法复杂度是否合理？",
    }

    DOMAIN_PROMPTS = {
        "code": "Python 代码审查",
        "design": "架构设计审查",
        "document": "文档质量审查",
        "test": "测试用例审查",
    }

    def __init__(
        self,
        model: str = "gpt-4",
        review_prompt: str = None,
        default_dimensions: List[str] = None,
        min_score_to_pass: float = 70.0,
    ):
        self.model = model
        self.review_prompt = review_prompt or self.DEFAULT_REVIEW_PROMPT
        self.default_dimensions = default_dimensions or ["correctness", "completeness"]
        self.min_score_to_pass = min_score_to_pass
        self._review_history: List[Dict] = []

    def review(
        self,
        task_description: str,
        worker_output: str,
        dimensions: List[str] = None,
        domain: str = "code",
        context: Dict = None,
    ) -> ReviewResult:
        """
        审查 Worker 输出
        
        Args:
            task_description: 任务描述
            worker_output: Worker 的输出内容
            dimensions: 审查维度列表
            domain: 领域类型（code/design/document/test）
            context: 额外上下文信息
            
        Returns:
            ReviewResult 审查结果
        """
        dimensions = dimensions or self.default_dimensions
        domain_prompt = self.DOMAIN_PROMPTS.get(domain, "通用审查")
        
        dimensions_text = "\n".join(
            f"- {self.DIMENSION_DESCRIPTIONS.get(d, d)}"
            for d in dimensions
        )
        
        prompt = self.review_prompt.format(
            domain=domain_prompt,
            task_description=task_description,
            worker_output=worker_output,
            dimensions=dimensions_text,
        )
        
        if context:
            prompt += f"\n\n## 额外上下文\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        
        raw_review = self._call_llm(prompt)
        result = self._parse_review(raw_review)
        
        self._review_history.append({
            "task_description": task_description,
            "worker_output_length": len(worker_output),
            "dimensions": dimensions,
            "result": {
                "status": result.status.value,
                "score": result.score,
                "issues_count": len(result.issues),
            },
        })
        
        return result

    def review_and_fix(
        self,
        task_description: str,
        worker_output: str,
        dimensions: List[str] = None,
        domain: str = "code",
        max_rounds: int = 3,
    ) -> Dict:
        """
        审查并自动修正（多轮循环）
        
        Args:
            task_description: 任务描述
            worker_output: Worker 的初始输出
            dimensions: 审查维度
            domain: 领域类型
            max_rounds: 最大修正轮数
            
        Returns:
            {
                "final_output": str,
                "review_result": ReviewResult,
                "rounds": int,
                "history": List[Dict]
            }
        """
        current_output = worker_output
        history = []
        
        for round_num in range(1, max_rounds + 1):
            review = self.review(
                task_description=task_description,
                worker_output=current_output,
                dimensions=dimensions,
                domain=domain,
            )
            
            history.append({
                "round": round_num,
                "review": {
                    "status": review.status.value,
                    "score": review.score,
                    "issues_count": len(review.issues),
                },
            })
            
            if review.status == ReviewStatus.PASS:
                return {
                    "final_output": current_output,
                    "review_result": review,
                    "rounds": round_num,
                    "history": history,
                }
            
            feedback = self._generate_fix_prompt(task_description, current_output, review)
            fixed_output = self._call_llm(feedback)
            current_output = self._extract_code_or_text(fixed_output)
        
        return {
            "final_output": current_output,
            "review_result": review,
            "rounds": max_rounds,
            "history": history,
        }

    def get_review_stats(self) -> Dict:
        """获取审查统计信息"""
        if not self._review_history:
            return {"total": 0}
        
        total = len(self._review_history)
        passed = sum(1 for r in self._review_history if r["result"]["status"] == "pass")
        avg_score = sum(r["result"]["score"] for r in self._review_history) / total
        
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
            "average_score": round(avg_score, 1),
        }

    def _call_llm(self, prompt: str) -> str:
        """
        调用 LLM（抽象方法，可替换为实际 API 调用）
        
        默认实现：使用 subprocess 调用 aider 或 openai CLI
        实际使用时应替换为具体的 API 调用
        """
        try:
            import subprocess
            
            result = subprocess.run(
                ["aider", "--message", prompt, "--yes-always", "--no-stream", "--no-pretty"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.stdout
        except Exception:
            return self._mock_review(prompt)

    def _mock_review(self, prompt: str) -> str:
        """模拟审查结果（用于测试）"""
        return """```json
{
  "status": "needs_improvement",
  "score": 65,
  "summary": "代码基本正确，但缺少错误处理和文档",
  "issues": [
    {
      "dimension": "correctness",
      "severity": "warning",
      "description": "缺少除零异常处理",
      "suggestion": "在 divide 方法中添加 ZeroDivisionError 处理",
      "location": "divide 方法"
    },
    {
      "dimension": "style",
      "severity": "info",
      "description": "缺少类型注解和文档字符串",
      "suggestion": "添加类型注解和 docstring",
      "location": "整个类"
    }
  ]
}
```"""

    def _parse_review(self, raw_text: str) -> ReviewResult:
        """解析 LLM 输出的审查结果"""
        json_text = self._extract_json(raw_text)
        
        if not json_text:
            return ReviewResult(
                status=ReviewStatus.NEEDS_IMPROVEMENT,
                score=50.0,
                summary="无法解析审查结果",
                raw_review=raw_text,
            )
        
        try:
            data = json.loads(json_text)
            
            status = ReviewStatus(data.get("status", "needs_improvement"))
            score = float(data.get("score", 50))
            summary = data.get("summary", "")
            
            issues = []
            for issue_data in data.get("issues", []):
                try:
                    dimension = ReviewDimension(issue_data.get("dimension", "correctness"))
                except ValueError:
                    dimension = ReviewDimension.CORRECTNESS
                
                issues.append(ReviewIssue(
                    dimension=dimension,
                    severity=issue_data.get("severity", "warning"),
                    description=issue_data.get("description", ""),
                    suggestion=issue_data.get("suggestion", ""),
                    location=issue_data.get("location", ""),
                ))
            
            if score >= self.min_score_to_pass and not any(
                i.severity == "critical" for i in issues
            ):
                status = ReviewStatus.PASS
            elif any(i.severity == "critical" for i in issues):
                status = ReviewStatus.FAIL
            
            return ReviewResult(
                status=status,
                score=score,
                issues=issues,
                summary=summary,
                raw_review=raw_text,
            )
            
        except json.JSONDecodeError:
            return ReviewResult(
                status=ReviewStatus.NEEDS_IMPROVEMENT,
                score=50.0,
                summary="审查结果 JSON 解析失败",
                raw_review=raw_text,
            )

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON（支持 markdown 代码块和混杂文本）"""
        # 1. 尝试 markdown 代码块
        pattern = r"```(?:json)?\s*\n(.*?)\n```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        
        # 2. 尝试提取最外层完整 JSON 对象（支持嵌套）
        start = text.find("{")
        if start == -1:
            return ""
        
        depth = 0
        end = -1
        in_string = False
        escape_next = False
        
        for i in range(start, len(text)):
            ch = text[i]
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        
        if end > start:
            return text[start:end]
        
        return ""

    def _extract_code_or_text(self, text: str) -> str:
        """提取代码块或文本内容"""
        pattern = r"```(?:\w+)?\s*\n(.*?)\n```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        return text.strip()

    def _generate_fix_prompt(
        self,
        task_description: str,
        current_output: str,
        review: ReviewResult,
    ) -> str:
        """生成修正提示"""
        issues_text = "\n".join(
            f"{i+1}. [{issue.severity}] {issue.description}\n"
            f"   位置：{issue.location}\n"
            f"   建议：{issue.suggestion}"
            for i, issue in enumerate(review.issues)
        )
        
        return f"""请根据以下审查意见修正你的输出：

## 原始任务
{task_description}

## 你的输出
{current_output}

## 审查意见（score: {review.score}/100）
{review.summary}

{issues_text}

请修正以上问题，输出完整的结果。"""


class RulePlusCriticValidator:
    """
    规则验证 + Critic Agent 混合验证器
    
    第一层：快速规则验证（JSON Schema / 正则 / 断言）
    第二层：Critic Agent 深度审查
    """
    
    def __init__(self, critic_agent: CriticAgent = None):
        self.critic = critic_agent or CriticAgent()
    
    def validate(
        self,
        task_description: str,
        worker_output: str,
        output_spec: Dict = None,
        critic_enabled: bool = True,
        critic_dimensions: List[str] = None,
    ) -> Dict:
        """
        混合验证
        
        Args:
            task_description: 任务描述
            worker_output: Worker 输出
            output_spec: 规则验证规范
            critic_enabled: 是否启用 Critic
            critic_dimensions: Critic 审查维度
            
        Returns:
            {
                "rule_validation": {"passed": bool, "errors": []},
                "critic_review": ReviewResult or None,
                "overall_passed": bool
            }
        """
        result = {
            "rule_validation": {"passed": True, "errors": []},
            "critic_review": None,
            "overall_passed": True,
        }
        
        if output_spec:
            from task_orchestrator import OutputValidator
            rule_passed, rule_errors = OutputValidator.validate(
                output_spec, worker_output
            )
            result["rule_validation"] = {
                "passed": rule_passed,
                "errors": rule_errors,
            }
            if not rule_passed:
                result["overall_passed"] = False
                return result
        
        if critic_enabled:
            review = self.critic.review(
                task_description=task_description,
                worker_output=worker_output,
                dimensions=critic_dimensions,
            )
            result["critic_review"] = review
            if review.status != ReviewStatus.PASS:
                result["overall_passed"] = False
        
        return result


def demo():
    """演示 Critic Agent"""
    print("=" * 70)
    print("🔍 Critic Agent 演示")
    print("=" * 70)
    
    critic = CriticAgent()
    
    task = "创建一个 Python 计算器类，支持加减乘除，除零时抛出 ValueError"
    output = """
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
    
    def multiply(self, a, b):
        return a * b
    
    def divide(self, a, b):
        return a / b
"""
    
    print(f"\n📋 任务：{task}")
    print(f"\n📝 Worker 输出：\n{output}")
    
    print("\n" + "-" * 70)
    print("🔍 开始审查...")
    print("-" * 70)
    
    review = critic.review(
        task_description=task,
        worker_output=output,
        dimensions=["correctness", "completeness", "safety", "style"],
    )
    
    print(f"\n📊 审查结果：")
    print(f"   状态：{review.status.value}")
    print(f"   得分：{review.score}/100")
    print(f"   总结：{review.summary}")
    print(f"\n📋 发现问题 ({len(review.issues)} 个)：")
    for i, issue in enumerate(review.issues, 1):
        print(f"   {i}. [{issue.severity}] {issue.description}")
        print(f"      位置：{issue.location}")
        print(f"      建议：{issue.suggestion}")
    
    print("\n" + "-" * 70)
    print("🔧 自动修正演示...")
    print("-" * 70)
    
    fix_result = critic.review_and_fix(
        task_description=task,
        worker_output=output,
        dimensions=["correctness", "style"],
        max_rounds=2,
    )
    
    print(f"\n📊 修正轮数：{fix_result['rounds']}")
    for h in fix_result["history"]:
        print(f"   第 {h['round']} 轮：score={h['review']['score']}, "
              f"issues={h['review']['issues_count']}")
    
    print(f"\n📈 审查统计：{critic.get_review_stats()}")
    
    print("\n" + "=" * 70)
    print("✅ Critic Agent 演示完成！")
    print("=" * 70)


if __name__ == "__main__":
    demo()
