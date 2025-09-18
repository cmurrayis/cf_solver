"""JavaScript challenge solver for Cloudflare challenges.

Solves JavaScript-based challenges by parsing and executing the challenge
code in a safe sandbox environment.
"""

import re
import ast
import math
import time
import random
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin
import base64
from py_mini_racer import MiniRacer


@dataclass
class ChallengeSolution:
    """Solution to a JavaScript challenge."""
    jschl_answer: str
    jschl_vc: str
    pass_value: Optional[str] = None
    s_value: Optional[str] = None
    submit_url: str = ""
    form_data: Dict[str, str] = None

    def __post_init__(self):
        if self.form_data is None:
            self.form_data = {}

    def to_form_data(self) -> Dict[str, str]:
        """Convert solution to form data."""
        data = {
            "jschl_answer": self.jschl_answer,
            "jschl_vc": self.jschl_vc,
        }

        if self.pass_value:
            data["pass"] = self.pass_value

        if self.s_value:
            data["s"] = self.s_value

        # Add any additional form data
        data.update(self.form_data)

        return data


class JSChallengeSolver:
    """Solves JavaScript-based Cloudflare challenges."""

    def __init__(self):
        self._compile_patterns()
        self._setup_js_context()
        self._setup_js_runtime()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for challenge parsing."""
        self.challenge_patterns = {
            # Challenge variable extraction
            "var_assignment": re.compile(r'var\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*([^;]+);'),
            "challenge_var": re.compile(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*["\']([^"\']*)["\'];'),

            # Mathematical operations
            "math_operation": re.compile(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*([+\-*/])\s*=\s*([^;]+);'),
            "function_call": re.compile(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\.\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(([^)]*)\)'),

            # String operations
            "string_concat": re.compile(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\+=\s*["\']([^"\']*)["\'];'),
            "string_method": re.compile(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\.\s*(charAt|charCodeAt|substr|substring)\s*\(([^)]*)\)'),

            # Form data extraction
            "jschl_vc": re.compile(r'name="jschl_vc"\s+value="([^"]+)"'),
            "pass_field": re.compile(r'name="pass"\s+value="([^"]+)"'),
            "s_field": re.compile(r'name="s"\s+value="([^"]+)"'),
            "form_action": re.compile(r'<form[^>]*action="([^"]*)"[^>]*id="challenge-form"', re.IGNORECASE),

            # Challenge timeout/delay
            "timeout_delay": re.compile(r'setTimeout\([^,]+,\s*(\d+)\)'),
        }

        # Mathematical function patterns
        self.math_patterns = {
            "charAt": re.compile(r'\.charAt\((\d+)\)'),
            "charCodeAt": re.compile(r'\.charCodeAt\((\d+)\)'),
            "length": re.compile(r'\.length'),
            "parseFloat": re.compile(r'parseFloat\(([^)]+)\)'),
            "parseInt": re.compile(r'parseInt\(([^)]+)(?:,\s*(\d+))?\)'),
        }

    def _setup_js_context(self) -> None:
        """Setup JavaScript execution context."""
        self.js_globals = {
            # Math functions
            "Math": self._create_math_object(),

            # String functions
            "String": str,
            "parseInt": self._js_parseInt,
            "parseFloat": self._js_parseFloat,
            "isNaN": self._js_isNaN,

            # Global constants
            "undefined": None,
            "null": None,
            "true": True,
            "false": False,
        }

    def _setup_js_runtime(self) -> None:
        """Setup MiniRacer JavaScript runtime."""
        self.js_context = MiniRacer()

        # Add basic JavaScript globals and Math object
        self.js_context.eval("""
            // Cloudflare challenge helper functions
            var cloudflareChallenge = {
                solve: function(code, domain) {
                    var t = domain;
                    eval(code);
                    return window.jschl_answer || window.answer || 0;
                }
            };
        """)

    def _create_math_object(self) -> Dict[str, Any]:
        """Create Math object with JavaScript functions."""
        return {
            "abs": abs,
            "ceil": math.ceil,
            "floor": math.floor,
            "round": round,
            "max": max,
            "min": min,
            "pow": pow,
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "PI": math.pi,
            "E": math.e,
        }

    def _js_parseInt(self, value: str, radix: int = 10) -> int:
        """JavaScript parseInt function."""
        try:
            # Handle string input
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return float('nan')

                # Extract numeric part
                match = re.match(r'[+-]?\d+', value)
                if match:
                    return int(match.group(), radix)

            return int(float(value))
        except (ValueError, TypeError):
            return float('nan')

    def _js_parseFloat(self, value: str) -> float:
        """JavaScript parseFloat function."""
        try:
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return float('nan')

                # Extract numeric part (including decimals)
                match = re.match(r'[+-]?\d*\.?\d*([eE][+-]?\d+)?', value)
                if match and match.group():
                    return float(match.group())

            return float(value)
        except (ValueError, TypeError):
            return float('nan')

    def _js_isNaN(self, value: Any) -> bool:
        """JavaScript isNaN function."""
        try:
            return math.isnan(float(value))
        except (ValueError, TypeError):
            return True

    def solve_challenge(self, html_content: str, url: str, challenge_delay: int = 4000) -> ChallengeSolution:
        """Solve JavaScript challenge from HTML content."""

        # Extract challenge components
        challenge_data = self._extract_challenge_data(html_content)

        # Extract and execute JavaScript
        js_answer = self._solve_javascript_challenge(html_content, url)

        # Create solution
        solution = ChallengeSolution(
            jschl_answer=str(js_answer),
            jschl_vc=challenge_data.get("jschl_vc", ""),
            pass_value=challenge_data.get("pass", ""),
            s_value=challenge_data.get("s", ""),
            submit_url=challenge_data.get("submit_url", ""),
            form_data=challenge_data.get("form_data", {})
        )

        # Wait for challenge delay if specified
        if challenge_delay > 0:
            time.sleep(challenge_delay / 1000.0)

        return solution

    def solve(self, challenge, **kwargs) -> ChallengeSolution:
        """Alias for solve_challenge method (contract API compatibility)."""
        if hasattr(challenge, 'url'):
            # Challenge object
            return self.solve_challenge(
                getattr(challenge, 'html', ''),
                challenge.url,
                kwargs.get('challenge_delay', 4000)
            )
        elif isinstance(challenge, dict):
            # Dictionary format
            return self.solve_challenge(
                challenge.get('html', challenge.get('content', '')),
                challenge.get('url', ''),
                kwargs.get('challenge_delay', 4000)
            )
        else:
            # Assume it's HTML content
            return self.solve_challenge(
                str(challenge),
                kwargs.get('url', ''),
                kwargs.get('challenge_delay', 4000)
            )

    def _extract_challenge_data(self, html_content: str) -> Dict[str, str]:
        """Extract challenge form data and URLs."""
        data = {}

        # Extract jschl_vc
        jschl_vc_match = self.challenge_patterns["jschl_vc"].search(html_content)
        if jschl_vc_match:
            data["jschl_vc"] = jschl_vc_match.group(1)

        # Extract pass field
        pass_match = self.challenge_patterns["pass_field"].search(html_content)
        if pass_match:
            data["pass"] = pass_match.group(1)

        # Extract s field
        s_match = self.challenge_patterns["s_field"].search(html_content)
        if s_match:
            data["s"] = s_match.group(1)

        # Extract form action URL
        form_action_match = self.challenge_patterns["form_action"].search(html_content)
        if form_action_match:
            data["submit_url"] = form_action_match.group(1)

        return data

    def _solve_javascript_challenge(self, html_content: str, url: str) -> Union[int, float]:
        """Solve the JavaScript mathematical challenge."""

        # Extract JavaScript code
        js_code = self._extract_challenge_javascript(html_content)

        if not js_code:
            raise ValueError("No JavaScript challenge code found")

        # Parse and execute JavaScript
        try:
            result = self._execute_challenge_javascript(js_code, url)
            return result
        except Exception as e:
            raise ValueError(f"Failed to solve JavaScript challenge: {e}")

    def _extract_challenge_javascript(self, html_content: str) -> str:
        """Extract JavaScript challenge code from HTML."""

        # Look for script tags with challenge code
        script_patterns = [
            r'<script[^>]*>(.*?var\s+[a-zA-Z_$][a-zA-Z0-9_$]*\s*=\s*[^;]+.*?)</script>',
            r'<script[^>]*>(.*?setTimeout\(.*?\).*?)</script>',
            r'<script[^>]*>(.*?jschl_answer.*?)</script>',
        ]

        for pattern in script_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if self._contains_challenge_code(match):
                    return match

        return ""

    def _contains_challenge_code(self, js_code: str) -> bool:
        """Check if JavaScript code contains challenge logic."""
        challenge_indicators = [
            "jschl_answer",
            "challenge-form",
            "setTimeout",
            "location.href",
        ]

        js_lower = js_code.lower()
        return any(indicator in js_lower for indicator in challenge_indicators)

    def _execute_challenge_javascript(self, js_code: str, url: str) -> Union[int, float]:
        """Execute JavaScript challenge code safely using MiniRacer."""

        # Parse URL for domain calculation
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        domain_length = len(domain)

        # Clean and prepare JavaScript code
        js_code = self._prepare_js_code(js_code)

        try:
            # First try with MiniRacer for accurate JavaScript execution
            result = self._execute_with_mini_racer(js_code, domain)
            if result is not None:
                return result + domain_length
        except Exception as e:
            # Fallback to custom Python interpreter
            pass

        # Fallback: Use custom Python-based interpreter
        return self._execute_with_python_fallback(js_code, domain, domain_length)

    def _execute_with_mini_racer(self, js_code: str, domain: str) -> Optional[Union[int, float]]:
        """Execute JavaScript using MiniRacer."""
        try:
            # Setup execution context
            setup_code = f"""
                var t = "{domain}";
                var jschl_answer = 0;
                var answer = 0;
                var a = 0;

                {js_code}

                // Return the final answer
                if (typeof jschl_answer !== 'undefined') {{
                    jschl_answer;
                }} else if (typeof answer !== 'undefined') {{
                    answer;
                }} else if (typeof a !== 'undefined') {{
                    a;
                }} else {{
                    0;
                }}
            """

            result = self.js_context.eval(setup_code)

            if isinstance(result, (int, float)):
                return result

        except Exception as e:
            # Log error but don't fail - we have fallback
            pass

        return None

    def _execute_with_python_fallback(self, js_code: str, domain: str, domain_length: int) -> Union[int, float]:
        """Fallback execution using custom Python interpreter."""
        # Initialize variables
        variables = {"t": domain, "t_length": domain_length}

        # Execute JavaScript line by line
        lines = js_code.split(';')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue

            try:
                self._execute_js_line(line, variables, domain)
            except Exception as e:
                # Continue with other lines if one fails
                pass

        # Look for the final answer variable
        possible_answer_vars = ['answer', 'jschl_answer', 'a', 'result']

        for var_name in possible_answer_vars:
            if var_name in variables:
                answer = variables[var_name]
                # Add domain length as typically required
                if isinstance(answer, (int, float)):
                    return answer + domain_length

        # Fallback: try to find any numeric variable
        for var_name, value in variables.items():
            if isinstance(value, (int, float)) and var_name != 't_length':
                return value + domain_length

        raise ValueError("Could not find challenge answer in JavaScript execution")

    def _prepare_js_code(self, js_code: str) -> str:
        """Clean and prepare JavaScript code for execution."""

        # Remove HTML entities
        js_code = js_code.replace('&lt;', '<').replace('&gt;', '>')
        js_code = js_code.replace('&amp;', '&').replace('&quot;', '"')

        # Remove comments
        js_code = re.sub(r'//[^\n]*', '', js_code)
        js_code = re.sub(r'/\*.*?\*/', '', js_code, flags=re.DOTALL)

        # Remove setTimeout and form submission code
        js_code = re.sub(r'setTimeout\([^}]*\}[^}]*\}[^;]*;', '', js_code)
        js_code = re.sub(r'document\.[^;]*;', '', js_code)
        js_code = re.sub(r'location\.[^;]*;', '', js_code)
        js_code = re.sub(r'window\.[^;]*;', '', js_code)

        # Clean up whitespace
        js_code = re.sub(r'\s+', ' ', js_code).strip()

        return js_code

    def _execute_js_line(self, line: str, variables: Dict[str, Any], domain: str) -> None:
        """Execute a single line of JavaScript."""

        # Variable assignment
        var_match = re.match(r'var\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(.+)', line)
        if var_match:
            var_name = var_match.group(1)
            var_value = var_match.group(2).strip()
            variables[var_name] = self._evaluate_js_expression(var_value, variables, domain)
            return

        # Assignment without var
        assign_match = re.match(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(.+)', line)
        if assign_match:
            var_name = assign_match.group(1)
            var_value = assign_match.group(2).strip()
            variables[var_name] = self._evaluate_js_expression(var_value, variables, domain)
            return

        # Compound assignment operations
        compound_ops = {
            '+=': lambda a, b: a + b,
            '-=': lambda a, b: a - b,
            '*=': lambda a, b: a * b,
            '/=': lambda a, b: a / b if b != 0 else 0,
            '%=': lambda a, b: a % b if b != 0 else 0,
        }

        for op, func in compound_ops.items():
            op_match = re.match(rf'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*{re.escape(op)}\s*(.+)', line)
            if op_match:
                var_name = op_match.group(1)
                expr = op_match.group(2).strip()
                if var_name in variables:
                    new_value = self._evaluate_js_expression(expr, variables, domain)
                    variables[var_name] = func(variables[var_name], new_value)
                return

    def _evaluate_js_expression(self, expr: str, variables: Dict[str, Any], domain: str) -> Any:
        """Evaluate JavaScript expression."""

        expr = expr.strip()

        # Handle string literals
        if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]

        # Handle numeric literals
        try:
            if '.' in expr:
                return float(expr)
            else:
                return int(expr)
        except ValueError:
            pass

        # Handle variable references
        if expr in variables:
            return variables[expr]

        # Handle string operations
        if '.charAt(' in expr:
            match = re.match(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\.charAt\((\d+)\)', expr)
            if match:
                var_name = match.group(1)
                index = int(match.group(2))
                if var_name in variables:
                    string_val = str(variables[var_name])
                    return string_val[index] if index < len(string_val) else ''

        if '.charCodeAt(' in expr:
            match = re.match(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\.charCodeAt\((\d+)\)', expr)
            if match:
                var_name = match.group(1)
                index = int(match.group(2))
                if var_name in variables:
                    string_val = str(variables[var_name])
                    return ord(string_val[index]) if index < len(string_val) else 0

        if '.length' in expr:
            match = re.match(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\.length', expr)
            if match:
                var_name = match.group(1)
                if var_name in variables:
                    return len(str(variables[var_name]))

        # Handle mathematical expressions
        math_expr = self._parse_math_expression(expr, variables)
        if math_expr is not None:
            return math_expr

        # Handle string concatenation
        if '+' in expr and any(isinstance(variables.get(var), str) for var in variables):
            parts = expr.split('+')
            result = ""
            for part in parts:
                part = part.strip()
                if part in variables:
                    result += str(variables[part])
                elif (part.startswith('"') and part.endswith('"')) or (part.startswith("'") and part.endswith("'")):
                    result += part[1:-1]
                else:
                    result += str(part)
            return result

        # Basic arithmetic with variables
        for op in ['+', '-', '*', '/', '%']:
            if op in expr:
                parts = expr.split(op, 1)
                if len(parts) == 2:
                    left = self._evaluate_js_expression(parts[0], variables, domain)
                    right = self._evaluate_js_expression(parts[1], variables, domain)

                    if op == '+':
                        return left + right
                    elif op == '-':
                        return left - right
                    elif op == '*':
                        return left * right
                    elif op == '/' and right != 0:
                        return left / right
                    elif op == '%' and right != 0:
                        return left % right

        return expr

    def _parse_math_expression(self, expr: str, variables: Dict[str, Any]) -> Optional[Union[int, float]]:
        """Parse mathematical expressions."""

        # Replace variables with their values
        for var_name, value in variables.items():
            if isinstance(value, (int, float)):
                expr = expr.replace(var_name, str(value))

        # Handle Math object methods
        math_funcs = {
            'Math.abs': abs,
            'Math.ceil': math.ceil,
            'Math.floor': math.floor,
            'Math.round': round,
            'Math.max': max,
            'Math.min': min,
            'Math.pow': pow,
            'Math.sqrt': math.sqrt,
        }

        for func_name, func in math_funcs.items():
            if func_name in expr:
                # Simple function call parsing
                pattern = rf'{re.escape(func_name)}\(([^)]+)\)'
                match = re.search(pattern, expr)
                if match:
                    args_str = match.group(1)
                    try:
                        args = [float(arg.strip()) for arg in args_str.split(',')]
                        result = func(*args) if len(args) > 1 else func(args[0])
                        expr = expr.replace(match.group(0), str(result))
                    except (ValueError, TypeError):
                        pass

        # Try to evaluate as Python expression
        try:
            # Only allow safe mathematical operations
            allowed_chars = set('0123456789+-*/().%= ')
            if all(c in allowed_chars for c in expr):
                return eval(expr)
        except (ValueError, SyntaxError, ZeroDivisionError):
            pass

        return None


# Utility functions
def create_js_solver() -> JSChallengeSolver:
    """Create a new JavaScript challenge solver."""
    return JSChallengeSolver()


def solve_js_challenge(html_content: str, url: str, delay: int = 4000) -> ChallengeSolution:
    """Quick function to solve a JavaScript challenge."""
    solver = JSChallengeSolver()
    return solver.solve_challenge(html_content, url, delay)