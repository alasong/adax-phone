.PHONY: help install install-dev test lint format clean run-demo

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装依赖
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

install-dev: ## 安装开发依赖
	.venv/bin/pip install -e ".[dev]"

test: ## 运行测试
	.venv/bin/python validation_test.py
	.venv/bin/python workflow_testing_framework.py

test-core: ## 运行核心引擎演示
	.venv/bin/python core_orchestration_engine.py

lint: ## 代码检查
	.venv/bin/python -m py_compile super_coder.py
	.venv/bin/python -m py_compile task_orchestrator.py
	.venv/bin/python -m py_compile core_orchestration_engine.py

format: ## 格式化代码
	.venv/bin/python -m black .

format-check: ## 检查代码格式
	.venv/bin/python -m black --check .

clean: ## 清理临时文件
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf logs/
	rm -rf history/
	rm -f .workflow_*_state.json
	rm -f workflow_*_result.json
	rm -f core_demo.yaml

run-demo: ## 运行完整演示
	@echo "=== 1. 核心引擎演示 ==="
	.venv/bin/python core_orchestration_engine.py
	@echo ""
	@echo "=== 2. 工作流测试演示 ==="
	.venv/bin/python workflow_testing_framework.py
	@echo ""
	@echo "=== 3. 业务模板演示 ==="
	.venv/bin/python demo_business_orchestration.py feature_development

run-workflow: ## 运行示例工作流
	.venv/bin/python task_orchestrator.py workflows/feature_development.yaml

list-workflows: ## 列出可用工作流
	.venv/bin/python super_coder.py --list-workflows
