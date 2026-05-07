#!/usr/bin/env python3
"""
工作流测试框架 (Workflow Testing Framework)
测试你的工作流，确保质量不退化

支持：
- 单元测试（单个任务）
- 集成测试（完整流程）
- 回滚测试（失败后处理）
"""

import yaml
import json
from typing import Dict, List, Callable
from pathlib import Path
from core_orchestration_engine import (
    CoreOrchestrationEngine,
    Workflow,
    Task,
    PluginManager,
    Observer,
    register_builtin_plugins
)

# ==================== 测试断言系统 ====================
class AssertionEngine:
    """断言引擎 - 验证工作流输出"""
    
    @staticmethod
    def assert_status(result: Dict, expected_status: str = "completed") -> bool:
        """断言任务状态"""
        return result.get("status") == expected_status
    
    @staticmethod
    def assert_success(result: Dict) -> bool:
        """断言任务成功"""
        return result.get("success", False)
    
    @staticmethod
    def assert_task_output(task_result: Dict, expected_output: Dict) -> bool:
        """断言输出符合预期"""
        output = task_result.get("output", {})
        for key, value in expected_output.items():
            if output.get(key) != value:
                return False
        return True
    
    @staticmethod
    def assert_task_in_results(results: List[Dict], task_id: str) -> bool:
        """断言任务在结果中"""
        return any(t.get("task_id") == task_id for t in results)
    
    @staticmethod
    def assert_duration(task_result: Dict, max_seconds: float) -> bool:
        """断言耗时在合理范围内"""
        duration = task_result.get("duration_seconds", 0)
        return duration < max_seconds
    
    @staticmethod
    def assert_no_errors(task_result: Dict) -> bool:
        """断言没有错误"""
        return len(task_result.get("errors", [])) == 0

# ==================== 测试用例 ====================
class WorkflowTestCase:
    """工作流测试用例"""
    
    def __init__(self, name: str, workflow: Workflow):
        self.name = name
        self.workflow = workflow
        self.assertions: List[Callable] = []
    
    def add_assertion(self, assertion: Callable):
        """添加断言"""
        self.assertions.append(assertion)
    
    def run(self, engine: CoreOrchestrationEngine) -> Dict:
        """运行测试"""
        print(f"\n🧪 测试用例: {self.name}")
        print("─" * 50)
        
        result = engine.execute_workflow(self.workflow)
        
        passed = 0
        failed = 0
        
        for i, assertion in enumerate(self.assertions, 1):
            try:
                if assertion(result):
                    print(f"   ✅ 断言 {i}: 通过")
                    passed += 1
                else:
                    print(f"   ❌ 断言 {i}: 失败")
                    failed += 1
            except Exception as e:
                print(f"   ❌ 断言 {i}: 异常 - {e}")
                failed += 1
        
        overall_success = failed == 0
        print(f"\n{'✅ 测试通过' if overall_success else '❌ 测试失败'}: {passed}/{passed+failed}")
        
        return {"success": overall_success, "passed": passed, "failed": failed, "result": result}

# ==================== 测试套件 ====================
class WorkflowTestSuite:
    """工作流测试套件"""
    
    def __init__(self, name: str = "Workflow Test Suite"):
        self.name = name
        self.test_cases: List[WorkflowTestCase] = []
        self.engine = None
        self._setup_engine()
    
    def _setup_engine(self):
        """设置引擎"""
        observer = Observer()
        plugin_manager = PluginManager()
        register_builtin_plugins(plugin_manager)
        self.engine = CoreOrchestrationEngine(plugin_manager, observer)
    
    def add_test_case(self, test_case: WorkflowTestCase):
        """添加测试用例"""
        self.test_cases.append(test_case)
    
    def run_all(self) -> Dict:
        """运行所有测试"""
        print("=" * 70)
        print(f"🧪 {self.name}")
        print("=" * 70)
        
        summary = {
            "total": len(self.test_cases),
            "passed": 0,
            "failed": 0,
            "test_results": []
        }
        
        for case in self.test_cases:
            result = case.run(self.engine)
            summary["test_results"].append(result)
            if result["success"]:
                summary["passed"] += 1
            else:
                summary["failed"] += 1
        
        print("\n" + "=" * 70)
        print("📊 测试套件总结")
        print("=" * 70)
        print(f"   总计: {summary['total']}")
        print(f"   通过: {summary['passed']}")
        print(f"   失败: {summary['failed']}")
        print(f"   结果: {'✅ 通过' if summary['failed'] == 0 else '❌ 失败'}")
        print("=" * 70)
        
        return summary

# ==================== 示例测试 ====================
def create_sample_test_suite() -> WorkflowTestSuite:
    """创建示例测试套件"""
    
    suite = WorkflowTestSuite("示例工作流测试套件")
    
    # 测试1: 简单工作流成功完成
    workflow1 = Workflow(
        id="simple_success",
        name="简单成功测试",
        tasks=[
            Task(id="task1", name="任务1", instruction="print('OK')"),
            Task(id="task2", name="任务2", instruction="print('OK')", depends_on=["task1"])
        ]
    )
    
    test_case1 = WorkflowTestCase("简单成功工作流", workflow1)
    test_case1.add_assertion(lambda r: all(t["success"] for t in r["tasks"]))
    test_case1.add_assertion(lambda r: r["success"])
    
    # 测试2: 并行执行
    workflow2 = Workflow(
        id="parallel_test",
        name="并行执行测试",
        max_parallel=4,
        tasks=[
            Task(id="t1", name="并行任务1", instruction="print('t1')", parallel=True),
            Task(id="t2", name="并行任务2", instruction="print('t2')", parallel=True),
            Task(id="t3", name="串行任务", instruction="print('t3')", depends_on=["t1", "t2"])
        ]
    )
    
    test_case2 = WorkflowTestCase("并行执行测试", workflow2)
    test_case2.add_assertion(lambda r: len(r["tasks"]) == 3)
    test_case2.add_assertion(lambda r: r["success"])
    
    # 添加测试用例
    suite.add_test_case(test_case1)
    suite.add_test_case(test_case2)
    
    return suite

def demo():
    """演示测试框架"""
    print("=" * 70)
    print("🧪 工作流测试框架演示")
    print("=" * 70)
    print("\n💡 为什么需要工作流测试？")
    print("   1️⃣  确保工作流质量不退化")
    print("   2️⃣  变更前验证流程正确性")
    print("   3️⃣  捕获边界情况")
    print("   4️⃣  提供安全的重构保障")
    
    suite = create_sample_test_suite()
    results = suite.run_all()
    
    print("\n✅ 测试框架演示完成！")
    print("\n📝 下一步：")
    print("   1. 为你的业务流程编写测试用例")
    print("   2. 在 CI 中集成测试框架")
    print("   3. 每次工作流变更都运行测试")

if __name__ == "__main__":
    demo()

