"""Challenge parser utilities for Cloudflare challenges.

Provides comprehensive parsing utilities for extracting challenge data,
JavaScript code, form parameters, and other challenge-related information
from HTML responses.
"""

import re
import json
import base64
from typing import Dict, List, Optional, Any, Union, Tuple, NamedTuple
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin, parse_qs
from html.parser import HTMLParser
import html


class FormField(NamedTuple):
    """Represents a form field."""
    name: str
    value: str
    field_type: str = "text"


class ParsedScript(NamedTuple):
    """Represents a parsed script element."""
    content: str
    src: Optional[str] = None
    script_type: str = "text/javascript"
    attributes: Dict[str, str] = {}


@dataclass
class ParsedForm:
    """Represents a parsed HTML form."""
    action: str
    method: str = "POST"
    fields: List[FormField] = None
    form_id: Optional[str] = None
    form_class: Optional[str] = None

    def __post_init__(self):
        if self.fields is None:
            self.fields = []

    def to_form_data(self) -> Dict[str, str]:
        """Convert to form data dictionary."""
        return {field.name: field.value for field in self.fields}


@dataclass
class ChallengeMetadata:
    """Metadata extracted from challenge response."""
    challenge_id: Optional[str] = None
    site_key: Optional[str] = None
    ray_id: Optional[str] = None
    challenge_ts: Optional[str] = None
    h_captcha_site_key: Optional[str] = None
    turnstile_site_key: Optional[str] = None
    cf_chl_rt_tk: Optional[str] = None
    cf_chl_seq_nb: Optional[str] = None
    cf_chl_prog: Optional[str] = None


class ChallengeFormParser(HTMLParser):
    """HTML parser specialized for Cloudflare challenge forms."""

    def __init__(self):
        super().__init__()
        self.forms = []
        self.current_form = None
        self.current_input = None
        self.in_script = False
        self.scripts = []
        self.current_script = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        attr_dict = dict(attrs)

        if tag == "form":
            self.current_form = ParsedForm(
                action=attr_dict.get("action", ""),
                method=attr_dict.get("method", "POST").upper(),
                form_id=attr_dict.get("id"),
                form_class=attr_dict.get("class"),
                fields=[]
            )

        elif tag == "input" and self.current_form is not None:
            field = FormField(
                name=attr_dict.get("name", ""),
                value=attr_dict.get("value", ""),
                field_type=attr_dict.get("type", "text")
            )
            self.current_form.fields.append(field)

        elif tag == "script":
            self.in_script = True
            self.current_script = ""
            self.script_attrs = attr_dict

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self.current_form is not None:
            self.forms.append(self.current_form)
            self.current_form = None

        elif tag == "script" and self.in_script:
            self.in_script = False
            script = ParsedScript(
                content=self.current_script.strip(),
                src=self.script_attrs.get("src"),
                script_type=self.script_attrs.get("type", "text/javascript"),
                attributes=self.script_attrs
            )
            self.scripts.append(script)
            self.current_script = ""

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self.current_script += data


class ChallengeParser:
    """Comprehensive parser for Cloudflare challenge responses."""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for challenge parsing."""

        # Challenge identification patterns
        self.challenge_patterns = {
            # JavaScript challenge patterns
            "js_challenge": re.compile(
                r'var\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*[^;]+;[\s\S]*?setTimeout\(',
                re.IGNORECASE
            ),
            "challenge_form": re.compile(
                r'<form[^>]*id="challenge-form"[^>]*>[\s\S]*?</form>',
                re.IGNORECASE
            ),

            # Form field patterns
            "jschl_vc": re.compile(
                r'name="jschl_vc"\s+value="([^"]+)"',
                re.IGNORECASE
            ),
            "jschl_answer": re.compile(
                r'name="jschl_answer"[^>]*>',
                re.IGNORECASE
            ),
            "pass_field": re.compile(
                r'name="pass"\s+value="([^"]+)"',
                re.IGNORECASE
            ),
            "s_field": re.compile(
                r'name="s"\s+value="([^"]+)"',
                re.IGNORECASE
            ),

            # Metadata patterns
            "ray_id": re.compile(
                r'data-ray="([^"]+)"',
                re.IGNORECASE
            ),
            "cf_ray": re.compile(
                r'CF-Ray:\s*([^\s]+)',
                re.IGNORECASE
            ),
            "challenge_ts": re.compile(
                r'data-ts="([^"]+)"',
                re.IGNORECASE
            ),

            # Turnstile patterns
            "turnstile_sitekey": re.compile(
                r'data-sitekey="([^"]+)"[^>]*cf-turnstile',
                re.IGNORECASE
            ),
            "turnstile_widget": re.compile(
                r'<div[^>]*class="[^"]*cf-turnstile[^"]*"[^>]*>',
                re.IGNORECASE
            ),

            # hCaptcha patterns
            "hcaptcha_sitekey": re.compile(
                r'data-sitekey="([^"]+)"[^>]*h-captcha',
                re.IGNORECASE
            ),

            # Rate limiting patterns
            "retry_after": re.compile(
                r'Retry-After:\s*(\d+)',
                re.IGNORECASE
            ),
            "rate_limit_msg": re.compile(
                r'rate.?limit|too many requests|please wait',
                re.IGNORECASE
            ),

            # Challenge delay patterns
            "setTimeout_delay": re.compile(
                r'setTimeout\([^,]*,\s*(\d+)\)',
                re.IGNORECASE
            ),
            "challenge_delay": re.compile(
                r'challenge.?delay["\']?\s*:\s*(\d+)',
                re.IGNORECASE
            ),

            # Cloudflare tokens
            "cf_chl_rt_tk": re.compile(
                r'name="cf-chl-rt-tk"\s+value="([^"]+)"',
                re.IGNORECASE
            ),
            "cf_chl_seq_nb": re.compile(
                r'name="cf-chl-seq-nb"\s+value="([^"]+)"',
                re.IGNORECASE
            ),
            "cf_chl_prog": re.compile(
                r'name="cf-chl-prog"\s+value="([^"]+)"',
                re.IGNORECASE
            ),
        }

        # JavaScript extraction patterns
        self.js_patterns = {
            "challenge_script": re.compile(
                r'<script[^>]*>([\s\S]*?var\s+[a-zA-Z_$][a-zA-Z0-9_$]*[\s\S]*?)</script>',
                re.IGNORECASE
            ),
            "inline_js": re.compile(
                r'<script[^>]*>([\s\S]*?)</script>',
                re.IGNORECASE
            ),
            "var_declarations": re.compile(
                r'var\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*([^;]+);',
                re.IGNORECASE
            ),
            "math_operations": re.compile(
                r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*([+\-*/])\s*=\s*([^;]+);',
                re.IGNORECASE
            ),
        }

        # Content type detection patterns
        self.content_patterns = {
            "cloudflare_challenge": re.compile(
                r'checking your browser|cloudflare|challenge',
                re.IGNORECASE
            ),
            "error_pages": re.compile(
                r'error\s*\d+|access denied|forbidden',
                re.IGNORECASE
            ),
            "captcha_content": re.compile(
                r'captcha|turnstile|hcaptcha',
                re.IGNORECASE
            ),
        }

    def parse_challenge_response(self, html_content: str, headers: Dict[str, str],
                                url: str) -> Dict[str, Any]:
        """Parse a complete challenge response."""

        result = {
            "url": url,
            "challenge_detected": False,
            "challenge_type": "none",
            "metadata": self.extract_metadata(html_content, headers),
            "forms": self.extract_forms(html_content),
            "scripts": self.extract_scripts(html_content),
            "javascript_challenge": self.extract_js_challenge(html_content),
            "form_data": {},
            "submit_url": "",
            "delay_ms": self.extract_challenge_delay(html_content),
        }

        # Determine challenge type
        challenge_type = self.detect_challenge_type(html_content, headers)
        result["challenge_type"] = challenge_type
        result["challenge_detected"] = challenge_type != "none"

        # Extract challenge-specific data
        if challenge_type == "javascript":
            js_data = self.extract_javascript_challenge_data(html_content, url)
            result.update(js_data)
        elif challenge_type == "turnstile":
            turnstile_data = self.extract_turnstile_data(html_content, url)
            result.update(turnstile_data)
        elif challenge_type == "hcaptcha":
            hcaptcha_data = self.extract_hcaptcha_data(html_content, url)
            result.update(hcaptcha_data)

        return result

    def extract_metadata(self, html_content: str, headers: Dict[str, str]) -> ChallengeMetadata:
        """Extract challenge metadata."""
        metadata = ChallengeMetadata()

        # Extract from HTML
        for field_name, pattern in self.challenge_patterns.items():
            if field_name in ["ray_id", "challenge_ts", "turnstile_sitekey",
                            "hcaptcha_sitekey", "cf_chl_rt_tk", "cf_chl_seq_nb", "cf_chl_prog"]:
                match = pattern.search(html_content)
                if match:
                    setattr(metadata, field_name, match.group(1))

        # Extract from headers
        if headers:
            cf_ray = headers.get("CF-Ray") or headers.get("cf-ray")
            if cf_ray:
                metadata.ray_id = cf_ray

        return metadata

    def extract_forms(self, html_content: str) -> List[ParsedForm]:
        """Extract all forms from HTML content."""
        parser = ChallengeFormParser()
        try:
            parser.feed(html_content)
            return parser.forms
        except Exception:
            # Fallback to regex parsing
            return self._extract_forms_regex(html_content)

    def _extract_forms_regex(self, html_content: str) -> List[ParsedForm]:
        """Fallback form extraction using regex."""
        forms = []

        form_pattern = re.compile(
            r'<form[^>]*action="([^"]*)"[^>]*>([\s\S]*?)</form>',
            re.IGNORECASE
        )

        for form_match in form_pattern.finditer(html_content):
            action = form_match.group(1)
            form_content = form_match.group(2)

            # Extract input fields
            fields = []
            input_pattern = re.compile(
                r'<input[^>]*name="([^"]*)"[^>]*value="([^"]*)"[^>]*>',
                re.IGNORECASE
            )

            for input_match in input_pattern.finditer(form_content):
                field = FormField(
                    name=input_match.group(1),
                    value=html.unescape(input_match.group(2))
                )
                fields.append(field)

            form = ParsedForm(action=action, fields=fields)
            forms.append(form)

        return forms

    def extract_scripts(self, html_content: str) -> List[ParsedScript]:
        """Extract all script elements."""
        parser = ChallengeFormParser()
        try:
            parser.feed(html_content)
            return parser.scripts
        except Exception:
            # Fallback to regex parsing
            return self._extract_scripts_regex(html_content)

    def _extract_scripts_regex(self, html_content: str) -> List[ParsedScript]:
        """Fallback script extraction using regex."""
        scripts = []

        for match in self.js_patterns["inline_js"].finditer(html_content):
            script = ParsedScript(content=match.group(1).strip())
            scripts.append(script)

        return scripts

    def extract_js_challenge(self, html_content: str) -> Optional[str]:
        """Extract JavaScript challenge code."""

        # Look for challenge script patterns
        for pattern in [self.js_patterns["challenge_script"], self.js_patterns["inline_js"]]:
            for match in pattern.finditer(html_content):
                js_code = match.group(1)
                if self._is_challenge_javascript(js_code):
                    return js_code

        return None

    def _is_challenge_javascript(self, js_code: str) -> bool:
        """Check if JavaScript code is challenge-related."""
        challenge_indicators = [
            "jschl_answer", "challenge-form", "setTimeout",
            "document.getElementById", "location.href"
        ]

        js_lower = js_code.lower()
        return any(indicator.lower() in js_lower for indicator in challenge_indicators)

    def extract_challenge_delay(self, html_content: str) -> int:
        """Extract challenge delay in milliseconds."""

        # Try setTimeout pattern
        match = self.challenge_patterns["setTimeout_delay"].search(html_content)
        if match:
            return int(match.group(1))

        # Try challenge delay pattern
        match = self.challenge_patterns["challenge_delay"].search(html_content)
        if match:
            return int(match.group(1))

        # Default delay (4 seconds)
        return 4000

    def detect_challenge_type(self, html_content: str, headers: Dict[str, str]) -> str:
        """Detect the type of challenge present."""

        html_lower = html_content.lower()

        # Check for Turnstile
        if "cf-turnstile" in html_lower or self.challenge_patterns["turnstile_widget"].search(html_content):
            return "turnstile"

        # Check for hCaptcha
        if "h-captcha" in html_lower or self.challenge_patterns["hcaptcha_sitekey"].search(html_content):
            return "hcaptcha"

        # Check for JavaScript challenge
        if self.challenge_patterns["js_challenge"].search(html_content):
            return "javascript"

        # Check for rate limiting
        if (self.challenge_patterns["rate_limit_msg"].search(html_content) or
            headers.get("Retry-After") or headers.get("retry-after")):
            return "rate_limited"

        # Check for managed challenge
        if "managed challenge" in html_lower or "browser integrity check" in html_lower:
            return "managed"

        return "none"

    def extract_javascript_challenge_data(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract JavaScript challenge specific data."""

        data = {
            "form_data": {},
            "submit_url": "",
            "javascript_code": "",
        }

        # Extract form fields
        for field_name in ["jschl_vc", "pass_field", "s_field"]:
            pattern = self.challenge_patterns[field_name]
            match = pattern.search(html_content)
            if match:
                if field_name == "jschl_vc":
                    data["form_data"]["jschl_vc"] = match.group(1)
                elif field_name == "pass_field":
                    data["form_data"]["pass"] = match.group(1)
                elif field_name == "s_field":
                    data["form_data"]["s"] = match.group(1)

        # Extract submit URL from form
        forms = self.extract_forms(html_content)
        for form in forms:
            if any(field.name == "jschl_vc" for field in form.fields):
                data["submit_url"] = urljoin(url, form.action)
                break

        # Extract JavaScript code
        js_code = self.extract_js_challenge(html_content)
        if js_code:
            data["javascript_code"] = js_code

        return data

    def extract_turnstile_data(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract Turnstile challenge data."""

        data = {
            "turnstile_sitekey": "",
            "callback_url": url,
        }

        # Extract site key
        match = self.challenge_patterns["turnstile_sitekey"].search(html_content)
        if match:
            data["turnstile_sitekey"] = match.group(1)

        return data

    def extract_hcaptcha_data(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract hCaptcha challenge data."""

        data = {
            "hcaptcha_sitekey": "",
            "callback_url": url,
        }

        # Extract site key
        match = self.challenge_patterns["hcaptcha_sitekey"].search(html_content)
        if match:
            data["hcaptcha_sitekey"] = match.group(1)

        return data

    def parse_javascript_variables(self, js_code: str) -> Dict[str, Any]:
        """Parse JavaScript variables from challenge code."""

        variables = {}

        # Extract variable declarations
        for match in self.js_patterns["var_declarations"].finditer(js_code):
            var_name = match.group(1)
            var_value = match.group(2).strip()

            # Try to evaluate simple values
            try:
                if var_value.startswith('"') and var_value.endswith('"'):
                    variables[var_name] = var_value[1:-1]
                elif var_value.startswith("'") and var_value.endswith("'"):
                    variables[var_name] = var_value[1:-1]
                elif var_value.isdigit():
                    variables[var_name] = int(var_value)
                elif var_value.replace('.', '').isdigit():
                    variables[var_name] = float(var_value)
                else:
                    variables[var_name] = var_value
            except (ValueError, IndexError):
                variables[var_name] = var_value

        return variables

    def clean_javascript_code(self, js_code: str) -> str:
        """Clean and prepare JavaScript code for execution."""

        # Remove HTML entities
        js_code = html.unescape(js_code)

        # Remove comments
        js_code = re.sub(r'//[^\n]*', '', js_code)
        js_code = re.sub(r'/\*.*?\*/', '', js_code, flags=re.DOTALL)

        # Remove setTimeout and DOM manipulation
        js_code = re.sub(r'setTimeout\([^}]*\}[^}]*\}[^;]*;', '', js_code)
        js_code = re.sub(r'document\.[^;]*;', '', js_code)
        js_code = re.sub(r'location\.[^;]*;', '', js_code)
        js_code = re.sub(r'window\.[^;]*;', '', js_code)

        # Clean whitespace
        js_code = re.sub(r'\s+', ' ', js_code).strip()

        return js_code


# Utility functions
def create_challenge_parser() -> ChallengeParser:
    """Create a new challenge parser instance."""
    return ChallengeParser()


def parse_challenge_response(html_content: str, headers: Dict[str, str] = None,
                           url: str = "") -> Dict[str, Any]:
    """Quick function to parse challenge response."""
    parser = ChallengeParser()
    return parser.parse_challenge_response(html_content, headers or {}, url)


def extract_form_data(html_content: str) -> Dict[str, str]:
    """Quick function to extract form data."""
    parser = ChallengeParser()
    forms = parser.extract_forms(html_content)

    if forms:
        return forms[0].to_form_data()

    return {}


def detect_challenge_type(html_content: str, headers: Dict[str, str] = None) -> str:
    """Quick function to detect challenge type."""
    parser = ChallengeParser()
    return parser.detect_challenge_type(html_content, headers or {})