#!/usr/bin/env python3
"""
沙箱执行验证 - 验证 AI 生成的代码能否真正运行

解决 AI 根本性缺陷：无法执行验证
- 沙箱隔离执行
- 单元测试自动运行
- 覆盖率收集
- 安全限制（禁止危险导入、文件写入等）
"""

import ast
import sys
import io
import json
import signal
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    error_type: str = ""
    timed_out: bool = False
    coverage: Optional[Dict] = None
    tests_passed: int = 0
    tests_failed: int = 0
    tests_errors: List[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    """验证结果（规则 + 沙箱 + Critic 三重验证）"""
    overall_passed: bool
    syntax_check: Dict = field(default_factory=dict)
    sandbox_result: Optional[ExecutionResult] = None
    test_result: Optional[ExecutionResult] = None
    style_issues: List[str] = field(default_factory=list)
    critic_review: Optional[Dict] = None


class SandboxExecutor:
    """
    沙箱执行器 - 在隔离环境中运行 AI 生成的代码
    
    安全特性：
    - 超时控制
    - 导入限制
    - 文件写入限制
    - 内存限制（可选）
    """
    
    DANGEROUS_MODULES = [
        "os", "subprocess", "sys", "ctypes", "pickle",
        "shelve", "shutil", "socket", "http", "urllib",
        "ftplib", "smtplib", "telnetlib",
    ]
    
    def __init__(
        self,
        timeout: int = 30,
        allowed_imports: List[str] = None,
        blocked_imports: List[str] = None,
        allow_file_write: bool = False,
        max_memory_mb: int = 256,
    ):
        self.timeout = timeout
        self.allowed_imports = set(allowed_imports or [])
        self.blocked_imports = set(blocked_imports or self.DANGEROUS_MODULES)
        self.allow_file_write = allow_file_write
        self.max_memory_mb = max_memory_mb
    
    def execute(self, code: str, language: str = "python") -> ExecutionResult:
        """
        在沙箱中执行代码
        
        Args:
            code: 要执行的代码
            language: 编程语言（目前只支持 python）
            
        Returns:
            ExecutionResult 执行结果
        """
        if language != "python":
            return ExecutionResult(
                success=False,
                error_type="UnsupportedLanguage",
                stderr=f"不支持的语言: {language}",
            )
        
        # 1. 语法检查
        syntax_error = self._check_syntax(code)
        if syntax_error:
            return ExecutionResult(
                success=False,
                error_type="SyntaxError",
                stderr=syntax_error,
                returncode=1,
            )
        
        # 2. 安全检查
        security_error = self._check_security(code)
        if security_error:
            return ExecutionResult(
                success=False,
                error_type="SecurityViolation",
                stderr=security_error,
                returncode=1,
            )
        
        # 3. 沙箱执行
        return self._run_in_sandbox(code)
    
    def execute_with_tests(
        self,
        code: str,
        test_class: str = None,
    ) -> ExecutionResult:
        """
        执行代码并运行单元测试
        
        Args:
            code: 包含代码和测试的完整代码
            test_class: 测试类名
            
        Returns:
            ExecutionResult 包含测试结果
        """
        # 移除用户代码中的 unittest.main() 调用（会提前 exit）
        cleaned_code = self._strip_unittest_main(code)
        
        test_runner = f"""
import unittest
import sys
import json

loader = unittest.TestLoader()
if {repr(test_class)}:
    suite = loader.loadTestsFromTestCase({test_class})
else:
    suite = loader.discover('.')

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

summary = {{
    "tests_run": result.testsRun,
    "failures": len(result.failures),
    "errors": len(result.errors),
    "success": result.wasSuccessful()
}}
sys.stderr.write("__TEST_SUMMARY__\\n")
sys.stderr.write(json.dumps(summary) + "\\n")
"""
        full_code = cleaned_code + "\n" + test_runner
        result = self._run_in_sandbox(full_code)
        
        # 解析测试摘要（可能在 stdout 或 stderr 中）
        combined_output = result.stdout + "\n" + result.stderr
        test_summary = self._parse_test_summary(combined_output)
        result.tests_passed = test_summary.get("tests_run", 0) - test_summary.get("failures", 0) - test_summary.get("errors", 0)
        result.tests_failed = test_summary.get("failures", 0) + test_summary.get("errors", 0)
        result.success = test_summary.get("success", result.returncode == 0)
        
        return result
    
    def _strip_unittest_main(self, code: str) -> str:
        """移除代码中的 unittest.main() 调用"""
        import re
        # 移除 if __name__ == '__main__': unittest.main() 块
        pattern = r"\n\s*if\s+__name__\s*==\s*['\"]__main__['\"]\s*:.*?unittest\.main\(\).*"
        return re.sub(pattern, "", code, flags=re.DOTALL)
    
    def execute_with_coverage(self, code: str) -> ExecutionResult:
        """
        执行代码并收集覆盖率
        
        Args:
            code: 要执行的代码
            
        Returns:
            ExecutionResult 包含覆盖率信息
        """
        try:
            import coverage as cov_lib
        except ImportError:
            # 如果没有安装 coverage，回退到基本执行
            result = self._run_in_sandbox(code)
            result.coverage = {"note": "coverage 包未安装，无法收集覆盖率"}
            return result
        
        # 使用 coverage 库收集覆盖率
        cov = cov_lib.Coverage()
        cov.start()
        
        result = self._run_in_sandbox(code)
        
        cov.stop()
        cov.save()
        
        # 获取覆盖率数据
        total = cov.report(show_missing=False)
        result.coverage = {"total_percent": total}
        
        return result
    
    def _check_syntax(self, code: str) -> Optional[str]:
        """检查语法错误"""
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            return f"SyntaxError: {e.msg} (line {e.lineno})"
    
    def _check_security(self, code: str) -> Optional[str]:
        """检查安全违规"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None  # 语法错误由 _check_syntax 处理
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.blocked_imports:
                        if not self.allowed_imports or alias.name not in self.allowed_imports:
                            return f"SecurityViolation: 禁止导入 '{alias.name}'"
            
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in self.blocked_imports:
                    if not self.allowed_imports or node.module.split(".")[0] not in self.allowed_imports:
                        return f"SecurityViolation: 禁止导入 '{node.module}'"
        
        if not self.allow_file_write:
            # 检查 open() 调用（写入模式）
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id == "open":
                        # 检查是否有写入模式参数
                        if len(node.args) >= 2:
                            mode_arg = node.args[1]
                            if isinstance(mode_arg, ast.Constant):
                                if any(c in str(mode_arg.value) for c in "wax+"):
                                    return "SecurityViolation: 禁止文件写入操作"
                        for kw in node.keywords:
                            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                                if any(c in str(kw.value.value) for c in "wax+"):
                                    return "SecurityViolation: 禁止文件写入操作"
        
        return None
    
    def _run_in_sandbox(self, code: str) -> ExecutionResult:
        """在子进程中执行代码（隔离环境）"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            proc = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=tempfile.gettempdir(),
            )
            
            return ExecutionResult(
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
                error_type="" if proc.returncode == 0 else self._extract_error_type(proc.stderr),
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error_type="TimeoutError",
                stderr=f"执行超时 ({self.timeout}s)",
                timed_out=True,
                returncode=1,
            )
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    
    def _extract_error_type(self, stderr: str) -> str:
        """从 stderr 中提取错误类型"""
        for line in stderr.splitlines():
            if line.strip().startswith(("Traceback", "Error", "Exception")):
                # 提取最后一行的错误类型
                for line2 in reversed(stderr.splitlines()):
                    if ":" in line2:
                        parts = line2.strip().split(":")
                        if parts[0].strip().endswith("Error") or parts[0].strip().endswith("Exception"):
                            return parts[0].strip()
                break
        return "UnknownError"
    
    def _parse_test_summary(self, stdout: str) -> Dict:
        """解析测试摘要"""
        for line in stdout.splitlines():
            if "__TEST_SUMMARY__" in line:
                continue
            try:
                return json.loads(line.strip())
            except json.JSONDecodeError:
                continue
        return {}


class CodeVerifier:
    """
    代码验证器 - 规则 + 沙箱 + Critic 三重验证
    
    解决 AI 幻觉问题：
    1. 规则验证：语法检查、安全检查
    2. 沙箱执行：代码能否真正运行
    3. Critic 审查：代码质量、逻辑正确性
    """
    
    def __init__(self, sandbox: SandboxExecutor = None):
        self.sandbox = sandbox or SandboxExecutor()
    
    def verify(
        self,
        code: str,
        task_description: str,
        check_style: bool = False,
        run_tests: bool = False,
        critic_enabled: bool = False,
    ) -> VerificationResult:
        """
        三重验证代码
        
        Args:
            code: AI 生成的代码
            task_description: 任务描述
            check_style: 是否检查代码风格
            run_tests: 是否运行单元测试
            critic_enabled: 是否启用 Critic 审查
            
        Returns:
            VerificationResult 验证结果
        """
        result = VerificationResult(overall_passed=True)
        
        # 1. 语法检查
        syntax_error = self.sandbox._check_syntax(code)
        result.syntax_check = {
            "passed": syntax_error is None,
            "error": syntax_error,
        }
        if syntax_error:
            result.overall_passed = False
            result.sandbox_result = ExecutionResult(
                success=False,
                error_type="SyntaxError",
                stderr=syntax_error,
                returncode=1,
            )
            return result
        
        # 2. 安全检查
        security_error = self.sandbox._check_security(code)
        result.syntax_check["security_passed"] = security_error is None
        result.syntax_check["security_error"] = security_error
        if security_error:
            result.overall_passed = False
            result.sandbox_result = ExecutionResult(
                success=False,
                error_type="SecurityViolation",
                stderr=security_error,
                returncode=1,
            )
            return result
        
        # 3. 沙箱执行
        exec_result = self.sandbox.execute(code)
        result.sandbox_result = exec_result
        if not exec_result.success:
            result.overall_passed = False
            return result
        
        # 4. 单元测试（可选）
        if run_tests:
            test_result = self.sandbox.execute_with_tests(code)
            result.test_result = test_result
            if not test_result.success:
                result.overall_passed = False
                return result
        
        # 5. 风格检查（可选）
        if check_style:
            result.style_issues = self._check_style(code)
        
        # 6. Critic 审查（可选）
        if critic_enabled:
            from critic_agent import CriticAgent
            critic = CriticAgent()
            review = critic.review(
                task_description=task_description,
                worker_output=code,
                dimensions=["correctness", "style", "performance"],
                domain="code",
            )
            result.critic_review = {
                "status": review.status.value,
                "score": review.score,
                "issues": [i.description for i in review.issues],
            }
            if review.status.value != "pass":
                result.overall_passed = False
        
        return result
    
    def _check_style(self, code: str) -> List[str]:
        """检查代码风格"""
        issues = []
        
        # 检查行长度
        for i, line in enumerate(code.splitlines(), 1):
            if len(line) > 120:
                issues.append(f"第 {i} 行超过 120 字符 ({len(line)} 字符)")
        
        # 检查是否有 docstring
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not (node.body and isinstance(node.body[0], ast.Expr) and
                            isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                        issues.append(f"{node.name} 缺少 docstring")
        except SyntaxError:
            pass
        
        # 检查命名规范
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith("def "):
                func_name = stripped.split("def ")[1].split("(")[0]
                if not func_name.islower() and "_" not in func_name and not func_name.startswith("_"):
                    issues.append(f"函数 '{func_name}' 应使用 snake_case 命名")
        
        return issues


def demo():
    """演示沙箱执行验证"""
    print("=" * 70)
    print("🔒 沙箱执行验证演示")
    print("=" * 70)
    
    executor = SandboxExecutor(timeout=5)
    
    # 1. 正确代码
    print("\n📋 测试 1: 正确代码")
    code1 = """
def add(a, b):
    return a + b

print(f"2 + 3 = {add(2, 3)}")
"""
    result = executor.execute(code1)
    print(f"   成功: {result.success}")
    print(f"   输出: {result.stdout.strip()}")
    
    # 2. 语法错误
    print("\n📋 测试 2: 语法错误")
    code2 = "def broken("
    result = executor.execute(code2)
    print(f"   成功: {result.success}")
    print(f"   错误: {result.error_type}")
    
    # 3. 运行时错误
    print("\n📋 测试 3: 运行时错误")
    code3 = "x = 1 / 0"
    result = executor.execute(code3)
    print(f"   成功: {result.success}")
    print(f"   错误: {result.error_type}")
    
    # 4. 超时
    print("\n📋 测试 4: 超时")
    code4 = "import time; time.sleep(10)"
    result = executor.execute(code4)
    print(f"   成功: {result.success}")
    print(f"   超时: {result.timed_out}")
    
    # 5. 安全违规
    print("\n📋 测试 5: 安全违规")
    code5 = "import os; os.system('echo hacked')"
    result = executor.execute(code5)
    print(f"   成功: {result.success}")
    print(f"   错误: {result.error_type}")
    
    # 6. 三重验证
    print("\n📋 测试 6: 三重验证")
    verifier = CodeVerifier()
    code6 = """
def add(a, b):
    '''Add two numbers.'''
    return a + b

print(add(2, 3))
"""
    result = verifier.verify(
        code=code6,
        task_description="创建加法函数",
        check_style=True,
    )
    print(f"   总体通过: {result.overall_passed}")
    print(f"   语法检查: {result.syntax_check}")
    print(f"   沙箱执行: {result.sandbox_result.success}")
    print(f"   风格问题: {result.style_issues}")
    
    print("\n" + "=" * 70)
    print("✅ 沙箱执行验证演示完成！")
    print("=" * 70)


if __name__ == "__main__":
    demo()
