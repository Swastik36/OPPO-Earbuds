import asyncio
import socket
import logging
from typing import Callable, Optional
from .protocol import OppoFrame, OppoStreamParser
from .exceptions import OppoConnectionError

logger = logging.getLogger("oppo_control.transport")

class OppoRFCOMMTransport:
    def __init__(self, mac_address: str, port: int = 15):
        self.mac_address = mac_address
        self.port = port
        self.sock = None
        self.is_connected = False
        self._read_task = None
        self.trace_mode = False
        self.record_callback: Optional[Callable[[str, bytes], None]] = None

    async def connect(self, on_frame_received: Callable[[OppoFrame], None]):
        loop = asyncio.get_running_loop()
        self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.sock.setblocking(False)
        
        logger.info(f"Connecting to {self.mac_address} on RFCOMM port {self.port}...")
        try:
            await loop.sock_connect(self.sock, (self.mac_address, self.port))
            self.is_connected = True
            logger.info("Connected to RFCOMM socket successfully!")
            self._read_task = asyncio.create_task(self._read_loop(on_frame_received))
        except Exception as e:
            logger.error(f"Failed to connect to RFCOMM socket: {e}")
            if self.sock:
                self.sock.close()
            raise OppoConnectionError(f"Failed to connect to {self.mac_address} on port {self.port}: {e}") from e

    async def send(self, data: bytes):
        if not self.is_connected or not self.sock:
            raise ConnectionError("Transport is not connected")
        if self.trace_mode:
            print(f"TX  {data.hex().upper()}", flush=True)
        logger.debug(f"TX  {data.hex().upper()}")
        if self.record_callback:
            self.record_callback("TX", data)
            
        loop = asyncio.get_running_loop()
        await loop.sock_sendall(self.sock, data)

    async def disconnect(self):
        if not self.is_connected:
            return
        
        logger.info("Disconnecting RFCOMM transport...")
        self.is_connected = False
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None
            
        if self.sock:
            self.sock.close()
            self.sock = None
        logger.info("RFCOMM transport disconnected.")

    async def _read_loop(self, on_frame_received: Callable[[OppoFrame], None]):
        loop = asyncio.get_running_loop()
        parser = OppoStreamParser()
        
        while self.is_connected:
            try:
                data = await loop.sock_recv(self.sock, 1024)
                if not data:
                    logger.warning("RFCOMM socket closed by remote device.")
                    break
                
                for frame in parser.feed(data):
                    frame_bytes = frame.to_bytes()
                    if self.trace_mode:
                        print(f"RX  {frame_bytes.hex().upper()}", flush=True)
                    logger.debug(f"RX  {frame_bytes.hex().upper()}")
                    if self.record_callback:
                        self.record_callback("RX", frame_bytes)
                        
                    on_frame_received(frame)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.is_connected:
                    logger.error(f"Error in RFCOMM read loop: {e}")
                break
                
        self.is_connected = False
        if self.sock:
            self.sock.close()
            self.sock = None
