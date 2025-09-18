Challenge Detection and Solving
===============================

The challenge module provides comprehensive detection and solving capabilities for various Cloudflare challenge types.

.. currentmodule:: cloudflare_research.challenge

Challenge Manager
-----------------

.. autoclass:: ChallengeManager
   :members:
   :undoc-members:
   :show-inheritance:

   The main challenge management interface that coordinates detection, parsing, and solving.

Challenge Detection
-------------------

.. currentmodule:: cloudflare_research.challenge.detector

.. autoclass:: ChallengeDetector
   :members:
   :undoc-members:
   :show-inheritance:

   Detects various types of Cloudflare challenges in HTTP responses.

.. automethod:: ChallengeDetector.detect_challenge_type
.. automethod:: ChallengeDetector.is_javascript_challenge
.. automethod:: ChallengeDetector.is_turnstile_challenge
.. automethod:: ChallengeDetector.is_managed_challenge
.. automethod:: ChallengeDetector.is_rate_limited

Challenge Parsing
-----------------

.. currentmodule:: cloudflare_research.challenge.parser

.. autoclass:: ChallengeParser
   :members:
   :undoc-members:
   :show-inheritance:

   Extracts challenge data from HTML responses.

.. automethod:: ChallengeParser.parse_javascript_challenge
.. automethod:: ChallengeParser.extract_cf_challenge_data
.. automethod:: ChallengeParser.parse_turnstile_challenge

Challenge Solving
-----------------

.. currentmodule:: cloudflare_research.challenge.solver

.. autoclass:: ChallengeSolver
   :members:
   :undoc-members:
   :show-inheritance:

   Solves various challenge types using appropriate algorithms.

.. automethod:: ChallengeSolver.solve_javascript_challenge
.. automethod:: ChallengeSolver.execute_javascript
.. automethod:: ChallengeSolver.solve_turnstile_challenge

Turnstile Integration
---------------------

.. currentmodule:: cloudflare_research.challenge.turnstile

.. autoclass:: TurnstileIntegration
   :members:
   :undoc-members:
   :show-inheritance:

   Handles Cloudflare Turnstile CAPTCHA challenges.

.. automethod:: TurnstileIntegration.solve_turnstile
.. automethod:: TurnstileIntegration.get_turnstile_token
.. automethod:: TurnstileIntegration.verify_turnstile_response

Challenge Handler
-----------------

.. currentmodule:: cloudflare_research.challenge.handler

.. autoclass:: ChallengeHandler
   :members:
   :undoc-members:
   :show-inheritance:

   High-level interface for handling complete challenge workflows.

Data Models
-----------

.. currentmodule:: cloudflare_research.challenge

.. autoclass:: ChallengeResult
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: ChallengeType
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: JavaScriptChallenge
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: TurnstileChallenge
   :members:
   :undoc-members:
   :show-inheritance:

Example Usage
-------------

Detect Challenge Type::

    detector = ChallengeDetector()
    challenge_type = detector.detect_challenge_type(html_content, headers)

    if challenge_type == ChallengeType.JAVASCRIPT:
        print("JavaScript challenge detected")

Parse and Solve JavaScript Challenge::

    parser = ChallengeParser()
    solver = ChallengeSolver()

    challenge_data = parser.parse_javascript_challenge(html_content)
    solution = await solver.solve_javascript_challenge(challenge_data)

Complete Challenge Workflow::

    manager = ChallengeManager()
    result = await manager.process_response(
        response_content=html_content,
        response_headers=headers,
        status_code=status_code,
        request_url=url,
        http_client=client
    )

    if result.success:
        print("Challenge solved successfully")
        # Use result.solution for subsequent requests

.. seealso::
   :doc:`../user_guide/troubleshooting` for challenge-specific troubleshooting.