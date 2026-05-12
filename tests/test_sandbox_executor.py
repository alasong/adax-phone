#!/usr/bin/env python3
"""沙箱执行验证 - 测试 AI 生成的代码能否真正运行"""

import pytest
import tempfile
import os
from pathlib import Path


class TestSandboxExecutor:
    """测试沙箱执行器"""

    def test_execute_valid_python_code(self):
        """执行正确的 Python 代码"""
        from sandbox_executor import SandboxExecutor
        executor = SandboxExecutor()
        
        code = """
def add(a, b):
    return a + b

result = add(2, 3)
print(result)
"""
        result = executor.execute(code, language="python")
        assert result.success is True
        assert "5" in result.stdout

    def test_execute_code_with_syntax_error(self):
        """执行有语法错误的代码"""
        from sandbox_executor import SandboxExecutor
        executor = SandboxExecutor()
        
        code = "def broken("
        result = executor.execute(code, language="python")
        assert result.success is False
        assert "SyntaxError" in result.error_type or result.returncode != 0

    def test_execute_code_with_runtime_error(self):
        """执行有运行时错误的代码"""
        from sandbox_executor import SandboxExecutor
        executor = SandboxExecutor()
        
        code = "x = 1 / 0"
        result = executor.execute(code, language="python")
        assert result.success is False
        assert "ZeroDivisionError" in result.error_type

    def test_execute_code_with_timeout(self):
        """执行超时"""
        from sandbox_executor import SandboxExecutor
        executor = SandboxExecutor(timeout=2)
        
        code = "import time; time.sleep(10)"
        result = executor.execute(code, language="python")
        assert result.success is False
        assert result.timed_out is True

    def test_execute_code_with_import_restriction(self):
        """执行受限导入"""
        from sandbox_executor import SandboxExecutor
        executor = SandboxExecutor(
            allowed_imports=["math", "json"],
            blocked_imports=["os", "subprocess", "sys"]
        )
        
        code = "import os; os.system('echo hacked')"
        result = executor.execute(code, language="python")
        assert result.success is False
        assert "security" in result.error_type.lower() or "violation" in result.error_type.lower()

    def test_execute_code_with_file_write_restriction(self):
        """执行文件写入限制"""
        from sandbox_executor import SandboxExecutor
        executor = SandboxExecutor(allow_file_write=False)
        
        code = "open('/tmp/test_sandbox.txt', 'w').write('hacked')"
        result = executor.execute(code, language="python")
        # 应该被阻止或限制
        assert result.success is False or not os.path.exists('/tmp/test_sandbox.txt')

    def test_execute_with_test_framework(self):
        """执行带单元测试的代码"""
        from sandbox_executor import SandboxExecutor
        executor = SandboxExecutor()
        
        code = """
import unittest

def add(a, b):
    return a + b

class TestAdd(unittest.TestCase):
    def test_add_positive(self):
        self.assertEqual(add(2, 3), 5)
    
    def test_add_negative(self):
        self.assertEqual(add(-1, -1), -2)

if __name__ == '__main__':
    unittest.main()
"""
        result = executor.execute_with_tests(code, test_class="TestAdd")
        assert result.success is True
        assert result.tests_passed == 2

    def test_execute_with_test_failure(self):
        """执行失败的单元测试"""
        from sandbox_executor import SandboxExecutor
        executor = SandboxExecutor()
        
        code = """
import unittest

def add(a, b):
    return a - b  # 故意写错

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

if __name__ == '__main__':
    unittest.main()
"""
        result = executor.execute_with_tests(code, test_class="TestAdd")
        assert result.success is False
        assert result.tests_failed > 0

    def test_execute_with_coverage(self):
        """执行并收集覆盖率"""
        from sandbox_executor import SandboxExecutor
        executor = SandboxExecutor()
        
        code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

result = add(1, 2)
result = subtract(5, 3)
"""
        result = executor.execute_with_coverage(code)
        assert result.success is True
        assert result.coverage is not None


class TestCodeVerifier:
    """测试代码验证器（规则 + 沙箱 + Critic 三重验证）"""

    def test_verify_valid_code(self):
        """验证正确的代码"""
        from sandbox_executor import CodeVerifier
        verifier = CodeVerifier()
        
        code = """
def add(a, b):
    '''Add two numbers.'''
    return a + b
"""
        result = verifier.verify(
            code=code,
            task_description="创建一个加法函数",
        )
        assert result.overall_passed is True

    def test_verify_code_with_syntax_error(self):
        """验证有语法错误的代码"""
        from sandbox_executor import CodeVerifier
        verifier = CodeVerifier()
        
        code = "def broken("
        result = verifier.verify(
            code=code,
            task_description="创建一个函数",
        )
        assert result.overall_passed is False
        assert result.sandbox_result is not None
        assert result.sandbox_result.success is False

    def test_verify_code_with_style_issues(self):
        """验证有风格问题的代码"""
        from sandbox_executor import CodeVerifier
        verifier = CodeVerifier()
        
        code = "def add(a,b):return a+b"
        result = verifier.verify(
            code=code,
            task_description="创建加法函数",
            check_style=True,
        )
        # 风格问题不应阻止通过，但应记录
        assert result.style_issues is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
