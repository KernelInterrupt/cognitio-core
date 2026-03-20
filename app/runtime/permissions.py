from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PermissionTier = Literal["observe", "annotate", "research", "sandboxed_exec"]


class PermissionProfile(BaseModel):
    tier: PermissionTier = "annotate"
    allowed_tools: set[str] = Field(default_factory=set)

    @classmethod
    def for_tier(cls, tier: PermissionTier) -> PermissionProfile:
        mapping: dict[PermissionTier, set[str]] = {
            "observe": {"highlight", "warning", "advice", "next"},
            "annotate": {"highlight", "warning", "advice", "next", "open_annotation"},
            "research": {"highlight", "warning", "advice", "next", "open_annotation", "research"},
            "sandboxed_exec": {
                "highlight",
                "warning",
                "advice",
                "next",
                "open_annotation",
                "research",
                "read_file",
                "write_file",
                "compile_annotation",
            },
        }
        return cls(tier=tier, allowed_tools=mapping[tier])

    def allows(self, tool_name: str) -> bool:
        return tool_name in self.allowed_tools
