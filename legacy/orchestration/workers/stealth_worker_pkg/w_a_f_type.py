
"""
stealth_worker_pkg/w_a_f_type.py — WAFType
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class WAFType(Enum):
    """Known WAF providers."""
    CLOUDFLARE = "cloudflare"
    AKAMAI = "akamai"
    PERIMETERX = "perimeterx"
    DATADOME = "datadome"
    KASADA = "kasada"
    IMPERVA = "imperva"
    SUCURI = "sucuri"
    AWS_WAF = "aws_waf"
    UNKNOWN = "unknown"




