"""Cookie jar and session management.

Provides HTTP cookie handling with proper parsing, storage,
and Chrome-compatible behavior.
"""

import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from urllib.parse import urlparse, urljoin
from datetime import datetime, timedelta


@dataclass
class Cookie:
    """Represents an HTTP cookie."""
    name: str
    value: str
    domain: Optional[str] = None
    path: str = "/"
    expires: Optional[datetime] = None
    max_age: Optional[int] = None
    secure: bool = False
    http_only: bool = False
    same_site: Optional[str] = None  # None, "Strict", "Lax", "None"
    created: datetime = field(default_factory=datetime.now)
    
    @property
    def is_expired(self) -> bool:
        """Check if cookie is expired."""
        if self.max_age is not None:
            expiry = self.created + timedelta(seconds=self.max_age)
            return datetime.now() > expiry
        
        if self.expires is not None:
            return datetime.now() > self.expires
        
        return False
    
    @property
    def is_session_cookie(self) -> bool:
        """Check if cookie is a session cookie (no expiry)."""
        return self.expires is None and self.max_age is None
    
    def matches_domain(self, domain: str) -> bool:
        """Check if cookie matches domain."""
        if not self.domain:
            return False
        
        cookie_domain = self.domain.lower().lstrip('.')
        request_domain = domain.lower()
        
        # Exact match
        if cookie_domain == request_domain:
            return True
        
        # Domain attribute starts with dot - subdomain match
        if self.domain.startswith('.'):
            return request_domain.endswith(cookie_domain)
        
        return False
    
    def matches_path(self, path: str) -> bool:
        """Check if cookie matches path."""
        if not self.path:
            return True
        
        # Path must be a prefix of request path
        if path.startswith(self.path):
            # Exact match or path ends with / or next char is /
            if len(path) == len(self.path):
                return True
            if self.path.endswith('/'):
                return True
            if len(path) > len(self.path) and path[len(self.path)] == '/':
                return True
        
        return False
    
    def to_header_value(self) -> str:
        """Convert cookie to header value format."""
        return f"{self.name}={self.value}"
    
    def to_set_cookie_header(self) -> str:
        """Convert cookie to Set-Cookie header format."""
        parts = [f"{self.name}={self.value}"]
        
        if self.domain:
            parts.append(f"Domain={self.domain}")
        
        if self.path and self.path != "/":
            parts.append(f"Path={self.path}")
        
        if self.expires:
            parts.append(f"Expires={self.expires.strftime('%a, %d %b %Y %H:%M:%S GMT')}")
        
        if self.max_age is not None:
            parts.append(f"Max-Age={self.max_age}")
        
        if self.secure:
            parts.append("Secure")
        
        if self.http_only:
            parts.append("HttpOnly")
        
        if self.same_site:
            parts.append(f"SameSite={self.same_site}")
        
        return "; ".join(parts)


class CookieJar:
    """HTTP cookie jar for session management."""
    
    def __init__(self):
        self._cookies: Dict[str, Dict[str, Cookie]] = {}  # domain -> name -> cookie
        self._session_cookies: Set[str] = set()  # Track session cookie keys
    
    def add_cookie(self, cookie: Cookie, url: str) -> None:
        """Add cookie to jar."""
        parsed_url = urlparse(url)
        
        # Set domain if not specified
        if not cookie.domain:
            cookie.domain = parsed_url.hostname
        
        # Validate domain
        if not self._is_valid_domain(cookie.domain, parsed_url.hostname):
            return
        
        # Set path if not specified
        if not cookie.path or cookie.path == "/":
            cookie.path = self._default_path(parsed_url.path)
        
        # Store cookie
        domain_key = cookie.domain.lower()
        if domain_key not in self._cookies:
            self._cookies[domain_key] = {}
        
        self._cookies[domain_key][cookie.name] = cookie
        
        # Track session cookies
        if cookie.is_session_cookie:
            self._session_cookies.add(f"{domain_key}:{cookie.name}")
    
    def get_cookies(self, url: str, secure_only: bool = None) -> List[Cookie]:
        """Get cookies for URL."""
        parsed_url = urlparse(url)
        domain = parsed_url.hostname.lower() if parsed_url.hostname else ""
        path = parsed_url.path or "/"
        is_secure = parsed_url.scheme == "https"
        
        if secure_only is None:
            secure_only = is_secure
        
        matching_cookies = []
        
        # Check all domains for matches
        for cookie_domain, cookies in self._cookies.items():
            for cookie in cookies.values():
                if self._cookie_matches_request(cookie, domain, path, is_secure, secure_only):
                    matching_cookies.append(cookie)
        
        # Sort by path length (most specific first) and creation time
        matching_cookies.sort(key=lambda c: (-len(c.path), c.created))
        
        return matching_cookies
    
    def get_cookie_header(self, url: str) -> Optional[str]:
        """Get Cookie header value for URL."""
        cookies = self.get_cookies(url)
        if not cookies:
            return None
        
        cookie_values = [cookie.to_header_value() for cookie in cookies]
        return "; ".join(cookie_values)
    
    def parse_set_cookie(self, set_cookie_header: str, url: str) -> None:
        """Parse Set-Cookie header and add cookies."""
        # Handle multiple Set-Cookie headers
        if isinstance(set_cookie_header, list):
            for header in set_cookie_header:
                self._parse_single_set_cookie(header, url)
        else:
            # Split by comma, but be careful with expires dates
            cookies = self._split_set_cookie_header(set_cookie_header)
            for cookie_str in cookies:
                self._parse_single_set_cookie(cookie_str, url)
    
    def _parse_single_set_cookie(self, cookie_str: str, url: str) -> None:
        """Parse single Set-Cookie header."""
        if not cookie_str.strip():
            return
        
        parts = [part.strip() for part in cookie_str.split(';')]
        if not parts:
            return
        
        # Parse name=value
        name_value = parts[0]
        if '=' not in name_value:
            return
        
        name, value = name_value.split('=', 1)
        name = name.strip()
        value = value.strip().strip('"')
        
        cookie = Cookie(name=name, value=value)
        
        # Parse attributes
        for part in parts[1:]:
            if '=' in part:
                attr_name, attr_value = part.split('=', 1)
                attr_name = attr_name.strip().lower()
                attr_value = attr_value.strip()
                
                if attr_name == 'domain':
                    cookie.domain = attr_value.lower()
                elif attr_name == 'path':
                    cookie.path = attr_value
                elif attr_name == 'expires':
                    cookie.expires = self._parse_expires(attr_value)
                elif attr_name == 'max-age':
                    try:
                        cookie.max_age = int(attr_value)
                    except ValueError:
                        pass
                elif attr_name == 'samesite':
                    cookie.same_site = attr_value
            else:
                attr_name = part.strip().lower()
                if attr_name == 'secure':
                    cookie.secure = True
                elif attr_name == 'httponly':
                    cookie.http_only = True
        
        self.add_cookie(cookie, url)
    
    def _split_set_cookie_header(self, header: str) -> List[str]:
        """Split Set-Cookie header handling expires dates."""
        # Simple split - real implementation would handle expires dates properly
        return [cookie.strip() for cookie in header.split(',') if '=' in cookie]
    
    def _parse_expires(self, expires_str: str) -> Optional[datetime]:
        """Parse expires date string."""
        import email.utils
        try:
            timestamp = email.utils.parsedate_to_datetime(expires_str)
            return timestamp.replace(tzinfo=None)  # Remove timezone for simplicity
        except (ValueError, TypeError):
            return None
    
    def _is_valid_domain(self, cookie_domain: str, request_domain: str) -> bool:
        """Validate cookie domain against request domain."""
        if not cookie_domain or not request_domain:
            return False
        
        cookie_domain = cookie_domain.lower().lstrip('.')
        request_domain = request_domain.lower()
        
        # Reject obvious mismatches
        if cookie_domain != request_domain and not request_domain.endswith('.' + cookie_domain):
            return False
        
        # Additional security checks would go here
        return True
    
    def _default_path(self, request_path: str) -> str:
        """Calculate default path for cookie."""
        if not request_path or request_path == '/':
            return '/'
        
        # Remove filename
        if request_path.endswith('/'):
            return request_path
        
        last_slash = request_path.rfind('/')
        if last_slash > 0:
            return request_path[:last_slash]
        
        return '/'
    
    def _cookie_matches_request(self, cookie: Cookie, domain: str, path: str,
                              is_secure: bool, secure_only: bool) -> bool:
        """Check if cookie matches request."""
        # Check expiry
        if cookie.is_expired:
            return False
        
        # Check domain
        if not cookie.matches_domain(domain):
            return False
        
        # Check path
        if not cookie.matches_path(path):
            return False
        
        # Check secure flag
        if cookie.secure and not is_secure:
            return False
        
        if secure_only and not cookie.secure:
            return False
        
        return True
    
    def clear_expired(self) -> int:
        """Remove expired cookies and return count removed."""
        removed_count = 0
        
        for domain in list(self._cookies.keys()):
            for name in list(self._cookies[domain].keys()):
                cookie = self._cookies[domain][name]
                if cookie.is_expired:
                    del self._cookies[domain][name]
                    removed_count += 1
                    
                    # Remove from session cookies if present
                    session_key = f"{domain}:{name}"
                    self._session_cookies.discard(session_key)
            
            # Remove empty domains
            if not self._cookies[domain]:
                del self._cookies[domain]
        
        return removed_count
    
    def clear_session_cookies(self) -> int:
        """Remove session cookies and return count removed."""
        removed_count = 0
        
        for session_key in list(self._session_cookies):
            domain, name = session_key.split(':', 1)
            if domain in self._cookies and name in self._cookies[domain]:
                del self._cookies[domain][name]
                removed_count += 1
                
                # Remove empty domains
                if not self._cookies[domain]:
                    del self._cookies[domain]
        
        self._session_cookies.clear()
        return removed_count
    
    def clear_all(self) -> None:
        """Clear all cookies."""
        self._cookies.clear()
        self._session_cookies.clear()
    
    def get_all_cookies(self) -> List[Cookie]:
        """Get all cookies in jar."""
        all_cookies = []
        for domain_cookies in self._cookies.values():
            all_cookies.extend(domain_cookies.values())
        return all_cookies
    
    def get_cookie_count(self) -> int:
        """Get total number of cookies."""
        return sum(len(domain_cookies) for domain_cookies in self._cookies.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cookie jar to dictionary."""
        return {
            "cookies": {
                domain: {
                    name: {
                        "name": cookie.name,
                        "value": cookie.value,
                        "domain": cookie.domain,
                        "path": cookie.path,
                        "secure": cookie.secure,
                        "http_only": cookie.http_only,
                        "same_site": cookie.same_site,
                        "expires": cookie.expires.isoformat() if cookie.expires else None,
                        "max_age": cookie.max_age,
                        "created": cookie.created.isoformat(),
                    }
                    for name, cookie in cookies.items()
                }
                for domain, cookies in self._cookies.items()
            },
            "session_cookies": list(self._session_cookies),
            "total_count": self.get_cookie_count(),
        }


# Utility functions
def create_chrome_cookie_jar() -> CookieJar:
    """Create cookie jar with Chrome-compatible behavior."""
    return CookieJar()


def parse_cookie_header(cookie_header: str) -> Dict[str, str]:
    """Parse Cookie header into name-value pairs."""
    cookies = {}
    if not cookie_header:
        return cookies
    
    for part in cookie_header.split(';'):
        part = part.strip()
        if '=' in part:
            name, value = part.split('=', 1)
            cookies[name.strip()] = value.strip()
    
    return cookies