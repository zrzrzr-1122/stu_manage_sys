from pydantic import BaseModel


class LoginBody(BaseModel):
    username: str
    password: str
    captchaId: str | None = None
    captchaCode: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PortalLoginBody(BaseModel):
    stu_id: int
    password: str
