Session Management
==================

The session module provides persistent session management with state tracking and cookie persistence across requests.

.. currentmodule:: cloudflare_research.session

Session Manager
---------------

.. autoclass:: SessionManager
   :members:
   :undoc-members:
   :show-inheritance:

   Manages persistent sessions for maintaining state across multiple requests.

.. automethod:: SessionManager.create_session
.. automethod:: SessionManager.get_session
.. automethod:: SessionManager.close_session
.. automethod:: SessionManager.cleanup_expired_sessions

Managed Session
---------------

.. autoclass:: ManagedSession
   :members:
   :undoc-members:
   :show-inheritance:

   Represents a single managed session with state and cookie persistence.

.. automethod:: ManagedSession.make_request
.. automethod:: ManagedSession.update_cookies
.. automethod:: ManagedSession.get_state
.. automethod:: ManagedSession.set_state

Session State
-------------

.. autoclass:: SessionState
   :members:
   :undoc-members:
   :show-inheritance:

   Tracks session state including cookies, headers, and challenge solutions.

.. automethod:: SessionState.update_from_response
.. automethod:: SessionState.get_request_headers
.. automethod:: SessionState.has_valid_cf_clearance
.. automethod:: SessionState.is_expired

Cookie Persistence
------------------

.. autoclass:: CookieJar
   :members:
   :undoc-members:
   :show-inheritance:

   Advanced cookie jar with Cloudflare-specific cookie handling.

.. automethod:: CookieJar.set_cookie
.. automethod:: CookieJar.get_cookies_for_url
.. automethod:: CookieJar.clear_expired_cookies
.. automethod:: CookieJar.serialize
.. automethod:: CookieJar.deserialize

Session Configuration
---------------------

.. autoclass:: SessionConfig
   :members:
   :undoc-members:
   :show-inheritance:

   Configuration options for session behavior.

Session Persistence
-------------------

.. autoclass:: SessionPersistence
   :members:
   :undoc-members:
   :show-inheritance:

   Handles session persistence to disk for resuming sessions across application restarts.

.. automethod:: SessionPersistence.save_session
.. automethod:: SessionPersistence.load_session
.. automethod:: SessionPersistence.delete_session
.. automethod:: SessionPersistence.list_sessions

Example Usage
-------------

Basic Session Management::

    session_manager = SessionManager()

    # Create a new session
    session = await session_manager.create_session("user_123")

    # Make requests with persistent state
    response1 = await session.make_request("GET", "https://example.com/login")
    response2 = await session.make_request("POST", "https://example.com/api/data")

    # Session automatically maintains cookies and state
    assert session.get_state().has_valid_cf_clearance()

    # Close session when done
    await session_manager.close_session("user_123")

Session with Custom Configuration::

    config = SessionConfig(
        cookie_expiry_hours=24,
        max_redirects=10,
        persistent_storage=True,
        storage_path="./sessions"
    )

    session_manager = SessionManager(config)
    session = await session_manager.create_session("persistent_session")

    # Session will be automatically saved to disk
    response = await session.make_request("GET", "https://example.com")

Session Persistence::

    persistence = SessionPersistence("./sessions")

    # Save session for later use
    await persistence.save_session("user_123", session.get_state())

    # Load session in a different application run
    saved_state = await persistence.load_session("user_123")
    if saved_state:
        session = await session_manager.restore_session("user_123", saved_state)

Multiple Sessions::

    session_manager = SessionManager()

    # Create multiple sessions for different users/contexts
    sessions = {}
    for user_id in ["user_1", "user_2", "user_3"]:
        sessions[user_id] = await session_manager.create_session(user_id)

    # Make concurrent requests with different sessions
    async def user_workflow(user_id, session):
        response = await session.make_request("GET", f"https://example.com/user/{user_id}")
        return response.status_code

    results = await asyncio.gather(*[
        user_workflow(user_id, session)
        for user_id, session in sessions.items()
    ])

    # Clean up all sessions
    for user_id in sessions:
        await session_manager.close_session(user_id)

Session State Inspection::

    session = await session_manager.create_session("inspector")

    # Make a request
    response = await session.make_request("GET", "https://cloudflare-protected.com")

    # Inspect session state
    state = session.get_state()

    print(f"CF Clearance valid: {state.has_valid_cf_clearance()}")
    print(f"Cookies count: {len(state.cookies)}")
    print(f"Session age: {state.age_seconds}s")

    # Get headers for next request
    headers = state.get_request_headers()
    print(f"Request headers: {headers}")

Advanced Cookie Handling::

    cookie_jar = CookieJar()

    # Manual cookie management
    cookie_jar.set_cookie("cf_clearance", "abc123", domain=".example.com")
    cookie_jar.set_cookie("__cf_bm", "xyz789", domain=".example.com")

    # Get cookies for specific URL
    cookies = cookie_jar.get_cookies_for_url("https://example.com/api")

    # Serialize for storage
    serialized = cookie_jar.serialize()
    with open("cookies.json", "w") as f:
        json.dump(serialized, f)

    # Deserialize from storage
    with open("cookies.json", "r") as f:
        data = json.load(f)
    cookie_jar.deserialize(data)

.. seealso::
   :doc:`../user_guide/examples` for complete session management examples.