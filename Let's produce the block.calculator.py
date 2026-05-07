class Calculator:
    """A simple calculator supporting basic arithmetic operations."""

    def add(self, a: float, b: float) -> float:
        """Return a + b."""
        return a + b

    def subtract(self, a: float, b: float) -> float:
        """Return a - b."""
        return a - b

    def multiply(self, a: float, b: float) -> float:
        """Return a * b."""
        return a * b

    def divide(self, a: float, b: float) -> float:
        """Return a / b. Raises ValueError if b is zero."""
        if b == 0:
            raise ValueError("除数不能为零")
        return a / b


if __name__ == "__main__":
    calc = Calculator()
    print("add(3,5) =", calc.add(3, 5))
    print("subtract(10,4) =", calc.subtract(10, 4))
    print("multiply(2,3) =", calc.multiply(2, 3))
    print("divide(9,3) =", calc.divide(9, 3))
    try:
        calc.divide(1, 0)
    except ValueError as e:
        print("divide(1,0) raised ValueError:", e)
