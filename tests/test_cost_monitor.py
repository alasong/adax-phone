#!/usr/bin/env python3
"""成本监控 - 追踪 token 用量和费用，防止预算超支"""

import pytest
import json
import time
from pathlib import Path


class TestCostMonitor:
    """测试成本监控器"""

    def test_track_single_usage(self):
        """追踪单次使用"""
        from cost_monitor import CostMonitor
        monitor = CostMonitor()
        
        monitor.record_usage(
            task_id="task_1",
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500,
            cost=0.05,
        )
        
        stats = monitor.get_stats()
        assert stats["total_cost"] == 0.05
        assert stats["total_input_tokens"] == 1000
        assert stats["total_output_tokens"] == 500

    def test_track_multiple_usages(self):
        """追踪多次使用"""
        from cost_monitor import CostMonitor
        monitor = CostMonitor()
        
        monitor.record_usage(task_id="t1", model="gpt-4", input_tokens=1000, output_tokens=500, cost=0.05)
        monitor.record_usage(task_id="t2", model="gpt-4", input_tokens=2000, output_tokens=1000, cost=0.10)
        
        stats = monitor.get_stats()
        assert stats["total_cost"] == 0.15
        assert stats["total_tasks"] == 2

    def test_budget_check_pass(self):
        """预算检查 - 未超支"""
        from cost_monitor import CostMonitor
        monitor = CostMonitor(budget=1.0)
        
        monitor.record_usage(task_id="t1", model="gpt-4", input_tokens=1000, output_tokens=500, cost=0.05)
        
        assert monitor.is_within_budget() is True
        assert monitor.get_budget_usage() == 0.05

    def test_budget_check_exceeded(self):
        """预算检查 - 超支"""
        from cost_monitor import CostMonitor
        monitor = CostMonitor(budget=0.10)
        
        monitor.record_usage(task_id="t1", model="gpt-4", input_tokens=1000, output_tokens=500, cost=0.05)
        monitor.record_usage(task_id="t2", model="gpt-4", input_tokens=2000, output_tokens=1000, cost=0.08)
        
        assert monitor.is_within_budget() is False
        assert monitor.get_budget_usage() == 1.3

    def test_budget_warning_threshold(self):
        """预算警告阈值"""
        from cost_monitor import CostMonitor
        monitor = CostMonitor(budget=1.0, warning_threshold=0.8)
        
        monitor.record_usage(task_id="t1", model="gpt-4", input_tokens=1000, output_tokens=500, cost=0.85)
        
        assert monitor.is_within_budget() is True
        assert monitor.is_warning_triggered() is True

    def test_model_pricing(self):
        """模型定价计算"""
        from cost_monitor import CostMonitor, ModelPricing
        pricing = ModelPricing()
        
        cost = pricing.calculate_cost("gpt-4", input_tokens=1000, output_tokens=500)
        assert cost > 0

    def test_persist_and_restore(self, tmp_path):
        """持久化和恢复"""
        from cost_monitor import CostMonitor
        state_file = tmp_path / "cost_state.json"
        
        monitor = CostMonitor(budget=1.0)
        monitor.record_usage(task_id="t1", model="gpt-4", input_tokens=1000, output_tokens=500, cost=0.05)
        monitor.save_state(str(state_file))
        
        monitor2 = CostMonitor.load_state(str(state_file))
        stats = monitor2.get_stats()
        assert stats["total_cost"] == 0.05

    def test_rate_limit_check(self):
        """速率限制检查"""
        from cost_monitor import CostMonitor
        monitor = CostMonitor(max_requests_per_minute=10)
        
        for i in range(10):
            monitor.record_usage(task_id=f"t{i}", model="gpt-4", input_tokens=100, output_tokens=50, cost=0.001)
            assert monitor.check_rate_limit() is True
        
        # 第 11 次应该被限制
        monitor.record_usage(task_id="t10", model="gpt-4", input_tokens=100, output_tokens=50, cost=0.001)
        assert monitor.check_rate_limit() is False

    def test_get_usage_by_task(self):
        """按任务查询用量"""
        from cost_monitor import CostMonitor
        monitor = CostMonitor()
        
        monitor.record_usage(task_id="t1", model="gpt-4", input_tokens=1000, output_tokens=500, cost=0.05)
        monitor.record_usage(task_id="t2", model="gpt-4", input_tokens=2000, output_tokens=1000, cost=0.10)
        monitor.record_usage(task_id="t1", model="gpt-4", input_tokens=500, output_tokens=200, cost=0.02)
        
        t1_usage = monitor.get_usage_by_task("t1")
        assert t1_usage["total_cost"] == 0.07
        assert t1_usage["total_requests"] == 2

    def test_get_usage_by_model(self):
        """按模型查询用量"""
        from cost_monitor import CostMonitor
        monitor = CostMonitor()
        
        monitor.record_usage(task_id="t1", model="gpt-4", input_tokens=1000, output_tokens=500, cost=0.05)
        monitor.record_usage(task_id="t2", model="gpt-3.5", input_tokens=5000, output_tokens=2000, cost=0.01)
        
        model_stats = monitor.get_usage_by_model()
        assert "gpt-4" in model_stats
        assert "gpt-3.5" in model_stats


class TestCostGuard:
    """测试成本保护器（自动暂停）"""

    def test_auto_pause_on_budget_exceeded(self):
        """预算超支时自动暂停"""
        from cost_monitor import CostGuard
        guard = CostGuard(budget=0.10)
        
        guard.record(task_id="t1", cost=0.05)
        assert guard.should_continue() is True
        
        guard.record(task_id="t2", cost=0.08)
        assert guard.should_continue() is False

    def test_auto_pause_on_rate_limit(self):
        """速率限制时自动暂停"""
        from cost_monitor import CostGuard
        guard = CostGuard(max_requests_per_minute=5)
        
        for i in range(5):
            guard.record(task_id=f"t{i}", cost=0.001)
        
        assert guard.should_continue() is False

    def test_resume_after_pause(self):
        """暂停后恢复"""
        from cost_monitor import CostGuard
        guard = CostGuard(budget=0.10)
        
        guard.record(task_id="t1", cost=0.15)
        assert guard.should_continue() is False
        
        guard.increase_budget(0.10)
        assert guard.should_continue() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
