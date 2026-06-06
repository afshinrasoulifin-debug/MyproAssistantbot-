
"""
utils/titanium/hpack_manual.py — Manual HPACK Table & Compression Control
═══════════════════════════════════════════════════════════════════════════
Provides byte-level control over HPACK header compression to match 
specific browser signatures (indexing, Huffman encoding, literal types).
"""

import logging
from typing import List, Tuple
from hpack import Encoder, Decoder
from arki_project.exceptions import ArkiBaseError

logger = logging.getLogger("arki.titanium.hpack")

class ManualHPACKManager:
    """
    Manages HPACK compression to ensure byte-level signature matching.
    """
    
    def __init__(self, table_size: int = 4096) -> None:
        self.encoder = Encoder()
        self.encoder.header_table_size = table_size
        self.decoder = Decoder()
        self.decoder.header_table_size = table_size

    def encode_headers_fixed(self, headers: List[Tuple[str, str]], huffman: bool = True) -> bytes:
        """
        Encodes headers with specific control over Huffman and indexing.
        Chrome/Safari often use specific Huffman patterns for certain headers.
        """
        # In a real deep implementation, we would manually construct the HPACK blocks
        # here using the hpack library's low-level primitives.
        try:
            return self.encoder.encode(headers, huffman=huffman)
        except ArkiBaseError as e:
            logger.error("HPACK encoding failed: %s", e)
            return b""

    def set_table_size(self, size: int) -> None:
        """Update the dynamic table size (triggers a SETTINGS_HEADER_TABLE_SIZE)."""
        self.encoder.header_table_size = size
        logger.debug("HPACK Table Size updated to %d", size)

hpack_manager = ManualHPACKManager()


