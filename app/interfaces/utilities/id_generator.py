from abc import ABC, abstractmethod


class IIdGenerator(ABC):
    @abstractmethod
    def new_id(self) -> str:
        """A new identifier that has never been issued before."""
