"""
LCDproc Virtual Display Client for MMDVMHost

Connects to MMDVMHost's LCDproc TCP port (default 13666) and maintains
a virtual display buffer that mirrors what would appear on a physical LCD.

This provides real-time structured data that's difficult to parse from logs:
- Current mode and transmission details
- Active callsigns and talkgroups
- Transmission timers and RSSI
- Network/reflector information

Reference: MMDVMHost_LCDproc_API.md
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LCDWidget:
    """Represents a text widget on the virtual LCD"""
    type: str = 'string'
    x: int = 1
    y: int = 1
    text: str = ''


@dataclass
class LCDScreen:
    """Represents a logical screen with widgets"""
    name: str = ''
    priority: int = 5
    widgets: Dict[str, LCDWidget] = field(default_factory=dict)


class LCDprocClient:
    """
    Virtual LCDproc display server that MMDVMHost connects to.
    
    Implements the LCDproc protocol to receive and parse display updates
    from MMDVMHost, providing structured real-time data.
    """
    
    def __init__(self, host: str = '127.0.0.1', port: int = 13666):
        self.host = host
        self.port = port
        self.width = 20  # Standard LCD width
        self.height = 4  # Standard LCD height
        
        # State
        self.screens: Dict[str, LCDScreen] = {}
        self.active_screen: Optional[str] = None
        self.client_name: str = ''
        
        # Connection
        self.server: Optional[asyncio.Server] = None
        self.client_writer: Optional[asyncio.StreamWriter] = None
        self.running = False
        
        # Callbacks for state changes
        self.on_update: Optional[Callable[[List[str]], None]] = None
    
    async def start(self):
        """Start the LCDproc server"""
        try:
            logger.info(f"Starting LCDproc server on {self.host}:{self.port}...")
            self.server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port,
                reuse_address=True
            )
            self.running = True
            
            addr = self.server.sockets[0].getsockname()
            logger.info(f"LCDproc server created, bound to {addr[0]}:{addr[1]}")
            
            # Start serving in background
            logger.info("Starting server to accept connections...")
            async def serve():
                async with self.server:
                    await self.server.serve_forever()
            
            asyncio.create_task(serve())
            logger.info(f"LCDproc virtual display is now accepting connections on {addr[0]}:{addr[1]}")
            logger.info(f"Configure MMDVMHost MMDVM.ini [LCDproc] Address={addr[0]} Port={addr[1]}")
        except Exception as e:
            logger.error(f"Failed to start LCDproc server: {e}", exc_info=True)
            raise
    
    async def stop(self):
        """Stop the LCDproc server"""
        self.running = False
        
        if self.client_writer:
            try:
                self.client_writer.close()
                await self.client_writer.wait_closed()
            except Exception as e:
                logger.debug(f"Error closing client: {e}")
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("LCDproc virtual display stopped")
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a client connection (MMDVMHost)"""
        addr = writer.get_extra_info('peername')
        logger.info(f"LCDproc client connected from {addr}")
        
        self.client_writer = writer
        
        try:
            # Don't send greeting immediately - wait for client to send "hello" first
            logger.debug(f"Waiting for hello from {addr}")
            
            # Process commands - LCDproc uses null-terminated strings
            buffer = b''
            while self.running:
                try:
                    # Read data in chunks
                    chunk = await asyncio.wait_for(reader.read(1024), timeout=60.0)
                    if not chunk:
                        logger.info("Client closed connection (no data)")
                        break
                    
                    logger.info(f"Received {len(chunk)} bytes: {chunk[:100].hex()}")  # Log first 100 bytes
                    buffer += chunk
                    
                    # Process all complete commands (null-terminated)
                    while b'\x00' in buffer:
                        command_bytes, buffer = buffer.split(b'\x00', 1)
                        
                        # Decode command
                        try:
                            command = command_bytes.decode('utf-8', errors='ignore').strip()
                        except Exception as e:
                            logger.warning(f"Could not decode command: {command_bytes.hex()}")
                            continue
                        
                        if not command:
                            logger.info("Empty command after decode")
                            continue
                        
                        logger.info(f"Received command: {command}")
                        response = self._process_command(command)
                        logger.info(f"Response: {response}")
                        
                        # Send response with null terminator (LCDproc protocol)
                        writer.write(f"{response}\x00".encode('utf-8'))
                        await writer.drain()
                    
                except asyncio.TimeoutError:
                    # Send keepalive check
                    continue
                except Exception as e:
                    logger.error(f"Error processing command: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Client handler error: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            self.client_writer = None
            logger.info(f"LCDproc client {addr} disconnected")
    
    def _process_command(self, command: str) -> str:
        """Process a single LCDproc command and return response"""
        
        # hello - respond with connect string
        if command == 'hello':
            return f'connect LCDproc 0.5.9 protocol 0.3.1 lcd wid {self.width} hgt {self.height} cellwid 5 cellhgt 8'
        
        # bye
        elif command == 'bye':
            return 'success'
        
        # noop (keepalive)
        elif command == 'noop':
            return 'success'
        
        # client_set name <NAME>
        elif command.startswith('client_set name '):
            self.client_name = command[16:]
            logger.debug(f"Client name: {self.client_name}")
            return 'success'
        
        # screen_add <SCR>
        elif command.startswith('screen_add '):
            screen_id = command[11:]
            self.screens[screen_id] = LCDScreen()
            if not self.active_screen:
                self.active_screen = screen_id
            logger.debug(f"Screen added: {screen_id}")
            return 'success'
        
        # screen_set <SCR> [flags...]
        elif command.startswith('screen_set '):
            parts = command.split()
            if len(parts) >= 2:
                screen_id = parts[1]
                if screen_id in self.screens:
                    # Parse flags (-name "MMDVM", -priority 1, etc.)
                    if '-name' in parts:
                        idx = parts.index('-name')
                        if idx + 1 < len(parts):
                            name = parts[idx + 1].strip('"')
                            self.screens[screen_id].name = name
                    if '-priority' in parts:
                        idx = parts.index('-priority')
                        if idx + 1 < len(parts):
                            try:
                                self.screens[screen_id].priority = int(parts[idx + 1])
                            except ValueError:
                                pass
                    logger.debug(f"Screen updated: {screen_id}")
            return 'success'
        
        # screen_del <SCR>
        elif command.startswith('screen_del '):
            screen_id = command[11:]
            if screen_id in self.screens:
                del self.screens[screen_id]
                if self.active_screen == screen_id:
                    self.active_screen = next(iter(self.screens.keys()), None)
                logger.debug(f"Screen deleted: {screen_id}")
            return 'success'
        
        # widget_add <SCR> <WID> string
        elif command.startswith('widget_add '):
            match = re.match(r'widget_add (\S+) (\S+) (\S+)', command)
            if match:
                screen_id, widget_id, widget_type = match.groups()
                if screen_id in self.screens:
                    self.screens[screen_id].widgets[widget_id] = LCDWidget(type=widget_type)
                    logger.debug(f"Widget added: {screen_id}.{widget_id} ({widget_type})")
            return 'success'
        
        # widget_set <SCR> <WID> <X> <Y> "<TEXT>"
        # MMDVMHost sends: widget_set Status Time 2147483644 0 "10:57:39 AM"
        # Format appears to be: screen widget left top "text"
        # The large left value (2147483644) seems to be max_int, use 1 for leftmost position
        elif command.startswith('widget_set '):
            # Try format with 5 params first (screen, widget, left, top, text)
            match = re.match(r'widget_set (\S+) (\S+) (\d+) (\d+) "(.*)"', command)
            if match:
                screen_id, widget_id, x_param, y, text = match.groups()
                
                # Auto-create screen if it doesn't exist
                if screen_id not in self.screens:
                    logger.info(f"Auto-creating screen '{screen_id}' from widget_set")
                    self.screens[screen_id] = LCDScreen()
                    if not self.active_screen:
                        self.active_screen = screen_id
                
                # Auto-create widget if it doesn't exist
                if widget_id not in self.screens[screen_id].widgets:
                    logger.info(f"Auto-creating widget '{widget_id}' in screen '{screen_id}'")
                    self.screens[screen_id].widgets[widget_id] = LCDWidget(type='string')
                
                widget = self.screens[screen_id].widgets[widget_id]
                # If X is very large (like max_int), default to 1 (leftmost)
                x_val = int(x_param)
                widget.x = 1 if x_val > self.width else x_val
                widget.y = int(y) + 1  # Convert 0-based to 1-based
                widget.text = text
                logger.info(f"Widget updated: {screen_id}.{widget_id} at ({widget.x},{widget.y}) = '{text}'")
                
                # Trigger display update callback
                self._notify_update()
            else:
                logger.warning(f"Could not parse widget_set command: {command}")
            return 'success'
        
        # widget_del <SCR> <WID>
        elif command.startswith('widget_del '):
            match = re.match(r'widget_del (\S+) (\S+)', command)
            if match:
                screen_id, widget_id = match.groups()
                if screen_id in self.screens and widget_id in self.screens[screen_id].widgets:
                    del self.screens[screen_id].widgets[widget_id]
                    logger.debug(f"Widget deleted: {screen_id}.{widget_id}")
            return 'success'
        
        # Unknown command
        else:
            logger.debug(f"Unknown command: {command}")
            return 'huh?'
    
    def _notify_update(self):
        """Notify callback of display update"""
        if self.on_update:
            lines = self.get_display_lines()
            try:
                self.on_update(lines)
            except Exception as e:
                logger.error(f"Error in update callback: {e}")
    
    def get_display_lines(self) -> List[str]:
        """
        Render the current active screen as a list of text lines.
        
        Returns:
            List of strings representing each line of the display.
            Lines are padded/truncated to exactly self.width characters.
        """
        if not self.active_screen or self.active_screen not in self.screens:
            return [' ' * self.width] * self.height
        
        screen = self.screens[self.active_screen]
        
        # Initialize empty display buffer
        lines = [' ' * self.width for _ in range(self.height)]
        
        # Render each widget into the buffer
        for widget in screen.widgets.values():
            if widget.type == 'string' and 1 <= widget.y <= self.height:
                line_idx = widget.y - 1  # Convert to 0-based
                x_pos = widget.x - 1  # Convert to 0-based
                
                # Truncate text to fit within line width
                text = widget.text[:self.width - x_pos] if x_pos < self.width else ''
                
                # Build new line with widget text inserted
                line = list(lines[line_idx])
                for i, char in enumerate(text):
                    if x_pos + i < self.width:
                        line[x_pos + i] = char
                lines[line_idx] = ''.join(line)
        
        return lines
    
    def get_state(self) -> dict:
        """
        Get the complete state of the virtual display.
        
        Returns:
            Dictionary with screens, active_screen, and rendered display lines.
        """
        return {
            'client_name': self.client_name,
            'active_screen': self.active_screen,
            'display_size': {'width': self.width, 'height': self.height},
            'screens': {
                screen_id: {
                    'name': screen.name,
                    'priority': screen.priority,
                    'widgets': {
                        wid: {
                            'type': w.type,
                            'x': w.x,
                            'y': w.y,
                            'text': w.text
                        }
                        for wid, w in screen.widgets.items()
                    }
                }
                for screen_id, screen in self.screens.items()
            },
            'display_lines': self.get_display_lines()
        }
