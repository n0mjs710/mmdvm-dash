"""
Live Log Viewer - Resource Optimized
Minimal processing, color-coded display, memory-constrained operation
"""
from collections import deque
from typing import Deque, Dict, Optional
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


class LogEntry:
    """Lightweight log entry for display"""
    __slots__ = ['timestamp', 'text', 'mode', 'level']
    
    def __init__(self, timestamp: str, text: str, mode: str = 'SYSTEM', level: str = 'INFO'):
        self.timestamp = timestamp
        self.text = text
        self.mode = mode
        self.level = level
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'text': self.text,
            'mode': self.mode,
            'level': self.level
        }


class LiveLogViewer:
    """
    Extremely lightweight live log display
    - Minimal regex processing
    - Fixed-size ring buffer
    - Color coding based on mode detection
    - No complex parsing or state management
    """
    
    # Mode detection patterns - simple and fast
    MODE_PATTERNS = {
        'DMR': re.compile(r'\bDMR(?:\sSlot\s[12])?\b', re.IGNORECASE),
        'DSTAR': re.compile(r'\bD-?Star\b', re.IGNORECASE),
        'YSF': re.compile(r'\b(?:YSF|System\s+Fusion)\b', re.IGNORECASE),
        'P25': re.compile(r'\bP25\b', re.IGNORECASE),
        'NXDN': re.compile(r'\bNXDN\b', re.IGNORECASE),
        'FM': re.compile(r'\bFM\b', re.IGNORECASE),
        'POCSAG': re.compile(r'\bPOCSAG\b', re.IGNORECASE),
    }
    
    # Level detection
    LEVEL_PATTERNS = {
        'ERROR': re.compile(r'\b(?:ERROR|FATAL|FAIL)\b', re.IGNORECASE),
        'WARN': re.compile(r'\b(?:WARN|WARNING)\b', re.IGNORECASE),
        'INFO': re.compile(r'\b(?:INFO|received|transmission|connected)\b', re.IGNORECASE),
    }
    
    def __init__(self, max_lines: int = 500):
        """
        Args:
            max_lines: Maximum lines to keep in memory (default 500 = ~50KB)
        """
        self.buffer: Deque[LogEntry] = deque(maxlen=max_lines)
        self.max_lines = max_lines
    
    def add_line(self, line: str, source: str = 'MMDVM'):
        """
        Add a raw log line with minimal processing
        Args:
            line: Raw log line
            source: Log source (MMDVM, DMRGateway, etc.)
        """
        if not line or len(line.strip()) == 0:
            return
        
        # Extract timestamp (if present)
        timestamp = self._extract_timestamp(line)
        
        # Detect mode
        mode = self._detect_mode(line, source)
        
        # Detect level
        level = self._detect_level(line)
        
        # Create entry
        entry = LogEntry(
            timestamp=timestamp,
            text=line.strip(),
            mode=mode,
            level=level
        )
        
        # Add to ring buffer (automatically drops oldest when full)
        self.buffer.append(entry)
    
    def _extract_timestamp(self, line: str) -> str:
        """Extract timestamp if present, otherwise use current time"""
        # Common formats:
        # M: 2025-01-15 12:34:56.789
        # I: 2025-01-15 12:34:56
        match = re.match(r'^[MDIE]:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
        if match:
            return match.group(1)
        
        # Fall back to current time
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _detect_mode(self, line: str, source: str) -> str:
        """Detect digital mode from line content"""
        # Check each mode pattern
        for mode, pattern in self.MODE_PATTERNS.items():
            if pattern.search(line):
                return mode
        
        # Fall back to source
        if 'DMRGateway' in source:
            return 'DMR'
        elif 'YSFGateway' in source:
            return 'YSF'
        elif 'P25Gateway' in source:
            return 'P25'
        elif 'NXDNGateway' in source:
            return 'NXDN'
        
        return 'SYSTEM'
    
    def _detect_level(self, line: str) -> str:
        """Detect log level"""
        # Check in order of severity
        if self.LEVEL_PATTERNS['ERROR'].search(line):
            return 'ERROR'
        elif self.LEVEL_PATTERNS['WARN'].search(line):
            return 'WARN'
        
        return 'INFO'
    
    def get_recent_lines(self, count: int = 100) -> list:
        """
        Get the most recent N lines
        Args:
            count: Number of lines to return
        Returns:
            List of log entry dictionaries
        """
        # Return most recent entries
        entries = list(self.buffer)[-count:]
        return [entry.to_dict() for entry in entries]
    
    def get_all_lines(self) -> list:
        """Get all buffered lines"""
        return [entry.to_dict() for entry in self.buffer]
    
    def clear(self):
        """Clear the buffer"""
        self.buffer.clear()
    
    def get_stats(self) -> Dict:
        """Get buffer statistics"""
        return {
            'total_lines': len(self.buffer),
            'max_lines': self.max_lines,
            'memory_usage_estimate': len(self.buffer) * 200  # ~200 bytes per entry estimate
        }


# Mode color scheme for frontend
MODE_COLORS = {
    'DMR': '#00ff00',      # Green
    'DSTAR': '#00ffff',    # Cyan
    'YSF': '#ffff00',      # Yellow
    'P25': '#ff8800',      # Orange
    'NXDN': '#ff00ff',     # Magenta
    'FM': '#ffffff',       # White
    'POCSAG': '#8888ff',   # Light blue
    'SYSTEM': '#888888',   # Gray
}

# Level colors for frontend
LEVEL_COLORS = {
    'ERROR': '#ff0000',    # Red
    'WARN': '#ffaa00',     # Orange
    'INFO': '#ffffff',     # White
}


def get_color_scheme() -> Dict:
    """Get the complete color scheme for frontend"""
    return {
        'modes': MODE_COLORS,
        'levels': LEVEL_COLORS
    }
