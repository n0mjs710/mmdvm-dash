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
            # Send greeting
            greeting = f"connect LCDproc 0.5.9 protocol 0.3.1 lcd wid {self.width} hgt {self.height} cellwid 5 cellhgt 8\n"
            writer.write(greeting.encode('utf-8'))
            await writer.drain()
            
            # Process commands
            while self.running:
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=60.0)
                    if not line:
                        break
                    
                    command = line.decode('utf-8').strip()
                    if not command:
                        continue
                    
                    response = self._process_command(command)
                    writer.write(f"{response}\n".encode('utf-8'))
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
        
        # hello
        if command == 'hello':
            return 'success'
        
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
        elif command.startswith('widget_set '):
            # Parse: widget_set scr1 l1 1 1 "DMR  →  BM 3120"
            match = re.match(r'widget_set (\S+) (\S+) (\d+) (\d+) "(.*)"', command)
            if match:
                screen_id, widget_id, x, y, text = match.groups()
                if screen_id in self.screens:
                    widget = self.screens[screen_id].widgets.get(widget_id)
                    if widget:
                        widget.x = int(x)
                        widget.y = int(y)
                        widget.text = text
                        logger.debug(f"Widget updated: {screen_id}.{widget_id} = '{text}'")
                        
                        # Trigger display update callback
                        self._notify_update()
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
