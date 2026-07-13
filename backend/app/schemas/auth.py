from pydantic import BaseModel, Field


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class RegisterIn(Credentials):
    name: str = ""


class UserOut(BaseModel):
    id: str
    email: str
    name: str


class AuthOut(BaseModel):
    token: str
    user: UserOut
