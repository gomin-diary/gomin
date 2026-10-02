from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    path: list[str | int]
    code: str
    message: str


class ApiError(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ApiSuccess(BaseModel, Generic[T]):
    success: Literal[True] = True
    data: T
    error: None = None


class ApiFailure(BaseModel):
    success: Literal[False] = False
    data: None = None
    error: ApiError


class HealthData(BaseModel):
    status: Literal["ok"] = "ok"


class DatabaseHealthData(HealthData):
    database: Literal["connected"] = "connected"
