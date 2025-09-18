CloudflareBypass Core Module
============================

The core bypass module provides the main CloudflareBypass class and configuration options.

.. currentmodule:: cloudflare_research.bypass

Main Classes
------------

.. autoclass:: CloudflareBypass
   :members:
   :undoc-members:
   :show-inheritance:

   .. automethod:: __init__
   .. automethod:: __aenter__
   .. automethod:: __aexit__

Configuration
-------------

.. autoclass:: CloudflareBypassConfig
   :members:
   :undoc-members:
   :show-inheritance:

Request Methods
---------------

The CloudflareBypass class provides HTTP methods that automatically handle Cloudflare challenges:

.. automethod:: CloudflareBypass.get
.. automethod:: CloudflareBypass.post
.. automethod:: CloudflareBypass.put
.. automethod:: CloudflareBypass.delete
.. automethod:: CloudflareBypass.head
.. automethod:: CloudflareBypass.options
.. automethod:: CloudflareBypass.patch

Response Handling
-----------------

.. automethod:: CloudflareBypass.process_response
.. automethod:: CloudflareBypass.handle_redirect
.. automethod:: CloudflareBypass.check_cloudflare_protection

Session Management
------------------

.. automethod:: CloudflareBypass.create_session
.. automethod:: CloudflareBypass.close_session

Example Usage
-------------

Basic Request::

    async with CloudflareBypass(config) as bypass:
        response = await bypass.get("https://example.com")
        print(f"Status: {response.status_code}")
        print(f"Content: {response.content}")

With Custom Headers::

    headers = {"User-Agent": "Custom Agent"}
    response = await bypass.get("https://example.com", headers=headers)

High Concurrency::

    import asyncio

    async def make_request(bypass, url):
        return await bypass.get(url)

    async with CloudflareBypass(config) as bypass:
        tasks = [make_request(bypass, url) for url in urls]
        results = await asyncio.gather(*tasks)

.. seealso::
   :doc:`../user_guide/examples` for more detailed examples.