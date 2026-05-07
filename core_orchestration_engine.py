#!/usr/bin/env python3
"""
核心编排引擎 (Core Orchestration Engine)
独立的、可扩展的、十年可用的核心层

核心原则：
1. 简单稳定的核心
2. 插件化架构
3. 向后兼容
4. 可观测性
"""

import json
import yaml
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# ==================== 可观测性系统 ====================
class Observer:
    """可观测性系统 - 指标、日志、追踪、审计"""
    
    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or Path("./logs")
        self.log_dir.mkdir(exist_ok=True)
        self.metrics = {
            "workflows_total": 0,
            "tasks_total": 0,
            "tasks_success": 0,
            "tasks_failed": 0
        }
        self.traces = []
        self._setup_logger()
    
    def _setup_logger(self):
        self.logger = logging.getLogger("orchestration")
        handler = logging.FileHandler(self.log_dir / "orchestration.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
    
    def log(self, level: str, message: str, context: Dict = None):
        """结构化日志"""
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        context_str = json.dumps(context) if context else ""
        log_method(f"{message} {context_str}")
    
    def track_metric(self, key: str, value: int = 1):
        """记录指标"""
        if key in self.metrics:
            self.metrics[key] += value
        else:
            self.metrics[key] = value
    
    def audit(self, event: str, actor: str = "system", details: Dict = None):
        """审计日志"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "actor": actor,
            "details": details
        }
        audit_file = self.log_dir / "audit.jsonl"
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
        self.log("INFO", f"Audit event: {event}", audit_entry)
    
    def get_metrics(self) -> Dict:
        """获取指标"""
        return self.metrics

# ==================== 插件架构 ====================
class PluginManager:
    """插件管理器 - 支持工具插件、验证插件、提示插件"""
    
    def __init__(self):
        self.plugins: Dict[str, Dict] = {}
    
    def register_tool_plugin(self, name: str, execute_func: Callable):
        """注册工具插件"""
        self.plugins[f"tool:{name}"] = {"type": "tool", "execute": execute_func}
    
    def register_validator_plugin(self, name: str, validate_func: Callable):
        """注册验证插件"""
        self.plugins[f"validator:{name}"] = {"type": "validator", "validate": validate_func}
    
    def register_prompt_plugin(self, name: str, build_func: Callable):
        """注册提示插件"""
        self.plugins[f"prompt:{name}"] = {"type": "prompt", "build": build_func}
    
    def get_tool(self, name: str) -> Optional[Dict]:
        """获取工具插件"""
        return self.plugins.get(f"tool:{name}")
    
    def get_validator(self, name: str) -> Optional[Dict]:
        """获取验证插件"""
        return self.plugins.get(f"validator:{name}")
    
    def list_plugins(self) -> List:
        """列出所有插件"""
        return list(self.plugins.keys())

# ==================== 核心数据模型 ====================
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class Task:
    id: str
    name: str
    description: str = ""
    tool: str = "script"
    instruction: str = ""
    depends_on: List[str] = field(default_factory=list)
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 300
    parallel: bool = False
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    errors: List[str] = field(default_factory=list)

@dataclass
class Workflow:
    id: str
    name: str
    version: str = "1.0"
    description: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    tasks: List[Task] = field(default_factory=list)
    max_parallel: int = 4
    state_file: Optional[str] = None

# ==================== 核心编排引擎 ====================
class CoreOrchestrationEngine:
    """
    核心编排引擎 - 十年可用的稳定核心
    
    功能：
    - 拓扑排序与任务调度
    - 插件化工具执行
    - 可观测性
    - 版本兼容
    """
    
    def __init__(self, plugin_manager: PluginManager = None, observer: Observer = None):
        self.plugin_manager = plugin_manager or PluginManager()
        self.observer = observer or Observer()
        self.history: List[Dict] = []
        self.observer.log("INFO", "Core Orchestration Engine initialized")
        self.observer.audit("system.start")
    
    def parse_workflow(self, file_path: Path) -> Workflow:
        """解析工作流文件（支持 YAML/JSON）"""
        self.observer.log("INFO", f"Parsing workflow: {file_path}")
        
        if file_path.suffix in [".yaml", ".yml"]:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        elif file_path.suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported format: {file_path.suffix}")
        
        return self._data_to_workflow(data)
    
    def _data_to_workflow(self, data: Dict) -> Workflow:
        """转换数据到工作流对象"""
        workflow = Workflow(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            variables=data.get("variables", {}),
            max_parallel=data.get("max_parallel", 4)
        )
        
        for task_data in data.get("tasks", []):
            workflow.tasks.append(Task(
                id=task_data.get("id", ""),
                name=task_data.get("name", ""),
                description=task_data.get("description", ""),
                tool=task_data.get("tool", "script"),
                instruction=task_data.get("instruction", ""),
                depends_on=task_data.get("depends_on", []),
                max_retries=task_data.get("max_retries", 3),
                retry_delay=task_data.get("retry_delay", 5),
                timeout=task_data.get("timeout", 300),
                parallel=task_data.get("parallel", False)
            ))
        
        return workflow
    
    def _topological_sort(self, workflow: Workflow) -> List[List[Task]]:
        """拓扑排序 - 分层执行"""
        task_map = {t.id: t for t in workflow.tasks}
        completed = set()
        layers = []
        
        while len(completed) < len(workflow.tasks):
            ready = []
            for task in workflow.tasks:
                if task.id not in completed:
                    if all(dep in completed for dep in task.depends_on):
                        ready.append(task)
            
            if not ready:
                remaining = [t.id for t in workflow.tasks if t.id not in completed]
                raise RuntimeError(f"Circular dependency detected: {remaining}")
            
            layers.append(ready)
            completed.update(t.id for t in ready)
        
        return layers
    
    def execute_workflow(self, workflow: Workflow) -> Dict:
        """执行工作流"""
        start_time = datetime.now()
        
        self.observer.log("INFO", f"Executing workflow: {workflow.name}")
        self.observer.audit("workflow.start", details={"workflow_id": workflow.id})
        self.observer.track_metric("workflows_total")
        
        layers = self._topological_sort(workflow)
        results = {
            "workflow_id": workflow.id,
            "started_at": start_time.isoformat(),
            "layers": [],
            "tasks": []
        }
        
        for layer_num, layer_tasks in enumerate(layers, 1):
            self.observer.log("INFO", f"Executing layer {layer_num}")
            layer_result = {
                "layer": layer_num,
                "tasks": []
            }
            
            # 层内执行（串行或并行）
            for task in layer_tasks:
                task_result = self._execute_task_with_retry(task, workflow)
                results["tasks"].append(task_result)
                layer_result["tasks"].append(task_result)
            
            results["layers"].append(layer_result)
        
        end_time = datetime.now()
        results["completed_at"] = end_time.isoformat()
        results["duration_seconds"] = (end_time - start_time).total_seconds()
        results["success"] = all(t.get("success", False) for t in results["tasks"])
        
        self.history.append(results)
        
        # 保存历史
        history_file = Path("./history") / f"{workflow.id}_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        history_file.parent.mkdir(exist_ok=True)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        self.observer.log("INFO", f"Workflow completed: {results['success']}")
        self.observer.audit("workflow.complete", details={"success": results['success']})
        
        return results
    
    def _execute_task_with_retry(self, task: Task, workflow: Workflow) -> Dict:
        """任务执行与重试"""
        self.observer.track_metric("tasks_total")
        
        for attempt in range(task.max_retries + 1):
            if attempt > 0:
                self.observer.log("INFO", f"Retry attempt {attempt}/{task.max_retries} for {task.id}")
                time.sleep(task.retry_delay * attempt)
            
            result = self._execute_single_task(task, workflow)
            
            if result["success"] or result["status"] == "skipped":
                self.observer.track_metric("tasks_success")
                return result
        
        self.observer.track_metric("tasks_failed")
        return result
    
    def _execute_single_task(self, task: Task, workflow: Workflow) -> Dict:
        """执行单个任务"""
        print(f"  📋 {task.name} ({task.id})")
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        result = {
            "task_id": task.id,
            "task_name": task.name,
            "status": "failed",
            "success": False,
            "errors": [],
            "started_at": task.started_at.isoformat(),
            "retry_count": task.retry_count
        }
        
        try:
            # 工具插件执行
            tool_plugin = self.plugin_manager.get_tool(task.tool)
            if tool_plugin:
                tool_output = tool_plugin["execute"](task.instruction)
                result["output"] = tool_output
                result["success"] = True
                result["status"] = "completed"
            else:
                # 默认脚本执行
                exec(task.instruction)
                result["success"] = True
                result["status"] = "completed"
            
        except Exception as e:
            task.errors.append(str(e))
            result["errors"].append(str(e))
            self.observer.log("ERROR", f"Task failed: {task.id}", {"error": str(e)})
        
        task.completed_at = datetime.now()
        result["completed_at"] = task.completed_at.isoformat()
        result["duration_seconds"] = (task.completed_at - task.started_at).total_seconds()
        
        return result

# ==================== 示例：内置插件 ====================
def register_builtin_plugins(plugin_manager: PluginManager):
    """注册内置插件"""
    
    # 脚本工具插件
    def execute_script(instruction: str):
        exec(instruction)
        return {"status": "ok"}
    
    plugin_manager.register_tool_plugin("script", execute_script)
    print("✅ Built-in plugins registered")

def demo():
    """演示核心引擎"""
    print("=" * 70)
    print("🚀 核心编排引擎演示 - 为未来十年设计")
    print("=" * 70)
    print("\n💡 核心特性：")
    print("   1️⃣  简单稳定的核心")
    print("   2️⃣  插件化架构")
    print("   3️⃣  可观测性（指标、日志、审计）")
    print("   4️⃣  工作流历史记录")
    print("   5️⃣  向后兼容设计")
    
    # 初始化
    observer = Observer()
    plugin_manager = PluginManager()
    register_builtin_plugins(plugin_manager)
    
    engine = CoreOrchestrationEngine(plugin_manager, observer)
    
    # 创建简单测试工作流
    test_workflow_data = {
        "id": "core_demo",
        "name": "核心引擎演示",
        "version": "1.0",
        "tasks": [
            {"id": "step1", "name": "第一步", "instruction": "print('✅ Step1 done')"},
            {"id": "step2", "name": "第二步", "instruction": "print('✅ Step2 done')", "depends_on": ["step1"]},
            {"id": "step3", "name": "第三步", "instruction": "print('✅ Step3 done')", "depends_on": ["step1"], "parallel": True}
        ]
    }
    
    with open("core_demo.yaml", "w", encoding="utf-8") as f:
        yaml.dump(test_workflow_data, f, allow_unicode=True)
    
    # 解析并执行
    workflow = engine._data_to_workflow(test_workflow_data)
    
    print("\n" + "=" * 70)
    print("📊 执行工作流")
    print("=" * 70)
    
    result = engine.execute_workflow(workflow)
    
    print("\n" + "=" * 70)
    print("📈 可观测性")
    print("=" * 70)
    print(f"\n📊 指标：{json.dumps(observer.get_metrics(), indent=2)}")
    print(f"\n📝 日志文件：./logs/orchestration.log")
    print(f"📜 审计日志：./logs/audit.jsonl")
    print(f"📚 工作流历史：./history/")
    
    print("\n" + "=" * 70)
    print("✅ 核心引擎演示完成 - 这是为未来十年准备的架构！")
    print("=" * 70)

if __name__ == "__main__":
    demo()

