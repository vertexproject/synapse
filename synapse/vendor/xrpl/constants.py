"""Collection of public constants for XRPL."""
from enum import Enum
from re import compile
from typing import Pattern

from typing_extensions import Final


class CryptoAlgorithm(str, Enum):
    """Represents the supported cryptography algorithms."""

    ED25519 = "ed25519"
    SECP256K1 = "secp256k1"


class XRPLException(Exception):
    """Base Exception for XRPL library."""

    pass


ISO_CURRENCY_REGEX: Final[Pattern[str]] = compile("^[A-Z0-9]{3}$")
"""
:meta private:
"""

HEX_CURRENCY_REGEX: Final[Pattern[str]] = compile("^[A-F0-9]{40}$")
"""
:meta private:
"""
