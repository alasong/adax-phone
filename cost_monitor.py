#!/usr/bin/env python3
"""
成本监控 - 追踪 token 用量和费用，防止预算超支

解决 AI 根本性缺陷：成本不可控
- Token 用量追踪
- 费用计算
- 预算限流
- 自动暂停
"""

import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class UsageRecord:
    """单次使用记录"""
    task_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class ModelPricing:
    """模型定价表"""
    
    PRICING = {
        # OpenAI (per 1M tokens, USD)
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        "gpt-3.5": {"input": 0.5, "output": 1.5},
        # Anthropic (per 1M tokens, USD)
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        # DeepSeek (per 1M tokens, USD)
        "deepseek-chat": {"input": 0.14, "output": 0.28},
        "deepseek-coder": {"input": 0.14, "output": 0.28},
    }
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """计算费用"""
        pricing = self.PRICING.get(model, {"input": 1.0, "output": 2.0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)
    
    def get_supported_models(self) -> List[str]:
        return list(self.PRICING.keys())


class CostMonitor:
    """
    成本监控器 - 追踪 token 用量和费用
    
    功能：
    - 记录每次 AI 调用的 token 用量和费用
    - 预算检查和警告
    - 按任务/模型统计
    - 持久化状态
    """
    
    def __init__(
        self,
        budget: float = 10.0,
        warning_threshold: float = 0.8,
        max_requests_per_minute: int = 60,
    ):
        self.budget = budget
        self.warning_threshold = warning_threshold
        self.max_requests_per_minute = max_requests_per_minute
        self.pricing = ModelPricing()
        self._records: List[UsageRecord] = []
        self._request_timestamps: List[float] = []
    
    def record_usage(
        self,
        task_id: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = None,
    ):
        """
        记录使用量
        
        Args:
            task_id: 任务 ID
            model: 模型名称
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            cost: 费用（如果为 None，自动计算）
        """
        if cost is None:
            cost = self.pricing.calculate_cost(model, input_tokens, output_tokens)
        
        record = UsageRecord(
            task_id=task_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )
        self._records.append(record)
        self._request_timestamps.append(time.time())
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if not self._records:
            return {
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_tasks": 0,
                "total_requests": 0,
            }
        
        total_cost = sum(r.cost for r in self._records)
        total_input = sum(r.input_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)
        unique_tasks = set(r.task_id for r in self._records)
        
        return {
            "total_cost": round(total_cost, 4),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_tasks": len(unique_tasks),
            "total_requests": len(self._records),
        }
    
    def is_within_budget(self) -> bool:
        """检查是否在预算内"""
        total_cost = sum(r.cost for r in self._records)
        return total_cost <= self.budget
    
    def get_budget_usage(self) -> float:
        """获取预算使用率 (0-1)"""
        total_cost = sum(r.cost for r in self._records)
        return round(total_cost / self.budget, 4) if self.budget > 0 else 0
    
    def is_warning_triggered(self) -> bool:
        """检查是否触发警告阈值"""
        return self.get_budget_usage() >= self.warning_threshold
    
    def check_rate_limit(self) -> bool:
        """检查速率限制"""
        now = time.time()
        one_minute_ago = now - 60
        
        # 清理旧记录
        self._request_timestamps = [t for t in self._request_timestamps if t > one_minute_ago]
        
        return len(self._request_timestamps) < self.max_requests_per_minute
    
    def get_usage_by_task(self, task_id: str) -> Dict:
        """按任务查询用量"""
        task_records = [r for r in self._records if r.task_id == task_id]
        if not task_records:
            return {"total_cost": 0, "total_requests": 0}
        
        return {
            "total_cost": round(sum(r.cost for r in task_records), 4),
            "total_requests": len(task_records),
            "total_input_tokens": sum(r.input_tokens for r in task_records),
            "total_output_tokens": sum(r.output_tokens for r in task_records),
        }
    
    def get_usage_by_model(self) -> Dict[str, Dict]:
        """按模型查询用量"""
        model_stats = {}
        for r in self._records:
            if r.model not in model_stats:
                model_stats[r.model] = {
                    "total_cost": 0,
                    "total_requests": 0,
                    "total_tokens": 0,
                }
            model_stats[r.model]["total_cost"] += r.cost
            model_stats[r.model]["total_requests"] += 1
            model_stats[r.model]["total_tokens"] += r.input_tokens + r.output_tokens
        
        for model in model_stats:
            model_stats[model]["total_cost"] = round(model_stats[model]["total_cost"], 4)
        
        return model_stats
    
    def save_state(self, path: str):
        """保存状态到文件"""
        state = {
            "budget": self.budget,
            "warning_threshold": self.warning_threshold,
            "max_requests_per_minute": self.max_requests_per_minute,
            "records": [
                {
                    "task_id": r.task_id,
                    "model": r.model,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost": r.cost,
                    "timestamp": r.timestamp,
                }
                for r in self._records
            ],
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
    
    @classmethod
    def load_state(cls, path: str) -> "CostMonitor":
        """从文件加载状态"""
        with open(path, "r") as f:
            state = json.load(f)
        
        monitor = cls(
            budget=state.get("budget", 10.0),
            warning_threshold=state.get("warning_threshold", 0.8),
            max_requests_per_minute=state.get("max_requests_per_minute", 60),
        )
        
        for r in state.get("records", []):
            monitor._records.append(UsageRecord(**r))
        
        return monitor


class CostGuard:
    """
    成本保护器 - 自动暂停超支任务
    
    功能：
    - 预算超支时自动暂停
    - 速率限制时自动暂停
    - 支持手动增加预算恢复
    """
    
    def __init__(
        self,
        budget: float = 10.0,
        max_requests_per_minute: int = 60,
        warning_threshold: float = 0.8,
    ):
        self.monitor = CostMonitor(
            budget=budget,
            warning_threshold=warning_threshold,
            max_requests_per_minute=max_requests_per_minute,
        )
        self._paused = False
        self._pause_reason = ""
    
    def record(self, task_id: str, cost: float, model: str = "unknown",
               input_tokens: int = 0, output_tokens: int = 0):
        """记录使用量"""
        self.monitor.record_usage(
            task_id=task_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )
        
        # 检查是否应该暂停
        if not self.monitor.is_within_budget():
            self._paused = True
            self._pause_reason = f"预算超支 (已用 ${self.monitor.get_stats()['total_cost']:.2f} / 预算 ${self.monitor.budget:.2f})"
        elif not self.monitor.check_rate_limit():
            self._paused = True
            self._pause_reason = "速率限制 (请求过于频繁)"
    
    def should_continue(self) -> bool:
        """检查是否应该继续执行"""
        if self._paused:
            return False
        return True
    
    def get_pause_reason(self) -> str:
        """获取暂停原因"""
        return self._pause_reason
    
    def increase_budget(self, amount: float):
        """增加预算并恢复执行"""
        self.monitor.budget += amount
        if self.monitor.is_within_budget():
            self._paused = False
            self._pause_reason = ""
    
    def reset(self):
        """重置保护器"""
        self._paused = False
        self._pause_reason = ""
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "paused": self._paused,
            "pause_reason": self._pause_reason,
            "budget_usage": self.monitor.get_budget_usage(),
            "stats": self.monitor.get_stats(),
        }


def demo():
    """演示成本监控"""
    print("=" * 70)
    print("💰 成本监控演示")
    print("=" * 70)
    
    monitor = CostMonitor(budget=1.0)
    
    # 模拟多次调用
    tasks = [
        ("task_1", "gpt-4", 1000, 500),
        ("task_2", "gpt-4", 2000, 1000),
        ("task_3", "gpt-3.5", 5000, 2000),
        ("task_1", "gpt-4", 500, 200),
    ]
    
    for task_id, model, input_tok, output_tok in tasks:
        monitor.record_usage(
            task_id=task_id,
            model=model,
            input_tokens=input_tok,
            output_tokens=output_tok,
        )
        stats = monitor.get_stats()
        budget_usage = monitor.get_budget_usage()
        print(f"   {task_id}: cost=${stats['total_cost']:.4f}, "
              f"budget={budget_usage*100:.1f}%, "
              f"warning={'⚠️' if monitor.is_warning_triggered() else '✅'}")
    
    print(f"\n📊 总统计: {monitor.get_stats()}")
    print(f"   按任务: {monitor.get_usage_by_task('task_1')}")
    print(f"   按模型: {monitor.get_usage_by_model()}")
    
    # 成本保护器演示
    print("\n🔒 成本保护器演示")
    guard = CostGuard(budget=0.10)
    
    guard.record("t1", cost=0.05)
    print(f"   t1 后: should_continue={guard.should_continue()}")
    
    guard.record("t2", cost=0.08)
    print(f"   t2 后: should_continue={guard.should_continue()}")
    print(f"   暂停原因: {guard.get_pause_reason()}")
    
    guard.increase_budget(0.10)
    print(f"   增加预算后: should_continue={guard.should_continue()}")
    
    print("\n" + "=" * 70)
    print("✅ 成本监控演示完成！")
    print("=" * 70)


if __name__ == "__main__":
    demo()
