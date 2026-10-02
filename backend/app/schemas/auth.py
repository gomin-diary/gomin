from uuid import UUID

from pydantic import BaseModel


class MemberData(BaseModel):
    id: UUID
    email: str
    name: str
