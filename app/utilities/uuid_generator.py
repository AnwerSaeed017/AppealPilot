import uuid

from app.interfaces.utilities.id_generator import IIdGenerator


class UuidGenerator(IIdGenerator):
    def new_id(self) -> str:
        return str(uuid.uuid4())
