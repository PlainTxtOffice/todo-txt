"""Gate recurring commands through an injected entitlement decision."""

from dataclasses import dataclass
from typing import Protocol


class RecurringEntitlement(Protocol):
    """Supply a fresh access decision from a future subscription adapter.

    Production adapters must validate subscription access externally. No
    client setting or local preview constitutes a verified subscription.
    """

    @property
    def description(self) -> str:
        """Describe the source of the access decision to the user."""
        ...

    def allows_recurring(self) -> bool:
        """Return whether recurring mutations and generation are allowed."""
        ...


@dataclass(frozen=True)
class UnavailableEntitlement:
    """Deny premium access until subscription infrastructure is connected."""

    description: str = "Premium subscription integration is not connected."

    def allows_recurring(self) -> bool:
        """Deny recurring access in ordinary application builds."""
        return False


@dataclass(frozen=True)
class PreviewEntitlement:
    """Allow an explicit local preview without claiming paid access."""

    description: str = "Local development preview — no paid subscription."

    def allows_recurring(self) -> bool:
        """Allow commands during an explicitly selected development preview."""
        return True
