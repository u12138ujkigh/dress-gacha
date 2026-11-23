# -*- coding: utf-8 -*-
"""Modular prompt assembly.

Every option the user picks contributes one named block. Blocks are declared
with their target channel, then concatenated in a fixed order:

    SYSTEM  ← design method (tier), attached template
    USER    ← dimensions, category anchor, garment detail level, visual style,
              composition + action, language contract, brief

The point of the split is that the system message states the rules and the user
message states the request, so editing one never muddies the other. The
/api/api_request endpoint returns the assembled blocks as well, so the UI can
show exactly what each option contributed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SYSTEM = "system"
USER = "user"


@dataclass
class Block:
    """One module of the assembled prompt."""
    key: str              # stable id: "tier_method", "dimensions", ...
    label: str            # Chinese label for the UI
    channel: str          # SYSTEM or USER
    text: str             # the module body
    origin: str = ""      # which option produced it, e.g. "档位=正常版"

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "channel": self.channel,
            "chars": len(self.text),
            "origin": self.origin,
            # The opening line lets the UI locate this module inside the
            # assembled message without summing offsets, which drift as soon as
            # a module is switched off.
            "head": self.text.split("\n")[0][:14],
        }


@dataclass
class Assembled:
    """A full prompt: ordered blocks plus the two rendered messages."""
    blocks: list[Block] = field(default_factory=list)

    def add(self, block: Block) -> None:
        if block.text and block.text.strip():
            self.blocks.append(block)

    def channel_text(self, channel: str, sep: str = "\n\n") -> str:
        return sep.join(b.text.strip() for b in self.blocks if b.channel == channel)

    @property
    def system(self) -> str:
        return self.channel_text(SYSTEM, sep="\n\n---\n\n")

    @property
    def user(self) -> str:
        return self.channel_text(USER, sep="\n\n")

    def outline(self) -> list[dict]:
        return [b.as_dict() for b in self.blocks]
