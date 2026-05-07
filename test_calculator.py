#!/usr/bin/env python3
"""简单的计算器类 - 用于测试AI辅助编码"""

class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
    
    def multiply(self, a, b):
        return a * b
    
    def divide(self, a, b):
        if b == 0:
            raise ZeroDivisionError("除数不能为零")
        return a / b
