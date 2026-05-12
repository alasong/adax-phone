#!/usr/bin/env python3
"""核心编排引擎单元测试"""

import pytest
import json
from pathlib import Path
from core_orchestration_engine import (
    CoreOrchestrationEngine,
    Workflow,
    Task,
    PluginManager,
    Observer,
    TaskStatus,
    register_builtin_plugins
)


class TestPluginManager:
    """测试插件管理器"""

    def test_register_tool_plugin(self):
        pm = PluginManager()
        pm.register_tool_plugin("test_tool", lambda x: x)
        assert pm.get_tool("test_tool") is not None
        assert pm.get_tool("test_tool")["type"] == "tool"

    def test_register_validator_plugin(self):
        pm = PluginManager()
        pm.register_validator_plugin("test_validator", lambda x: True)
        assert pm.get_validator("test_validator") is not None

    def test_register_prompt_plugin(self):
        pm = PluginManager()
        pm.register_prompt_plugin("test_prompt", lambda x: "prompt")
        plugin = pm.plugins.get("prompt:test_prompt")
        assert plugin is not None
        assert plugin["type"] == "prompt"

    def test_list_plugins(self):
        pm = PluginManager()
        pm.register_tool_plugin("tool1", lambda x: x)
        pm.register_tool_plugin("tool2", lambda x: x)
        assert len(pm.list_plugins()) == 2


class TestWorkflow:
    """测试工作流数据模型"""

    def test_create_workflow(self):
        wf = Workflow(id="test", name="Test Workflow")
        assert wf.id == "test"
        assert wf.name == "Test Workflow"
        assert wf.version == "1.0"
        assert wf.tasks == []

    def test_create_workflow_with_tasks(self):
        wf = Workflow(
            id="test",
            name="Test",
            tasks=[
                Task(id="t1", name="Task 1"),
                Task(id="t2", name="Task 2", depends_on=["t1"])
            ]
        )
        assert len(wf.tasks) == 2
        assert wf.tasks[1].depends_on == ["t1"]


class TestTopologicalSort:
    """测试拓扑排序"""

    def test_simple_linear(self):
        engine = CoreOrchestrationEngine()
        wf = Workflow(
            id="test",
            name="Test",
            tasks=[
                Task(id="a", name="A"),
                Task(id="b", name="B", depends_on=["a"]),
                Task(id="c", name="C", depends_on=["b"])
            ]
        )
        layers = engine._topological_sort(wf)
        assert len(layers) == 3
        assert layers[0][0].id == "a"
        assert layers[1][0].id == "b"
        assert layers[2][0].id == "c"

    def test_parallel_tasks(self):
        engine = CoreOrchestrationEngine()
        wf = Workflow(
            id="test",
            name="Test",
            tasks=[
                Task(id="a", name="A"),
                Task(id="b", name="B", depends_on=["a"]),
                Task(id="c", name="C", depends_on=["a"])
            ]
        )
        layers = engine._topological_sort(wf)
        assert len(layers) == 2
        assert layers[0][0].id == "a"
        assert len(layers[1]) == 2

    def test_circular_dependency(self):
        engine = CoreOrchestrationEngine()
        wf = Workflow(
            id="test",
            name="Test",
            tasks=[
                Task(id="a", name="A", depends_on=["b"]),
                Task(id="b", name="B", depends_on=["a"])
            ]
        )
        with pytest.raises(RuntimeError, match="Circular dependency"):
            engine._topological_sort(wf)


class TestObserver:
    """测试可观测性系统"""

    def test_track_metric(self):
        observer = Observer()
        observer.track_metric("test_metric")
        observer.track_metric("test_metric")
        assert observer.get_metrics()["test_metric"] == 2

    def test_audit_log(self, tmp_path):
        observer = Observer(log_dir=tmp_path)
        observer.audit("test.event", actor="test_user", details={"key": "value"})
        audit_file = tmp_path / "audit.jsonl"
        assert audit_file.exists()
        with open(audit_file, "r") as f:
            lines = f.readlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["event"] == "test.event"
        assert entry["actor"] == "test_user"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
