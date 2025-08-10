# calculator.py

from fastmcp import FastMCP

mcp = FastMCP("Calculator-MCP")

@mcp.tool(name="add", description="Add two numbers and return the sum.")
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool(name="sub", description="Subtract the second number from the first.")
def sub(a: int, b: int) -> int:
    """Subtract two numbers"""
    return a - b

@mcp.tool(name="mul", description="Multiply two numbers and return the product.")
def mul(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

@mcp.tool(name="div", description="Divide two numbers (floating point division).")
def div(a: int, b: int) -> float:
    """Divide two numbers (returns floating point division result)"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

if __name__ == "__main__":
    mcp.run()
