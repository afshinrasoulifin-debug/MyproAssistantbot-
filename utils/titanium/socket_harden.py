
"""
utils/titanium/socket_harden.py — Socket-level TCP/IP Fingerprint Hardening
═══════════════════════════════════════════════════════════════════════════
Manipulates low-level socket options (TCP_WINDOW_CLAMP, TCP_MAXSEG) to 
match real browser OS signatures. Critical for Akamai/Cloudflare L4 detection.
"""

import socket
import logging
from arki_project.exceptions import ArkiBaseError

logger = logging.getLogger("arki.titanium.socket")

class SocketHardener:
    """
    Hardens raw sockets to match specific OS TCP/IP fingerprints.
    """
    
    @staticmethod
    def harden_socket(sock: socket.socket, os_type: str = "windows") -> None:
        """
        Apply TCP-level options to the socket.
        Note: Some options require elevated privileges or specific OS support.
        """
        try:
            # TCP_NODELAY is standard for browsers
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            if os_type.lower() == "windows":
                # Windows 10/11 TCP Window Scale is typically 8 (256)
                # We try to set a large receive buffer to trigger this
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            
            elif os_type.lower() == "macos":
                # macOS has specific TCP behavior
                if hasattr(socket, 'TCP_KEEPALIVE'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, 60)
            
            # TCP_MAXSEG (MSS) - Critical for matching MTU/MSS signatures
            # Typically 1460 for Ethernet (1500 MTU - 40 bytes headers)
            try:
                if hasattr(socket, 'TCP_MAXSEG'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_MAXSEG, 1440)
            except ArkiBaseError:
                pass # Often restricted by kernel
                
            logger.debug("🛡️ Socket hardened for %s fingerprint", os_type)
            
        except ArkiBaseError as e:
            logger.warning("Failed to apply full socket hardening: %s", e)

socket_hardener = SocketHardener()


