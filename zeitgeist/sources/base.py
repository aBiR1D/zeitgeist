"""Abstract base class for signal collectors."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zeitgeist.models import Signal


class SignalCollector(abc.ABC):
    """Base class that all signal collectors must implement."""

    name: str = "base"

    @abc.abstractmethod
    async def collect(self) -> list[Signal]:
        """Collect signals from this source.

        Returns a list of Signal objects representing emerging activity.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
