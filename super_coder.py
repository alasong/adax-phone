#!/usr/bin/env python3
"""
超级Coding工具 - 基于aider，支持多种AI工具的迭代开发平台
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# 导入任务编排模块
try:
    from task_orchestrator import (
        TaskOrchestrator,
        TaskParser,
        TaskExecutor,
        Workflow
    )
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False


class ToolType(Enum):
    """支持的工具类型"""
    AIDER = "aider"
    CLAUDE = "claude"
    CODEX = "codex"


@dataclass
class ProjectConfig:
    """项目配置"""
    project_path: Path
    tools: List[ToolType] = field(default_factory=lambda: [ToolType.AIDER])
    auto_commit: bool = True
    iterations: int = 3
    verbose: bool = False
    tool_configs: Dict[ToolType, Dict] = field(default_factory=dict)
    git_config: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """配置管理器"""
    
    @staticmethod
    def load_config(config_path: Path = None) -> Dict:
        """从文件加载配置"""
        if not config_path:
            config_path = Path("config.json")
        
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        return {}
    
    @staticmethod
    def save_config(config: Dict, config_path: Path = None):
        """保存配置到文件"""
        if not config_path:
            config_path = Path("config.json")
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)


@dataclass
class IterationResult:
    """迭代结果"""
    tool: ToolType
    success: bool
    changes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    commit_hash: Optional[str] = None


class ToolAdapter:
    """工具适配器基类"""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
    
    def execute(self, instruction: str, files: List[Path]) -> IterationResult:
        """执行指令"""
        raise NotImplementedError
    
    def is_available(self) -> bool:
        """检查工具是否可用"""
        raise NotImplementedError


class AiderAdapter(ToolAdapter):
    """Aider适配器"""
    
    def __init__(self, config: ProjectConfig, tool_config: Dict = None):
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
        result = IterationResult(tool=ToolType.AIDER, success=False)
        
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
            
            if not self.config.auto_commit:
                cmd.append("--no-auto-commits")
            
            model = self.tool_config.get("model")
            if model:
                cmd.extend(["--model", model])
            
            edit_format = self.tool_config.get("edit_format")
            if edit_format:
                cmd.extend(["--edit-format", edit_format])
            
            for f in files:
                cmd.append(str(f))
            
            if self.config.verbose:
                print(f"执行Aider命令: {' '.join(cmd)}")
            
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
            
            if self.config.verbose:
                print("Aider输出:", proc.stdout)
                if proc.stderr:
                    print("Aider错误:", proc.stderr)
            
        except Exception as e:
            result.errors.append(str(e))
        
        return result


class ClaudeAdapter(ToolAdapter):
    """Claude适配器 (框架)"""
    
    def __init__(self, config: ProjectConfig, tool_config: Dict = None):
        super().__init__(config)
        self.tool_config = tool_config or {}
    
    def is_available(self) -> bool:
        # TODO: 实现Claude可用性检查
        return False
    
    def execute(self, instruction: str, files: List[Path]) -> IterationResult:
        result = IterationResult(tool=ToolType.CLAUDE, success=False)
        # TODO: 实现Claude执行逻辑
        result.errors.append("Claude适配器尚未实现")
        return result


class CodexAdapter(ToolAdapter):
    """Codex适配器 (框架)"""
    
    def __init__(self, config: ProjectConfig, tool_config: Dict = None):
        super().__init__(config)
        self.tool_config = tool_config or {}
    
    def is_available(self) -> bool:
        # TODO: 实现Codex可用性检查
        return False
    
    def execute(self, instruction: str, files: List[Path]) -> IterationResult:
        result = IterationResult(tool=ToolType.CODEX, success=False)
        # TODO: 实现Codex执行逻辑
        result.errors.append("Codex适配器尚未实现")
        return result


class SuperCoder:
    """超级Coding工具主类"""
    
    def __init__(self, project_path: str, tools: List[str] = None, config_path: str = None):
        self.project_path = Path(project_path).resolve()
        
        # 加载配置文件
        self.config_data = ConfigManager.load_config(Path(config_path) if config_path else None)
        
        # 解析工具
        tool_map = {
            "aider": ToolType.AIDER,
            "claude": ToolType.CLAUDE,
            "codex": ToolType.CODEX
        }
        
        selected_tools = []
        if tools:
            for t in tools:
                if t in tool_map:
                    selected_tools.append(tool_map[t])
        
        # 从配置文件获取工具配置
        tool_configs = {}
        if "tools" in self.config_data:
            for tool_name, tool_cfg in self.config_data["tools"].items():
                if tool_name in tool_map:
                    tool_type = tool_map[tool_name]
                    if tool_cfg.get("enabled", False):
                        if tool_type not in selected_tools:
                            selected_tools.append(tool_type)
                    tool_configs[tool_type] = tool_cfg
        
        # 获取项目配置
        project_cfg = self.config_data.get("project", {})
        git_cfg = self.config_data.get("git", {})
        
        self.config = ProjectConfig(
            project_path=self.project_path,
            tools=selected_tools if selected_tools else [ToolType.AIDER],
            tool_configs=tool_configs,
            git_config=git_cfg
        )
        
        self.adapters: Dict[ToolType, ToolAdapter] = {}
        self._init_adapters()
    
    def _init_adapters(self):
        """初始化工具适配器"""
        # Aider
        aider_config = self.config.tool_configs.get(ToolType.AIDER, {})
        self.adapters[ToolType.AIDER] = AiderAdapter(self.config, aider_config)
        
        # Claude
        claude_config = self.config.tool_configs.get(ToolType.CLAUDE, {})
        self.adapters[ToolType.CLAUDE] = ClaudeAdapter(self.config, claude_config)
        
        # Codex
        codex_config = self.config.tool_configs.get(ToolType.CODEX, {})
        self.adapters[ToolType.CODEX] = CodexAdapter(self.config, codex_config)
    
    def check_tools(self) -> Dict[ToolType, bool]:
        """检查工具可用性"""
        availability = {}
        for tool_type, adapter in self.adapters.items():
            if tool_type in self.config.tools:
                availability[tool_type] = adapter.is_available()
        return availability
    
    def iterate_design(self, 
                      initial_instruction: str, 
                      files: List[str],
                      max_iterations: int = None) -> List[IterationResult]:
        """
        迭代设计/开发流程
        
        Args:
            initial_instruction: 初始指令
            files: 要处理的文件列表
            max_iterations: 最大迭代次数
        
        Returns:
            迭代结果列表
        """
        max_iter = max_iterations or self.config.iterations
        file_paths = [Path(f) for f in files]
        results = []
        
        print(f"🚀 开始迭代设计流程，共 {max_iter} 轮")
        print(f"📁 项目路径: {self.project_path}")
        print(f"📄 涉及文件: {[str(f) for f in file_paths]}")
        print(f"🔧 使用工具: {[t.value for t in self.config.tools]}")
        print("-" * 60)
        
        for i in range(max_iter):
            print(f"\n📍 第 {i+1} 轮迭代")
            
            for tool_type in self.config.tools:
                adapter = self.adapters.get(tool_type)
                if not adapter or not adapter.is_available():
                    print(f"⚠️  跳过工具: {tool_type.value} (不可用)")
                    continue
                
                print(f"🔧 使用工具: {tool_type.value}")
                
                instruction = initial_instruction
                if i > 0:
                    instruction = f"{initial_instruction}\n\n(迭代 {i+1}: 继续完善和优化)"
                
                result = adapter.execute(instruction, file_paths)
                results.append(result)
                
                if result.success:
                    print(f"✅ 成功! 变更文件: {result.changes}")
                    if result.commit_hash:
                        print(f"📝 Commit: {result.commit_hash}")
                else:
                    print(f"❌ 失败: {result.errors}")
            
            print("-" * 60)
        
        return results
    
    def run_workflow(self, workflow_path: str) -> Dict:
        """
        运行工作流文件
        
        Args:
            workflow_path: 工作流文件路径
            
        Returns:
            工作流执行结果
        """
        if not ORCHESTRATOR_AVAILABLE:
            print("❌ 任务编排模块不可用")
            return {"success": False, "error": "模块未导入"}
        
        print(f"🚀 运行工作流: {workflow_path}")
        
        orchestrator = TaskOrchestrator(str(self.project_path))
        result = orchestrator.run_workflow(Path(workflow_path))
        
        return result
    
    def list_workflows(self) -> List[Path]:
        """
        列出可用的工作流文件
        
        Returns:
            工作流文件路径列表
        """
        workflows = []
        workflow_dirs = [
            Path("."),
            Path("workflows"),
        ]
        
        for wf_dir in workflow_dirs:
            wf_path = self.project_path / wf_dir
            if wf_path.exists():
                for pattern in ["*.yaml", "*.yml", "*.json"]:
                    workflows.extend(wf_path.glob(pattern))
        
        return workflows
    
    def run_interactive(self):
        """交互式模式"""
        print("🎮 超级Coding工具 - 交互式模式")
        print("输入 'quit' 或 'exit' 退出")
        print("输入 'workflows' 查看可用工作流")
        print("输入 'run <workflow>' 运行工作流\n")
        
        while True:
            try:
                instruction = input(">>> ").strip()
                
                if instruction.lower() in ["quit", "exit"]:
                    print("👋 再见!")
                    break
                
                if not instruction:
                    continue
                
                # 查看工作流
                if instruction.lower() == "workflows":
                    print("\n📋 可用工作流:")
                    wfs = self.list_workflows()
                    if wfs:
                        for wf in wfs:
                            print(f"  - {wf.name}")
                    else:
                        print("  (无工作流文件)")
                    continue
                
                # 运行工作流
                if instruction.lower().startswith("run "):
                    wf_name = instruction[4:].strip()
                    wf_path = None
                    
                    # 查找工作流文件
                    for candidate in [wf_name, f"workflows/{wf_name}", f"{wf_name}.yaml", f"workflows/{wf_name}.yaml"]:
                        candidate_path = self.project_path / candidate
                        if candidate_path.exists():
                            wf_path = candidate_path
                            break
                    
                    if wf_path:
                        self.run_workflow(str(wf_path))
                    else:
                        print(f"❌ 找不到工作流: {wf_name}")
                    continue
                
                # 常规迭代开发
                print("\n📝 请输入要处理的文件（多个文件用空格分隔）:")
                files_input = input("文件: ").strip()
                files = [f.strip() for f in files_input.split()] if files_input else []
                
                if not files:
                    print("⚠️  未指定文件，跳过")
                    continue
                
                self.iterate_design(instruction, files)
                
            except KeyboardInterrupt:
                print("\n👋 再见!")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="超级Coding工具 - 支持多种AI工具的迭代开发平台"
    )
    parser.add_argument(
        "--path",
        default=".",
        help="项目路径 (默认: 当前目录)"
    )
    parser.add_argument(
        "--tools",
        nargs="+",
        help="使用的工具 (aider, claude, codex) (覆盖配置文件)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        help="最大迭代次数 (覆盖配置文件)"
    )
    parser.add_argument(
        "--no-auto-commit",
        action="store_true",
        help="禁用自动提交"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="详细输出"
    )
    parser.add_argument(
        "--instruction",
        "-i",
        help="直接执行指令（非交互式）"
    )
    parser.add_argument(
        "--files",
        nargs="+",
        help="要处理的文件（配合 --instruction 使用）"
    )
    parser.add_argument(
        "--config",
        help="配置文件路径 (默认: config.json)"
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="初始化配置文件"
    )
    parser.add_argument(
        "--workflow",
        "-w",
        help="运行工作流文件"
    )
    parser.add_argument(
        "--list-workflows",
        "-l",
        action="store_true",
        help="列出可用的工作流"
    )
    parser.add_argument(
        "--init-example",
        action="store_true",
        help="创建示例工作流文件（调用task_orchestrator）"
    )
    
    args = parser.parse_args()
    
    # 初始化示例工作流
    if args.init_example:
        if ORCHESTRATOR_AVAILABLE:
            import task_orchestrator
            task_orchestrator._create_example_workflow()
        else:
            print("❌ 任务编排模块不可用")
        return
    
    # 初始化配置文件
    if args.init_config:
        example_config = {
            "project": {
                "path": ".",
                "auto_commit": True,
                "iterations": 3,
                "verbose": False
            },
            "tools": {
                "aider": {
                    "enabled": True,
                    "model": "gpt-4",
                    "edit_format": "diff"
                },
                "claude": {
                    "enabled": False,
                    "model": "claude-3-sonnet-20240229"
                },
                "codex": {
                    "enabled": False,
                    "model": "gpt-4"
                }
            },
            "git": {
                "auto_push": False,
                "commit_prefix": "super-coder:"
            }
        }
        ConfigManager.save_config(example_config, Path("config.json"))
        print("✅ 配置文件已创建: config.json")
        return
    
    coder = SuperCoder(args.path, args.tools, args.config)
    
    # 从配置文件加载默认值，命令行参数覆盖
    project_cfg = coder.config_data.get("project", {})
    if args.iterations is not None:
        coder.config.iterations = args.iterations
    elif "iterations" in project_cfg:
        coder.config.iterations = project_cfg["iterations"]
    
    if args.no_auto_commit:
        coder.config.auto_commit = False
    elif "auto_commit" in project_cfg:
        coder.config.auto_commit = project_cfg["auto_commit"]
    
    if args.verbose:
        coder.config.verbose = True
    elif "verbose" in project_cfg:
        coder.config.verbose = project_cfg["verbose"]
    
    # 检查工具
    print("🔍 检查工具可用性...")
    availability = coder.check_tools()
    for tool, available in availability.items():
        status = "✅ 可用" if available else "❌ 不可用"
        print(f"  {tool.value}: {status}")
    
    # 列出工作流
    if args.list_workflows:
        print("\n📋 可用工作流:")
        wfs = coder.list_workflows()
        if wfs:
            for wf in wfs:
                print(f"  - {wf}")
        else:
            print("  (无工作流文件)")
        return
    
    # 运行工作流
    if args.workflow:
        coder.run_workflow(args.workflow)
        return
    
    # 直接执行或交互式
    if args.instruction and args.files:
        coder.iterate_design(args.instruction, args.files)
    else:
        coder.run_interactive()


if __name__ == "__main__":
    main()
