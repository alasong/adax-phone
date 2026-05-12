#!/usr/bin/env python3
"""Critic Agent 单元测试"""

import pytest
from critic_agent import (
    CriticAgent,
    ReviewResult,
    ReviewIssue,
    ReviewStatus,
    ReviewDimension,
    RulePlusCriticValidator,
)


class TestReviewResult:
    """测试审查结果数据模型"""

    def test_create_review_result(self):
        result = ReviewResult(
            status=ReviewStatus.PASS,
            score=85,
            summary="代码质量良好",
        )
        assert result.status == ReviewStatus.PASS
        assert result.score == 85
        assert result.issues == []

    def test_create_review_with_issues(self):
        issue = ReviewIssue(
            dimension=ReviewDimension.CORRECTNESS,
            severity="critical",
            description="缺少除零处理",
            suggestion="添加 ZeroDivisionError 处理",
            location="divide 方法",
        )
        result = ReviewResult(
            status=ReviewStatus.FAIL,
            score=40,
            issues=[issue],
            summary="存在严重问题",
        )
        assert len(result.issues) == 1
        assert result.issues[0].severity == "critical"


class TestCriticAgent:
    """测试 Critic Agent"""

    def test_default_init(self):
        critic = CriticAgent()
        assert critic.model == "gpt-4"
        assert critic.default_dimensions == ["correctness", "completeness"]
        assert critic.min_score_to_pass == 70.0

    def test_custom_init(self):
        critic = CriticAgent(
            model="gpt-3.5-turbo",
            default_dimensions=["safety"],
            min_score_to_pass=80,
        )
        assert critic.model == "gpt-3.5-turbo"
        assert critic.default_dimensions == ["safety"]
        assert critic.min_score_to_pass == 80

    def test_review_returns_result(self):
        critic = CriticAgent()
        result = critic.review(
            task_description="创建一个计算器类",
            worker_output="class Calculator: pass",
            dimensions=["correctness"],
        )
        assert isinstance(result, ReviewResult)
        assert isinstance(result.status, ReviewStatus)
        assert isinstance(result.score, float)

    def test_review_and_fix_returns_dict(self):
        critic = CriticAgent()
        result = critic.review_and_fix(
            task_description="创建一个计算器类",
            worker_output="class Calculator: pass",
            max_rounds=2,
        )
        assert "final_output" in result
        assert "review_result" in result
        assert "rounds" in result
        assert "history" in result
        assert isinstance(result["history"], list)

    def test_review_stats(self):
        critic = CriticAgent()
        critic.review(
            task_description="test",
            worker_output="output",
        )
        critic.review(
            task_description="test2",
            worker_output="output2",
        )
        stats = critic.get_review_stats()
        assert stats["total"] == 2
        assert "average_score" in stats

    def test_extract_json_from_markdown(self):
        critic = CriticAgent()
        text = """```json
{"status": "pass", "score": 90}
```"""
        json_text = critic._extract_json(text)
        assert '"status"' in json_text
        assert '"score"' in json_text

    def test_extract_json_raw(self):
        critic = CriticAgent()
        text = 'Some text {"status": "pass"} more text'
        json_text = critic._extract_json(text)
        assert '"status"' in json_text

    def test_extract_json_empty(self):
        critic = CriticAgent()
        text = "no json here"
        json_text = critic._extract_json(text)
        assert json_text == ""

    def test_parse_review_valid(self):
        critic = CriticAgent()
        raw = """```json
{
  "status": "pass",
  "score": 85,
  "summary": "good",
  "issues": []
}
```"""
        result = critic._parse_review(raw)
        assert result.status == ReviewStatus.PASS
        assert result.score == 85
        assert result.summary == "good"
        assert result.issues == []

    def test_parse_review_with_issues(self):
        critic = CriticAgent()
        raw = """```json
{
  "status": "fail",
  "score": 30,
  "summary": "bad",
  "issues": [
    {
      "dimension": "correctness",
      "severity": "critical",
      "description": "bug",
      "suggestion": "fix it",
      "location": "line 5"
    }
  ]
}
```"""
        result = critic._parse_review(raw)
        assert result.status == ReviewStatus.FAIL
        assert len(result.issues) == 1
        assert result.issues[0].severity == "critical"

    def test_parse_review_invalid_json(self):
        critic = CriticAgent()
        raw = "not json at all"
        result = critic._parse_review(raw)
        assert result.status == ReviewStatus.NEEDS_IMPROVEMENT
        assert result.score == 50

    def test_extract_code_from_markdown(self):
        critic = CriticAgent()
        text = """```python
def hello():
    pass
```"""
        code = critic._extract_code_or_text(text)
        assert "def hello" in code

    def test_extract_code_plain(self):
        critic = CriticAgent()
        text = "just plain text"
        code = critic._extract_code_or_text(text)
        assert code == "just plain text"

    def test_dimension_descriptions_exist(self):
        critic = CriticAgent()
        for dim in ["correctness", "completeness", "safety", "style", "performance"]:
            assert dim in critic.DIMENSION_DESCRIPTIONS

    def test_domain_prompts_exist(self):
        critic = CriticAgent()
        for domain in ["code", "design", "document", "test"]:
            assert domain in critic.DOMAIN_PROMPTS


class TestRulePlusCriticValidator:
    """测试混合验证器"""

    def test_init_default(self):
        validator = RulePlusCriticValidator()
        assert validator.critic is not None

    def test_init_with_critic(self):
        critic = CriticAgent()
        validator = RulePlusCriticValidator(critic_agent=critic)
        assert validator.critic is critic

    def test_validate_without_output_spec(self):
        validator = RulePlusCriticValidator()
        result = validator.validate(
            task_description="test",
            worker_output="output",
            critic_enabled=False,
        )
        assert result["rule_validation"]["passed"] is True
        assert result["critic_review"] is None
        assert result["overall_passed"] is True

    def test_validate_with_critic_enabled(self):
        validator = RulePlusCriticValidator()
        result = validator.validate(
            task_description="test",
            worker_output="output",
            critic_enabled=True,
        )
        assert result["critic_review"] is not None
        assert isinstance(result["critic_review"], ReviewResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
