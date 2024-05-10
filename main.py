import os
import sys
import uuid

from fastapi import FastAPI, Query
from fastapi.routing import APIRouter
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL environment variable is empty.")
    sys.exit(1)

app = FastAPI()

main_router = APIRouter()
function_registry_router = APIRouter()

engine = create_async_engine(DATABASE_URL, future=True, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


class TunedModel(BaseModel):
    class Config:
        """tells pydantic to convert even non dict obj to json"""

        orm_mode = True


class GptFunction(Base):
    __tablename__ = "gpt_functions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)


@main_router.get("/time/")
async def get_local_time(offset: int = Query(..., ge=-12, le=14)):
    tz = timezone(timedelta(hours=offset))
    local_time = datetime.now(tz)
    return {"timezone": offset, "current_time": local_time}


@function_registry_router.get("/")
async def list_functions():
    return {"public": [], "private": []}


@function_registry_router.post("/", response_model=FunctionMetadata)
async def register_function(body: RegisterFunctionRequest) -> FunctionMetadata:
    return await _register_function(body)


main_router.include_router(function_registry_router, prefix="/registry")
app.include_router(main_router)
