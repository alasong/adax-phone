#!/usr/bin/env python3
"""
业务流程编排系统 - 完整演示
结合了编排引擎 + 业务模板库
展示如何使用现成的业务方法论
"""

import yaml
import json
import sys
from business_templates import BusinessTemplateLibrary
from task_orchestrator import TaskExecutor, Workflow, TaskStatus

def print_separator(title):
    print("\n" + "=" * 70)
    print(f"📦 {title}")
    print("=" * 70)

def main():
    print("=" * 70)
    print("🚀 业务流程编排系统 - 完整演示")
    print("=" * 70)
    print("\n💡 本系统包含：")
    print("   1️⃣ 任务编排引擎（拓扑排序、并行执行、质量验证）")
    print("   2️⃣ 业务模板库（现成的软件工程方法论流程）")
    
    # 1. 列出可用模板
    print_separator("步骤 1: 查看可用的业务流程模板")
    templates = BusinessTemplateLibrary.get_templates()
    
    print("\n📋 可用的业务流程模板：")
    print("   ┌──────────────────────────────────────────────────────────┐")
    for i, (key, template) in enumerate(templates.items(), 1):
        print(f"   │ {i}. {key:30} {template['name']}")
    print("   └──────────────────────────────────────────────────────────┘")
    
    # 2. 选择一个模板（默认选 feature_development）
    selected_key = "feature_development"
    if len(sys.argv) > 1 and sys.argv[1] in templates:
        selected_key = sys.argv[1]
    
    selected_template = templates[selected_key]
    
    print_separator(f"步骤 2: 加载选定模板 - {selected_template['name']}")
    print(f"\n   说明：{selected_template['description']}")
    print(f"   任务数：{len(selected_template['tasks'])}")
    
    # 3. 显示任务流程
    print_separator("步骤 3: 查看业务流程的任务编排")
    
    print("\n📊 业务流程的依赖关系与执行顺序：")
    print("   ────────────────────────────────────────────────────────────")
    
    task_map = {t['id']: t for t in selected_template['tasks']}
    completed = set()
    layers = []
    
    while len(completed) < len(task_map):
        ready = []
        for task_id, task in task_map.items():
            if task_id not in completed:
                deps = task.get('depends_on', [])
                if all(dep in completed for dep in deps):
                    ready.append(task_id)
        layers.append(ready)
        completed.update(ready)
    
    for i, layer in enumerate(layers, 1):
        layer_str = "  ".join(task_map[t]['name'] for t in layer)
        parallel_mark = "⚡ (并行)" if len(layer) > 1 else ""
        print(f"   第 {i} 轮: {layer_str} {parallel_mark}")
    
    # 4. 展示业务方法论
    print_separator("步骤 4: 展示支撑的业务方法论")
    
    method_map = {
        "feature_development": "瀑布模型 + 敏捷开发最佳实践",
        "bug_fix": "RCA (根本原因分析) + 测试验证",
        "code_refactor": "Martin Fowler 重构方法论 + 测试保护网",
        "ci_cd": "现代 DevOps 最佳实践 + 持续集成/部署",
        "tdd": "Kent Beck 的 TDD 测试驱动开发（红-绿-重构）"
    }
    
    print(f"\n📚 业务方法论：{method_map[selected_key]}")
    
    # 5. 生成 YAML 配置文件
    print_separator("步骤 5: 生成可执行的工作流文件")
    
    output_file = f"workflows/{selected_key}.yaml"
    
    workflow_data = {
        "id": selected_template['id'],
        "name": selected_template['name'],
        "description": selected_template['description'],
        "version": "1.0",
        "author": "Super Coder",
        "max_parallel": 4,
        "variables": {"feature_name": "新功能", "target_file": "app.py"},
        "tasks": selected_template['tasks']
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(workflow_data, f, allow_unicode=True, sort_keys=False)
    
    print(f"\n✅ 工作流文件已生成：{output_file}")
    print("\n📝 你可以这样使用：")
    print(f"   python task_orchestrator.py {output_file}")
    print(f"\n💡 或者选择其他模板：")
    for key in templates.keys():
        if key != selected_key:
            print(f"   python {sys.argv[0]} {key}")
    
    print("\n" + "=" * 70)
    print("✅ 总结：现在你有了现成的业务流程模板！")
    print("=" * 70)
    print("""
  🔑 核心价值：
    1. 无需从零设计工作流
    2. 现成的软件工程最佳实践
    3. 可定制，可扩展
    4. 质量保证机制内置其中
""")

if __name__ == "__main__":
    main()

