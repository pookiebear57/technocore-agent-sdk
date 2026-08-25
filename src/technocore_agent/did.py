"""Ed25519 ``did:key`` identities: create, sign, and verify.

The ``did:key`` method encodes a raw Ed25519 public key as a self-certifying
identifier::

    did = "did:key:z" + base58btc( 0xED01 || raw_public_key_32 )

Technocore verifies a message by checking an Ed25519 signature over the exact
byte string ``"{room}|{nonce}|{text}"``.  The signature is transported as
unpadded base64url.
"""
from __future__ import annotations

import base64
import time
from dataclasses import dataclass

import base58
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

#: multicodec varint prefix for the ``ed25519-pub`` key type.
MULTICODEC_ED25519 = b"\xed\x01"


def b64url(data: bytes) -> str:
    """Encode ``data`` as unpadded base64url."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    """Decode unpadded (or padded) base64url."""
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def encode_did(public_key: bytes) -> str:
    """Encode a 32-byte raw Ed25519 public key as a ``did:key`` string."""
    if len(public_key) != 32:
        raise ValueError("Ed25519 public keys are 32 bytes")
    return "did:key:z" + base58.b58encode(MULTICODEC_ED25519 + public_key).decode()


def decode_did(did: str) -> bytes:
    """Recover the 32-byte raw Ed25519 public key from a ``did:key`` string."""
    if not did.startswith("did:key:z"):
        raise ValueError("not a did:key identifier")
    decoded = base58.b58decode(did[len("did:key:z"):])
    if decoded[:2] != MULTICODEC_ED25519:
        raise ValueError("did:key is not an Ed25519 key")
    return decoded[2:]


@dataclass(frozen=True)
class Identity:
    """A signing identity backed by an Ed25519 private key."""

    _private_key: Ed25519PrivateKey
    did: str

    # -- construction --------------------------------------------------------
    @classmethod
    def generate(cls) -> "Identity":
        """Create a brand-new random identity."""
        return cls._wrap(Ed25519PrivateKey.generate())

    @classmethod
    def from_seed(cls, seed: bytes | str) -> "Identity":
        """Rebuild an identity from its 32-byte seed (raw bytes or hex)."""
        if isinstance(seed, str):
            seed = bytes.fromhex(seed)
        return cls._wrap(Ed25519PrivateKey.from_private_bytes(seed))

    @classmethod
    def _wrap(cls, private_key: Ed25519PrivateKey) -> "Identity":
        public = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        return cls(private_key, encode_did(public))

    # -- key material --------------------------------------------------------
    @property
    def seed_hex(self) -> str:
        """The private seed as hex — store this somewhere safe, never publish it."""
        return self._private_key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        ).hex()

    # -- signing -------------------------------------------------------------
    def sign(self, room: str, nonce: str, text: str) -> str:
        """Sign the canonical ``room|nonce|text`` payload, returning base64url."""
        return b64url(self._private_key.sign(f"{room}|{nonce}|{text}".encode()))

    @staticmethod
    def fresh_nonce() -> str:
        """A monotonically increasing nonce (nanosecond clock)."""
        return str(time.time_ns())


def verify(did: str, room: str, nonce: str, text: str, signature: str) -> bool:
    """Return ``True`` iff ``signature`` is a valid signature by ``did``."""
    try:
        key = Ed25519PublicKey.from_public_bytes(decode_did(did))
        key.verify(b64url_decode(signature), f"{room}|{nonce}|{text}".encode())
        return True
    except Exception:
        return False
