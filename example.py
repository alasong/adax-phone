#!/usr/bin/env python3
"""
示例文件 - 用于测试超级Coding工具
"""

import math
from typing import Union

class Calculator:
    """功能完善的计算器类，支持基本运算、幂、模、平方根、阶乘、最大公约数、最小公倍数等。"""

    def __init__(self):
        self._memory: Union[int, float, None] = None

    # ---------- 基本运算 ----------
    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """加法"""
        return a + b

    def subtract(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """减法"""
        return a - b

    def multiply(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """乘法"""
        return a * b

    def divide(self, a: Union[int, float], b: Union[int, float]) -> float:
        """除法，除数为零时抛出 ValueError"""
        if b == 0:
            raise ValueError("除数不能为零")
        return a / b

    # ---------- 扩展运算 ----------
    def power(self, base: Union[int, float], exp: Union[int, float]) -> Union[int, float]:
        """幂运算"""
        return base ** exp

    def modulo(self, a: int, b: int) -> int:
        """取模运算"""
        if b == 0:
            raise ValueError("模数不能为零")
        return a % b

    def sqrt(self, x: Union[int, float]) -> float:
        """平方根，负数时抛出 ValueError"""
        if x < 0:
            raise ValueError("不能对负数开平方")
        return math.sqrt(x)

    def factorial(self, n: int) -> int:
        """阶乘，非负整数"""
        if n < 0:
            raise ValueError("阶乘要求非负整数")
        return math.factorial(n)

    def gcd(self, a: int, b: int) -> int:
        """最大公约数"""
        return math.gcd(a, b)

    def lcm(self, a: int, b: int) -> int:
        """最小公倍数"""
        if a == 0 or b == 0:
            return 0
        return abs(a * b) // math.gcd(a, b)

    # ---------- 奇偶判断 ----------
    def is_even(self, n: int) -> bool:
        """判断是否为偶数"""
        return n % 2 == 0

    def is_odd(self, n: int) -> bool:
        """判断是否为奇数"""
        return n % 2 != 0

    # ---------- 内存功能 ----------
    def memory_store(self, value: Union[int, float]) -> None:
        """将值存入内存"""
        self._memory = value

    def memory_recall(self) -> Union[int, float, None]:
        """返回内存中的值，若无则返回 None"""
        return self._memory

    def memory_clear(self) -> None:
        """清除内存"""
        self._memory = None

    # ---------- 字符串表示 ----------
    def __repr__(self) -> str:
        return f"Calculator(memory={self._memory})"

    def __str__(self) -> str:
        return f"Calculator with memory: {self._memory}"


def main():
    calc = Calculator()
    print("计算器示例（增强版）:")
    print(f"5 + 3 = {calc.add(5, 3)}")
    print(f"10 - 4 = {calc.subtract(10, 4)}")
    print(f"6 * 7 = {calc.multiply(6, 7)}")
    print(f"20 / 4 = {calc.divide(20, 4)}")
    print(f"2 ** 10 = {calc.power(2, 10)}")
    print(f"17 % 5 = {calc.modulo(17, 5)}")
    print(f"√144 = {calc.sqrt(144)}")
    print(f"5! = {calc.factorial(5)}")
    print(f"gcd(12, 18) = {calc.gcd(12, 18)}")
    print(f"lcm(12, 18) = {calc.lcm(12, 18)}")
    print(f"7 is even? {calc.is_even(7)}")
    print(f"7 is odd? {calc.is_odd(7)}")

    calc.memory_store(42)
    print(f"Memory stored: {calc.memory_recall()}")
    calc.memory_clear()
    print(f"Memory after clear: {calc.memory_recall()}")


if __name__ == "__main__":
    main()
