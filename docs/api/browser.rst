Browser Emulation Module
========================

The browser module provides comprehensive browser emulation capabilities including TLS fingerprinting, header generation, and behavioral timing.

.. currentmodule:: cloudflare_research.browser

Browser Fingerprinting
-----------------------

.. automodule:: cloudflare_research.browser.fingerprint
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: TLSFingerprint
   :members:
   :undoc-members:
   :show-inheritance:

   Manages TLS fingerprinting to mimic real browser behavior.

.. automethod:: TLSFingerprint.generate_ja3_fingerprint
.. automethod:: TLSFingerprint.randomize_fingerprint
.. automethod:: TLSFingerprint.get_cipher_suites
.. automethod:: TLSFingerprint.get_supported_versions

Header Generation
-----------------

.. automodule:: cloudflare_research.browser.headers
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: HeaderGenerator
   :members:
   :undoc-members:
   :show-inheritance:

   Generates authentic browser headers based on specified browser profiles.

.. automethod:: HeaderGenerator.generate_headers
.. automethod:: HeaderGenerator.get_user_agent
.. automethod:: HeaderGenerator.get_accept_headers
.. automethod:: HeaderGenerator.get_browser_profile

Behavioral Timing
-----------------

.. automodule:: cloudflare_research.browser.timing
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BehaviorTiming
   :members:
   :undoc-members:
   :show-inheritance:

   Simulates human-like timing patterns for requests and interactions.

.. automethod:: BehaviorTiming.calculate_delay
.. automethod:: BehaviorTiming.randomize_timing
.. automethod:: BehaviorTiming.get_navigation_timing
.. automethod:: BehaviorTiming.simulate_user_interaction

Browser Profiles
-----------------

Supported browser profiles for emulation:

Chrome Profiles
~~~~~~~~~~~~~~~

.. autodata:: CHROME_LATEST
   :annotation: Latest Chrome browser profile

.. autodata:: CHROME_MOBILE
   :annotation: Chrome mobile browser profile

Firefox Profiles
~~~~~~~~~~~~~~~~

.. autodata:: FIREFOX_LATEST
   :annotation: Latest Firefox browser profile

.. autodata:: FIREFOX_ESR
   :annotation: Firefox ESR browser profile

Safari Profiles
~~~~~~~~~~~~~~~

.. autodata:: SAFARI_LATEST
   :annotation: Latest Safari browser profile

.. autodata:: SAFARI_MOBILE
   :annotation: Safari mobile browser profile

Configuration Options
---------------------

.. autoclass:: BrowserConfig
   :members:
   :undoc-members:
   :show-inheritance:

   Configuration for browser emulation behavior.

Example Usage
-------------

Generate TLS Fingerprint::

    fingerprint = TLSFingerprint()
    ja3_string = fingerprint.generate_ja3_fingerprint("chrome_120")
    print(f"JA3: {ja3_string}")

Create Browser Headers::

    header_gen = HeaderGenerator("chrome", "120.0.0.0")
    headers = header_gen.generate_headers("https://example.com")

    for key, value in headers.items():
        print(f"{key}: {value}")

Simulate Human Timing::

    timing = BehaviorTiming()
    delay = timing.calculate_delay("navigation")
    await asyncio.sleep(delay)

Complete Browser Emulation::

    config = BrowserConfig(
        browser_type="chrome",
        version="120.0.0.0",
        platform="Windows",
        mobile=False
    )

    # Generate fingerprint
    fingerprint = TLSFingerprint()
    ja3 = fingerprint.generate_ja3_fingerprint(config.profile_id)

    # Generate headers
    header_gen = HeaderGenerator(config.browser_type, config.version)
    headers = header_gen.generate_headers(url)

    # Apply timing
    timing = BehaviorTiming()
    await asyncio.sleep(timing.calculate_delay("request"))

.. seealso::
   :doc:`../user_guide/configuration` for detailed browser configuration options.