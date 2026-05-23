from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SegmentRow(BaseModel):
    segment: str
    bookings: int
    no_shows: float
    no_show_rate: float
    avg_price: float | None = None
    observed_revenue_at_risk: float | None = None


class AssistantQuery(BaseModel):
    question: str = Field(min_length=3)


class PredictionRequest(BaseModel):
    branch: str | None = None
    platform: str | None = None
    country: str | None = None
    room: str | None = None
    first_time_flag: int | None = None
    customer_status: str | None = None
    price: float | None = None
