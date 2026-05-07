#!/usr/bin/env python3
"""
示例文件 - 用于测试超级Coding工具
"""

class Calculator:
    """简单的计算器类"""
    
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
    
    def multiply(self, a, b):
        return a * b
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("除数不能为零")
        return a / b


def main():
    calc = Calculator()
    print("计算器示例:")
    print(f"5 + 3 = {calc.add(5, 3)}")
    print(f"10 - 4 = {calc.subtract(10, 4)}")
    print(f"6 * 7 = {calc.multiply(6, 7)}")
    print(f"20 / 4 = {calc.divide(20, 4)}")


if __name__ == "__main__":
    main()
