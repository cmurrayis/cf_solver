"""HTTP/2 protocol support and configuration.

Provides HTTP/2 specific functionality for browser emulation
including stream management and header compression.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class HTTP2Setting(Enum):
    """HTTP/2 settings parameters."""
    HEADER_TABLE_SIZE = 0x1
    ENABLE_PUSH = 0x2
    MAX_CONCURRENT_STREAMS = 0x3
    INITIAL_WINDOW_SIZE = 0x4
    MAX_FRAME_SIZE = 0x5
    MAX_HEADER_LIST_SIZE = 0x6


@dataclass
class HTTP2Settings:
    """HTTP/2 connection settings."""
    header_table_size: int = 65536
    enable_push: bool = True
    max_concurrent_streams: int = 1000
    initial_window_size: int = 6291456
    max_frame_size: int = 16384
    max_header_list_size: int = 262144

    def to_wire_format(self) -> Dict[int, int]:
        """Convert settings to wire format."""
        return {
            HTTP2Setting.HEADER_TABLE_SIZE.value: self.header_table_size,
            HTTP2Setting.ENABLE_PUSH.value: int(self.enable_push),
            HTTP2Setting.MAX_CONCURRENT_STREAMS.value: self.max_concurrent_streams,
            HTTP2Setting.INITIAL_WINDOW_SIZE.value: self.initial_window_size,
            HTTP2Setting.MAX_FRAME_SIZE.value: self.max_frame_size,
            HTTP2Setting.MAX_HEADER_LIST_SIZE.value: self.max_header_list_size,
        }


@dataclass
class HTTP2Configuration:
    """Configuration for HTTP/2 connections."""
    # Connection settings
    settings: HTTP2Settings = field(default_factory=HTTP2Settings)
    
    # Priority settings
    enable_priority: bool = True
    default_weight: int = 16
    
    # Window update behavior
    connection_window_size: int = 15663105
    auto_window_update: bool = True
    
    # Server push handling
    handle_push_promises: bool = False
    max_push_streams: int = 100
    
    # Header compression
    dynamic_table_size: int = 4096
    huffman_encoding: bool = True


class HTTP2HeaderCompressor:
    """HPACK header compression for HTTP/2."""
    
    def __init__(self, table_size: int = 4096):
        self.table_size = table_size
        self.dynamic_table: List[tuple[str, str]] = []
        self.static_table = self._build_static_table()
    
    def _build_static_table(self) -> Dict[int, tuple[str, str]]:
        """Build HPACK static table."""
        # Simplified static table - real implementation would have full table
        return {
            1: (":authority", ""),
            2: (":method", "GET"),
            3: (":method", "POST"),
            4: (":path", "/"),
            5: (":path", "/index.html"),
            6: (":scheme", "http"),
            7: (":scheme", "https"),
            8: (":status", "200"),
            9: (":status", "204"),
            10: (":status", "206"),
            # ... more entries would follow
        }
    
    def compress_headers(self, headers: Dict[str, str]) -> bytes:
        """Compress headers using HPACK."""
        # Simplified compression - real implementation would follow RFC 7541
        compressed = b""
        
        for name, value in headers.items():
            name_lower = name.lower()
            
            # Check static table
            found_index = None
            for index, (static_name, static_value) in self.static_table.items():
                if static_name == name_lower:
                    if static_value == value:
                        # Indexed header field
                        compressed += self._encode_integer(index, 7, 0x80)
                        found_index = index
                        break
                    else:
                        # Literal with incremental indexing
                        compressed += self._encode_integer(index, 6, 0x40)
                        compressed += self._encode_string(value)
                        break
            
            if found_index is None:
                # Literal with incremental indexing - new name
                compressed += b"\x40"  # Pattern 01
                compressed += self._encode_string(name_lower)
                compressed += self._encode_string(value)
                
                # Add to dynamic table
                self.dynamic_table.append((name_lower, value))
                if len(self.dynamic_table) > 100:  # Simplified table management
                    self.dynamic_table.pop(0)
        
        return compressed
    
    def _encode_integer(self, value: int, prefix_bits: int, prefix_pattern: int) -> bytes:
        """Encode integer with specified prefix."""
        max_prefix = (1 << prefix_bits) - 1
        
        if value < max_prefix:
            return bytes([prefix_pattern | value])
        else:
            result = bytes([prefix_pattern | max_prefix])
            value -= max_prefix
            while value >= 128:
                result += bytes([128 | (value & 127)])
                value >>= 7
            result += bytes([value])
            return result
    
    def _encode_string(self, value: str, huffman: bool = True) -> bytes:
        """Encode string with optional Huffman coding."""
        if huffman:
            # Simplified - real implementation would use Huffman coding
            encoded = value.encode('utf-8')
            return self._encode_integer(len(encoded), 7, 0x80) + encoded
        else:
            encoded = value.encode('utf-8')
            return self._encode_integer(len(encoded), 7, 0x00) + encoded


class HTTP2PriorityManager:
    """Manages HTTP/2 stream priorities."""
    
    def __init__(self):
        self.stream_priorities: Dict[int, Dict[str, Any]] = {}
        self.dependency_tree: Dict[int, List[int]] = {}
    
    def set_priority(self, stream_id: int, depends_on: int = 0,
                    weight: int = 16, exclusive: bool = False) -> None:
        """Set priority for a stream."""
        self.stream_priorities[stream_id] = {
            "depends_on": depends_on,
            "weight": weight,
            "exclusive": exclusive
        }
        
        if depends_on not in self.dependency_tree:
            self.dependency_tree[depends_on] = []
        
        if exclusive:
            # Move existing children to depend on this stream
            existing_children = self.dependency_tree[depends_on].copy()
            self.dependency_tree[depends_on] = [stream_id]
            self.dependency_tree[stream_id] = existing_children
        else:
            self.dependency_tree[depends_on].append(stream_id)
    
    def get_chrome_priorities(self) -> Dict[str, Dict[str, Any]]:
        """Get Chrome-like priority configuration."""
        return {
            "main_resource": {"weight": 256, "depends_on": 0, "exclusive": False},
            "stylesheet": {"weight": 256, "depends_on": 0, "exclusive": False},
            "script": {"weight": 256, "depends_on": 0, "exclusive": False},
            "image": {"weight": 8, "depends_on": 0, "exclusive": False},
            "font": {"weight": 256, "depends_on": 0, "exclusive": False},
            "xhr": {"weight": 256, "depends_on": 0, "exclusive": False},
        }


class HTTP2StreamManager:
    """Manages HTTP/2 streams and flow control."""
    
    def __init__(self, config: HTTP2Configuration):
        self.config = config
        self.streams: Dict[int, Dict[str, Any]] = {}
        self.next_stream_id = 1
        self.connection_window = config.connection_window_size
        
    def create_stream(self, headers: Dict[str, str],
                     priority: Optional[Dict[str, Any]] = None) -> int:
        """Create a new HTTP/2 stream."""
        stream_id = self.next_stream_id
        self.next_stream_id += 2  # Client streams are odd
        
        self.streams[stream_id] = {
            "id": stream_id,
            "state": "idle",
            "headers": headers,
            "window_size": self.config.settings.initial_window_size,
            "priority": priority or {"weight": 16, "depends_on": 0},
            "data_sent": 0,
            "data_received": 0,
        }
        
        return stream_id
    
    def update_window(self, stream_id: int, delta: int) -> None:
        """Update stream window size."""
        if stream_id in self.streams:
            self.streams[stream_id]["window_size"] += delta
        
        if stream_id == 0:  # Connection window
            self.connection_window += delta
    
    def can_send_data(self, stream_id: int, size: int) -> bool:
        """Check if data can be sent on stream."""
        if stream_id not in self.streams:
            return False
        
        stream_window = self.streams[stream_id]["window_size"]
        return stream_window >= size and self.connection_window >= size
    
    def get_stream_info(self, stream_id: int) -> Optional[Dict[str, Any]]:
        """Get stream information."""
        return self.streams.get(stream_id)


def create_chrome_http2_config() -> HTTP2Configuration:
    """Create HTTP/2 configuration that matches Chrome behavior."""
    settings = HTTP2Settings(
        header_table_size=65536,
        enable_push=False,  # Chrome typically disables push
        max_concurrent_streams=1000,
        initial_window_size=6291456,
        max_frame_size=16384,
        max_header_list_size=262144,
    )
    
    return HTTP2Configuration(
        settings=settings,
        enable_priority=True,
        connection_window_size=15663105,
        auto_window_update=True,
        handle_push_promises=False,
        dynamic_table_size=4096,
        huffman_encoding=True,
    )


def get_chrome_http2_headers() -> Dict[str, str]:
    """Get HTTP/2 pseudo-headers in Chrome order."""
    return {
        ":method": "GET",
        ":authority": "",  # Will be set per request
        ":scheme": "https",
        ":path": "/",  # Will be set per request
    }


def encode_http2_priority_frame(stream_id: int, depends_on: int = 0,
                               weight: int = 15, exclusive: bool = False) -> bytes:
    """Encode HTTP/2 PRIORITY frame."""
    # Frame header (9 bytes) + priority data (5 bytes)
    frame_length = 5
    frame_type = 0x2  # PRIORITY
    flags = 0x0
    
    # Frame header
    frame = frame_length.to_bytes(3, 'big')
    frame += frame_type.to_bytes(1, 'big')
    frame += flags.to_bytes(1, 'big')
    frame += stream_id.to_bytes(4, 'big')
    
    # Priority data
    if exclusive:
        depends_on |= 0x80000000
    
    frame += depends_on.to_bytes(4, 'big')
    frame += weight.to_bytes(1, 'big')
    
    return frame


# HTTP/2 constants for Chrome emulation
CHROME_HTTP2_SETTINGS = {
    "HEADER_TABLE_SIZE": 65536,
    "ENABLE_PUSH": 0,
    "MAX_CONCURRENT_STREAMS": 1000,
    "INITIAL_WINDOW_SIZE": 6291456,
    "MAX_FRAME_SIZE": 16384,
    "MAX_HEADER_LIST_SIZE": 262144,
}

CHROME_WINDOW_UPDATE_SIZE = 15663105