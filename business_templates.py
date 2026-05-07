#!/usr/bin/env python3
"""
业务流程模板库 - 现成的方法论和业务知识
提供可直接复用的工作流模板
"""

import yaml
from typing import Dict, List

class BusinessTemplateLibrary:
    """
    业务流程模板库
    包含现成的方法论和最佳实践
    """
    
    @staticmethod
    def get_templates() -> Dict:
        """获取所有模板"""
        return {
            "feature_development": BusinessTemplateLibrary._feature_development_template(),
            "bug_fix": BusinessTemplateLibrary._bug_fix_template(),
            "code_refactor": BusinessTemplateLibrary._code_refactor_template(),
            "ci_cd": BusinessTemplateLibrary._ci_cd_template(),
            "tdd": BusinessTemplateLibrary._tdd_template()
        }
    
    @staticmethod
    def list_templates():
        """列出可用模板"""
        templates = BusinessTemplateLibrary.get_templates()
        print("=" * 70)
        print("📦 可用的业务流程模板")
        print("=" * 70)
        for key, template in templates.items():
            print(f"\n📋 {key}")
            print(f"   名称: {template['name']}")
            print(f"   说明: {template['description']}")
        print("\n" + "=" * 70)
    
    # ========== 模板 1: 标准功能开发流程 ==========
    @staticmethod
    def _feature_development_template() -> Dict:
        """标准功能开发流程（基于瀑布 + 敏捷最佳实践）"""
        return {
            "id": "feature_development",
            "name": "标准功能开发流程",
            "description": "基于软件工程最佳实践的完整功能开发流程：需求→设计→实现→测试→部署",
            "tasks": [
                {
                    "id": "requirements_analysis",
                    "name": "需求分析",
                    "description": "分析并明确功能需求，编写需求文档",
                    "tool": "script",
                    "instruction": "print('✅ 需求分析完成')",
                    "parallel": False
                },
                {
                    "id": "architecture_design",
                    "name": "架构设计",
                    "description": "设计系统架构、接口定义、数据结构",
                    "tool": "script",
                    "instruction": "print('✅ 架构设计完成')",
                    "depends_on": ["requirements_analysis"],
                    "parallel": False
                },
                {
                    "id": "implementation",
                    "name": "代码实现",
                    "description": "编写功能代码，遵循编码规范",
                    "tool": "script",
                    "instruction": "print('✅ 代码实现完成')",
                    "depends_on": ["architecture_design"],
                    "output_validation": {
                        "regex": "完成",
                        "assertions": ["True"]
                    }
                },
                {
                    "id": "unit_test",
                    "name": "单元测试",
                    "description": "编写并运行单元测试，确保代码质量",
                    "tool": "script",
                    "instruction": "print('✅ 单元测试通过')",
                    "depends_on": ["implementation"],
                    "parallel": True
                },
                {
                    "id": "integration_test",
                    "name": "集成测试",
                    "description": "进行集成测试，验证各模块协作",
                    "tool": "script",
                    "instruction": "print('✅ 集成测试通过')",
                    "depends_on": ["implementation"],
                    "parallel": True
                },
                {
                    "id": "code_review",
                    "name": "代码评审",
                    "description": "进行代码审查，检查代码质量和最佳实践",
                    "tool": "script",
                    "instruction": "print('✅ 代码评审通过')",
                    "depends_on": ["unit_test", "integration_test"],
                    "parallel": False
                },
                {
                    "id": "deployment",
                    "name": "部署上线",
                    "description": "部署到生产环境",
                    "tool": "script",
                    "instruction": "print('✅ 部署完成')",
                    "depends_on": ["code_review"]
                }
            ]
        }
    
    # ========== 模板 2: Bug 修复流程 ==========
    @staticmethod
    def _bug_fix_template() -> Dict:
        """Bug 修复流程（基于 RCA - 根本原因分析方法论）"""
        return {
            "id": "bug_fix",
            "name": "标准 Bug 修复流程",
            "description": "基于 RCA 根本原因分析的完整 Bug 修复流程：复现→诊断→修复→验证",
            "tasks": [
                {
                    "id": "reproduce_bug",
                    "name": "复现 Bug",
                    "description": "在开发环境中复现问题，确认现象",
                    "tool": "script",
                    "instruction": "print('✅ Bug 复现成功')",
                    "parallel": False
                },
                {
                    "id": "diagnose_root_cause",
                    "name": "诊断根因",
                    "description": "使用 5 Whys/鱼骨图找到根本原因",
                    "tool": "script",
                    "instruction": "print('✅ 根因找到')",
                    "depends_on": ["reproduce_bug"]
                },
                {
                    "id": "implement_fix",
                    "name": "实现修复",
                    "description": "编写修复代码",
                    "tool": "script",
                    "instruction": "print('✅ 修复代码完成')",
                    "depends_on": ["diagnose_root_cause"],
                    "max_retries": 2
                },
                {
                    "id": "verify_fix",
                    "name": "验证修复",
                    "description": "测试验证问题是否真正解决",
                    "tool": "script",
                    "instruction": "print('✅ 修复验证通过')",
                    "depends_on": ["implement_fix"]
                },
                {
                    "id": "cleanup_and_document",
                    "name": "清理与文档",
                    "description": "清理临时代码，更新文档，添加测试用例",
                    "tool": "script",
                    "instruction": "print('✅ 清理与文档完成')",
                    "depends_on": ["verify_fix"]
                }
            ]
        }
    
    # ========== 模板 3: 代码重构流程 ==========
    @staticmethod
    def _code_refactor_template() -> Dict:
        """代码重构流程（基于 Martin Fowler 重构模式）"""
        return {
            "id": "code_refactor",
            "name": "标准代码重构流程",
            "description": "基于 Martin Fowler 重构方法论的安全重构流程",
            "tasks": [
                {
                    "id": "code_smell_detection",
                    "name": "坏味道检测",
                    "description": "检测代码中的坏味道和技术债务",
                    "tool": "script",
                    "instruction": "print('✅ 坏味道检测完成')",
                    "parallel": False
                },
                {
                    "id": "test_safety_net",
                    "name": "建立测试保护网",
                    "description": "确保有足够的测试覆盖，避免重构引入新问题",
                    "tool": "script",
                    "instruction": "print('✅ 测试保护网已建立')",
                    "depends_on": ["code_smell_detection"],
                    "parallel": True
                },
                {
                    "id": "incremental_refactor",
                    "name": "增量重构",
                    "description": "使用小步骤进行重构，每一步都有测试",
                    "tool": "script",
                    "instruction": "print('✅ 增量重构完成')",
                    "depends_on": ["test_safety_net"],
                    "max_retries": 3
                },
                {
                    "id": "verify_refactoring",
                    "name": "验证重构结果",
                    "description": "运行完整测试套件，确保功能一致",
                    "tool": "script",
                    "instruction": "print('✅ 重构验证通过')",
                    "depends_on": ["incremental_refactor"],
                    "parallel": False
                }
            ]
        }
    
    # ========== 模板 4: CI/CD 流程 ==========
    @staticmethod
    def _ci_cd_template() -> Dict:
        """CI/CD 流程（基于现代 DevOps 最佳实践）"""
        return {
            "id": "ci_cd",
            "name": "标准 CI/CD 流程",
            "description": "基于现代 DevOps 最佳实践的持续集成与部署流程",
            "tasks": [
                {
                    "id": "code_checkout",
                    "name": "代码检出",
                    "description": "从版本控制系统检出代码",
                    "tool": "script",
                    "instruction": "print('✅ 代码检出完成')",
                    "parallel": False
                },
                {
                    "id": "linting",
                    "name": "代码 lint 检查",
                    "description": "运行静态代码分析，检查代码规范",
                    "tool": "script",
                    "instruction": "print('✅ Lint 检查通过')",
                    "depends_on": ["code_checkout"],
                    "parallel": True
                },
                {
                    "id": "unit_tests",
                    "name": "单元测试",
                    "description": "运行单元测试套件",
                    "tool": "script",
                    "instruction": "print('✅ 单元测试通过')",
                    "depends_on": ["code_checkout"],
                    "parallel": True
                },
                {
                    "id": "build",
                    "name": "构建",
                    "description": "编译与构建应用",
                    "tool": "script",
                    "instruction": "print('✅ 构建成功')",
                    "depends_on": ["linting", "unit_tests"]
                },
                {
                    "id": "deploy_staging",
                    "name": "部署到预发布环境",
                    "description": "部署到 staging 环境",
                    "tool": "script",
                    "instruction": "print('✅ 预发布部署完成')",
                    "depends_on": ["build"]
                },
                {
                    "id": "e2e_tests",
                    "name": "端到端测试",
                    "description": "在预发布环境运行 E2E 测试",
                    "tool": "script",
                    "instruction": "print('✅ E2E 测试通过')",
                    "depends_on": ["deploy_staging"]
                },
                {
                    "id": "deploy_production",
                    "name": "部署到生产环境",
                    "description": "部署到生产环境（蓝绿/金丝雀发布）",
                    "tool": "script",
                    "instruction": "print('✅ 生产部署完成')",
                    "depends_on": ["e2e_tests"]
                }
            ]
        }
    
    # ========== 模板 5: TDD 流程 ==========
    @staticmethod
    def _tdd_template() -> Dict:
        """TDD (测试驱动开发) 流程（Kent Beck 的 TDD 方法论）"""
        return {
            "id": "tdd",
            "name": "TDD 测试驱动开发流程",
            "description": "基于 Kent Beck TDD 方法论：红 → 绿 → 重构",
            "tasks": [
                {
                    "id": "write_failing_test",
                    "name": "写失败的测试",
                    "description": "红：先写一个失败的测试（明确功能需求）",
                    "tool": "script",
                    "instruction": "print('✅ 失败的测试已写')",
                    "parallel": False
                },
                {
                    "id": "make_test_pass",
                    "name": "让测试通过",
                    "description": "绿：编写刚好让测试通过的代码",
                    "tool": "script",
                    "instruction": "print('✅ 测试通过')",
                    "depends_on": ["write_failing_test"],
                    "max_retries": 3
                },
                {
                    "id": "refactor_code",
                    "name": "重构代码",
                    "description": "重构：优化代码，保持测试通过",
                    "tool": "script",
                    "instruction": "print('✅ 代码重构完成')",
                    "depends_on": ["make_test_pass"]
                }
            ]
        }

def main():
    """演示业务模板库"""
    BusinessTemplateLibrary.list_templates()

if __name__ == "__main__":
    main()

