"""Pydantic request/response models."""
from pydantic import BaseModel, Field
from typing import Optional


class LoginIn(BaseModel):
    username: str
    password: str | None = None
    role: str | None = Field(default=None, description="legacy demo field, ignored when password provided")


class SignupIn(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, description="minimum 8 chars")
    role: str = Field(default="operator", description="viewer | operator | admin (demo)")


class TokenOut(BaseModel):
    token: str
    expires_in: int = 3600


class EventAttrs(BaseModel):
    event_cause: str
    event_type: str = "unplanned"
    corridor: str = "Non-corridor"
    priority: str = "High"
    latitude: float = 12.97
    longitude: float = 77.59
    hour: int = 12
    dow: int = 1
    month: int = 6
    is_weekend: int = 0
    zone: str = "__missing__"
    junction: str = "__missing__"
    police_station: str = "__missing__"


class ForecastOut(BaseModel):
    closure_prob: float


class PlanIn(EventAttrs):
    closure_prob: float


class PlanOut(BaseModel):
    closure_prob: float
    expected_crowd: int
    barricades_needed: int
    officers_needed: int
    severity_score: float
    diversion_corridor: Optional[str] = None
    diversion_lat: Optional[float] = None
    diversion_lon: Optional[float] = None


class ChatIn(BaseModel):
    query: str


class RagIn(BaseModel):
    query: str
    k: int = 5
