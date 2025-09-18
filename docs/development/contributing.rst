Contributing Guide
=================

Thank you for your interest in contributing to CloudflareBypass Research Tool! This guide will help you get started.

Code of Conduct
---------------

This project adheres to a code of conduct that all contributors are expected to follow:

**Our Standards**

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

**Unacceptable Behavior**

- Harassment, trolling, or discriminatory language
- Publishing others' private information
- Using the project for malicious purposes
- Violating applicable laws or terms of service

Getting Started
---------------

Development Environment Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Fork and clone the repository**::

    git clone https://github.com/yourusername/cloudflare-bypass-research.git
    cd cloudflare-bypass-research

2. **Set up development environment**::

    # Create virtual environment
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    venv\Scripts\activate     # Windows

    # Install development dependencies
    pip install -r requirements.txt
    pip install -r requirements-dev.txt

3. **Install pre-commit hooks**::

    pre-commit install

4. **Verify installation**::

    python -c "import cloudflare_research; print('Setup successful')"
    pytest tests/unit/ --maxfail=1

Development Dependencies
~~~~~~~~~~~~~~~~~~~~~~~

Additional tools for development::

    # Testing
    pytest>=7.4.0
    pytest-asyncio>=0.21.0
    pytest-cov>=4.1.0
    pytest-mock>=3.11.0

    # Code quality
    black>=23.7.0
    flake8>=6.0.0
    mypy>=1.5.0
    isort>=5.12.0

    # Security
    bandit>=1.7.0
    safety>=2.3.0

    # Documentation
    sphinx>=7.1.0
    sphinx-rtd-theme>=1.3.0

    # Development tools
    pre-commit>=3.3.0
    ipython>=8.14.0

Contributing Process
-------------------

Issue Reporting
~~~~~~~~~~~~~~

Before creating an issue:

1. **Check existing issues** to avoid duplicates
2. **Use the search function** to find related discussions
3. **Provide clear reproduction steps** for bugs
4. **Include environment information**

**Bug Report Template**::

    **Bug Description**
    A clear description of the bug.

    **Reproduction Steps**
    1. Step one
    2. Step two
    3. Step three

    **Expected Behavior**
    What should happen.

    **Actual Behavior**
    What actually happens.

    **Environment**
    - Python version:
    - OS:
    - CloudflareBypass version:
    - Dependencies:

    **Additional Context**
    Any other relevant information.

**Feature Request Template**::

    **Feature Description**
    Clear description of the requested feature.

    **Use Case**
    Why is this feature needed?

    **Proposed Solution**
    How should this be implemented?

    **Alternatives**
    Other solutions considered.

    **Additional Context**
    Any other relevant information.

Pull Request Process
~~~~~~~~~~~~~~~~~~~

1. **Create a feature branch**::

    git checkout -b feature/your-feature-name
    # or
    git checkout -b fix/issue-description

2. **Make your changes** following the coding standards

3. **Add or update tests** for your changes

4. **Run the test suite**::

    pytest
    flake8
    mypy
    black --check .

5. **Update documentation** if needed

6. **Commit your changes** with clear messages

7. **Push and create pull request**

**Pull Request Template**::

    **Description**
    Clear description of changes made.

    **Type of Change**
    - [ ] Bug fix
    - [ ] New feature
    - [ ] Breaking change
    - [ ] Documentation update

    **Testing**
    - [ ] Tests pass locally
    - [ ] New tests added
    - [ ] Manual testing completed

    **Checklist**
    - [ ] Code follows style guidelines
    - [ ] Self-review completed
    - [ ] Documentation updated
    - [ ] No breaking changes (or documented)

Coding Standards
---------------

Python Style
~~~~~~~~~~~

We follow PEP 8 with some modifications:

**Line Length**: 88 characters (Black default)

**Import Organization**::

    # Standard library imports
    import asyncio
    import json
    from typing import Dict, List, Optional

    # Third-party imports
    import aiohttp
    import pydantic

    # Local imports
    from cloudflare_research.models import CloudflareResponse
    from .utils import helper_function

**Function Documentation**::

    async def process_challenge(
        challenge_data: Dict[str, Any],
        timeout: float = 30.0
    ) -> ChallengeResult:
        """Process a Cloudflare challenge.

        Args:
            challenge_data: Dictionary containing challenge information
            timeout: Maximum time to spend solving the challenge

        Returns:
            ChallengeResult containing the solution and metadata

        Raises:
            ChallengeError: If the challenge cannot be solved
            TimeoutError: If solving exceeds the timeout
        """

**Type Hints**

Use type hints for all public APIs::

    from typing import Dict, List, Optional, Union, Any

    async def make_request(
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> CloudflareResponse:
        pass

Code Organization
~~~~~~~~~~~~~~~~

**Module Structure**::

    cloudflare_research/
    ├── __init__.py          # Public API exports
    ├── bypass.py            # Main bypass class
    ├── models/              # Data models
    │   ├── __init__.py
    │   └── response.py
    ├── challenge/           # Challenge system
    │   ├── __init__.py
    │   ├── detector.py
    │   └── solver.py
    └── utils/               # Utilities
        ├── __init__.py
        └── helpers.py

**Class Design**::

    class ComponentName:
        """Brief description of the component.

        Longer description if needed.

        Attributes:
            attribute_name: Description of attribute

        Example:
            Basic usage example::

                component = ComponentName()
                result = component.method()
        """

        def __init__(self, config: Config) -> None:
            """Initialize the component."""
            self.config = config

        async def public_method(self, param: str) -> str:
            """Public method with clear interface."""
            return await self._private_method(param)

        async def _private_method(self, param: str) -> str:
            """Private method (prefixed with underscore)."""
            # Implementation
            pass

Error Handling
~~~~~~~~~~~~~

**Exception Hierarchy**::

    class CloudflareBypassError(Exception):
        """Base exception for all CloudflareBypass errors."""
        pass

    class ChallengeError(CloudflareBypassError):
        """Raised when challenge solving fails."""
        pass

    class ConfigurationError(CloudflareBypassError):
        """Raised when configuration is invalid."""
        pass

**Error Handling Patterns**::

    async def process_request(url: str) -> Response:
        try:
            response = await http_client.get(url)
            return response
        except aiohttp.ClientError as e:
            # Convert to our exception hierarchy
            raise CloudflareBypassError(f"Request failed: {e}") from e
        except asyncio.TimeoutError as e:
            raise TimeoutError(f"Request to {url} timed out") from e

Testing Standards
----------------

Test Organization
~~~~~~~~~~~~~~~~

**Test Structure**::

    class TestComponentName:
        """Test class for ComponentName."""

        @pytest.fixture
        def component(self):
            """Fixture providing a configured component."""
            config = TestConfig()
            return ComponentName(config)

        @pytest.mark.asyncio
        async def test_method_success(self, component):
            """Test successful operation."""
            result = await component.method("test_input")
            assert result == "expected_output"

        @pytest.mark.asyncio
        async def test_method_failure(self, component):
            """Test error handling."""
            with pytest.raises(ExpectedError):
                await component.method("invalid_input")

**Test Naming Conventions**:

- `test_method_name_condition` - e.g., `test_solve_challenge_success`
- `test_method_name_error_case` - e.g., `test_solve_challenge_timeout`
- `test_method_name_edge_case` - e.g., `test_solve_challenge_empty_data`

**Assertions**::

    # Prefer specific assertions
    assert response.status_code == 200  # Good
    assert response.ok                  # Less specific

    # Use descriptive error messages
    assert len(results) == 5, f"Expected 5 results, got {len(results)}"

Mock Usage
~~~~~~~~~

**Mock External Dependencies**::

    @pytest.fixture
    def mock_http_client():
        with patch('cloudflare_research.http.HTTPClient') as mock:
            mock.get.return_value = MockResponse(200, "Success")
            yield mock

    @pytest.mark.asyncio
    async def test_with_mock(mock_http_client):
        bypass = CloudflareBypass(config)
        result = await bypass.get("https://example.com")
        assert result.status_code == 200

**Verify Interactions**::

    mock_http_client.get.assert_called_once_with(
        "https://example.com",
        headers=expected_headers
    )

Documentation Standards
----------------------

Code Documentation
~~~~~~~~~~~~~~~~~

**Module Docstrings**::

    """Challenge detection and solving module.

    This module provides functionality for detecting various types of
    Cloudflare challenges and implementing solving algorithms.

    Example:
        Basic usage::

            detector = ChallengeDetector()
            challenge_type = detector.detect(html_content)
    """

**Class Docstrings**::

    class ChallengeDetector:
        """Detects Cloudflare challenges in HTTP responses.

        The detector analyzes HTML content and HTTP headers to identify
        the type of challenge present, if any.

        Attributes:
            patterns: Compiled regex patterns for detection
            timeout: Detection timeout in seconds

        Example:
            Detect challenge type::

                detector = ChallengeDetector()
                challenge_type = detector.detect_challenge_type(html, headers)
        """

**Method Docstrings**::

    async def solve_javascript_challenge(
        self,
        challenge_data: Dict[str, Any]
    ) -> ChallengeResult:
        """Solve a JavaScript challenge.

        Executes the challenge JavaScript code and returns the solution.

        Args:
            challenge_data: Dictionary containing:
                - code: JavaScript code to execute
                - nonce: Challenge nonce
                - timeout: Optional timeout override

        Returns:
            ChallengeResult with solution and metadata

        Raises:
            ChallengeError: If challenge cannot be solved
            TimeoutError: If execution exceeds timeout

        Example:
            Solve a challenge::

                result = await solver.solve_javascript_challenge({
                    'code': 'function challenge() { return 42; }',
                    'nonce': 'abc123'
                })
        """

API Documentation
~~~~~~~~~~~~~~~~

**Keep docstrings up-to-date** with code changes

**Include examples** for complex APIs

**Document edge cases** and error conditions

**Use consistent terminology** throughout

Commit Message Format
--------------------

We use conventional commits for clear history:

**Format**::

    <type>[optional scope]: <description>

    [optional body]

    [optional footer(s)]

**Types**:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks

**Examples**::

    feat(challenge): add Turnstile CAPTCHA support

    Implement detection and solving for Cloudflare Turnstile CAPTCHAs.
    Includes new solver class and integration with challenge manager.

    Closes #123

    fix(http): handle connection pool exhaustion

    Add proper error handling when connection pool is exhausted.
    Includes retry logic and graceful degradation.

    performance(browser): optimize header generation

    Cache compiled regexes for better performance.
    Reduces header generation time by ~40%.

Release Process
--------------

Version Management
~~~~~~~~~~~~~~~~~

We use semantic versioning (SemVer):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

**Version Bumping**::

    # Update version in setup.py and __init__.py
    # Create changelog entry
    # Tag the release
    git tag v1.2.3
    git push origin v1.2.3

Release Checklist
~~~~~~~~~~~~~~~~

Before releasing:

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version bumped
- [ ] Security scan completed
- [ ] Performance benchmarks run

**Release Notes Template**::

    ## [1.2.3] - 2023-XX-XX

    ### Added
    - New feature descriptions

    ### Changed
    - Modified functionality

    ### Fixed
    - Bug fix descriptions

    ### Security
    - Security improvements

Community Guidelines
-------------------

Communication
~~~~~~~~~~~~

**Be Respectful**: Treat all contributors with respect

**Be Patient**: Remember that people contribute in their free time

**Be Constructive**: Provide helpful feedback and suggestions

**Be Inclusive**: Welcome contributors of all backgrounds

Mentorship
~~~~~~~~~

**First-time Contributors**:
- Look for "good first issue" labels
- Ask questions in discussions
- Request code reviews
- Start with documentation or tests

**Experienced Contributors**:
- Help review pull requests
- Mentor new contributors
- Share knowledge in discussions
- Help maintain code quality

Recognition
~~~~~~~~~~

We recognize contributors through:

- Contributor acknowledgments in releases
- GitHub contributor graphs
- Special recognition for significant contributions
- Opportunity to become a maintainer

Security Guidelines
------------------

Reporting Security Issues
~~~~~~~~~~~~~~~~~~~~~~~~

**DO NOT** create public issues for security vulnerabilities.

Instead:
1. Email security issues to: security@example.com
2. Include detailed description and reproduction steps
3. Allow time for investigation and fix
4. Coordinate disclosure timing

Secure Development
~~~~~~~~~~~~~~~~~

**Input Validation**: Always validate external inputs

**Secrets Management**: Never commit secrets or keys

**Dependency Security**: Regularly update dependencies

**Code Review**: Security-focused code reviews

Legal Considerations
-------------------

Licensing
~~~~~~~~

- All contributions must be compatible with the MIT License
- Contributors retain copyright to their contributions
- By contributing, you agree to license under project terms

Ethical Use
~~~~~~~~~~

- Contributions must support legitimate research and testing
- No features designed primarily for malicious use
- Respect for target website terms of service
- Responsible disclosure of security findings

Getting Help
-----------

If you need help:

1. **Check the documentation** first
2. **Search existing issues** for similar problems
3. **Ask in GitHub Discussions** for general questions
4. **Create an issue** for bugs or feature requests
5. **Join our community** for real-time discussion

Resources
--------

- **Documentation**: https://cloudflare-bypass-docs.readthedocs.io
- **GitHub Repository**: https://github.com/username/cloudflare-bypass-research
- **Issue Tracker**: https://github.com/username/cloudflare-bypass-research/issues
- **Discussions**: https://github.com/username/cloudflare-bypass-research/discussions

Thank you for contributing to CloudflareBypass Research Tool! 🎉

.. seealso::
   - :doc:`testing` - Testing guidelines and practices
   - :doc:`architecture` - System architecture overview