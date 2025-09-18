HTTP Client Module
==================

The HTTP module provides high-performance HTTP/2 client capabilities with cookie management and response handling.

.. currentmodule:: cloudflare_research.http

HTTP Client
-----------

.. automodule:: cloudflare_research.http.client
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: CloudflareHTTPClient
   :members:
   :undoc-members:
   :show-inheritance:

   High-performance HTTP client optimized for Cloudflare interactions.

.. automethod:: CloudflareHTTPClient.request
.. automethod:: CloudflareHTTPClient.get
.. automethod:: CloudflareHTTPClient.post
.. automethod:: CloudflareHTTPClient.close

HTTP/2 Support
--------------

.. automodule:: cloudflare_research.http.http2
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: HTTP2Client
   :members:
   :undoc-members:
   :show-inheritance:

   Native HTTP/2 client implementation for optimal performance.

.. automethod:: HTTP2Client.send_request
.. automethod:: HTTP2Client.create_connection
.. automethod:: HTTP2Client.handle_response

Cookie Management
-----------------

.. automodule:: cloudflare_research.http.cookies
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: CookieManager
   :members:
   :undoc-members:
   :show-inheritance:

   Manages Cloudflare-specific cookies including __cf_bm and cf_clearance.

.. automethod:: CookieManager.extract_cf_cookies
.. automethod:: CookieManager.update_cookies
.. automethod:: CookieManager.get_cookie_header
.. automethod:: CookieManager.is_cf_cookie

Response Processing
-------------------

.. automodule:: cloudflare_research.http.response
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: CloudflareResponse
   :members:
   :undoc-members:
   :show-inheritance:

   Enhanced response object with Cloudflare-specific analysis.

.. automethod:: CloudflareResponse.is_cloudflare_protected
.. automethod:: CloudflareResponse.get_cf_ray
.. automethod:: CloudflareResponse.has_challenge
.. automethod:: CloudflareResponse.get_challenge_type

Client Configuration
--------------------

.. autoclass:: HTTPClientConfig
   :members:
   :undoc-members:
   :show-inheritance:

   Configuration options for the HTTP client.

Connection Management
---------------------

.. autoclass:: ConnectionPool
   :members:
   :undoc-members:
   :show-inheritance:

   Manages persistent connections with connection pooling.

.. automethod:: ConnectionPool.get_connection
.. automethod:: ConnectionPool.release_connection
.. automethod:: ConnectionPool.cleanup_idle_connections

Example Usage
-------------

Basic HTTP Request::

    client = CloudflareHTTPClient()
    response = await client.get("https://example.com")

    print(f"Status: {response.status_code}")
    print(f"CF-RAY: {response.get_cf_ray()}")
    print(f"Protected: {response.is_cloudflare_protected()}")

Cookie Management::

    cookie_manager = CookieManager()

    # Extract Cloudflare cookies from response
    cf_cookies = cookie_manager.extract_cf_cookies(response.headers)

    # Use cookies in subsequent requests
    headers = {"Cookie": cookie_manager.get_cookie_header()}
    response = await client.get("https://example.com", headers=headers)

HTTP/2 with Custom Configuration::

    config = HTTPClientConfig(
        use_http2=True,
        max_connections=100,
        connection_timeout=30.0,
        read_timeout=60.0
    )

    client = CloudflareHTTPClient(config)
    response = await client.request("GET", "https://example.com")

Connection Pooling::

    pool = ConnectionPool(max_size=50)

    async with pool.get_connection("https://example.com") as conn:
        response = await conn.request("GET", "/api/endpoint")

Response Analysis::

    response = await client.get("https://cloudflare-protected-site.com")

    if response.has_challenge():
        challenge_type = response.get_challenge_type()
        print(f"Challenge detected: {challenge_type}")

    # Check for specific Cloudflare indicators
    if response.is_cloudflare_protected():
        cf_ray = response.get_cf_ray()
        print(f"Cloudflare Ray ID: {cf_ray}")

.. seealso::
   :doc:`../user_guide/examples` for more HTTP client examples.