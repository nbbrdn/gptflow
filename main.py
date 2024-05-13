import os
import sys
import uuid

from fastapi import FastAPI, Query
from fastapi.routing import APIRouter
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
from sqlalchemy import Column, ForeignKey, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from typing import Any, List

from metadata import (
    GPTToolMetadata,
    FunctionMetadata,
    FunctionSignatureMetadata,
    FunctionParameterMetadata,
)

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


class GptFunction(Base):
    __tablename__ = "gpt_functions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    parameters = relationship(
        "FunctionParameter",
        back_populates="function",
        lazy="selectin",
    )


class FunctionParameter(Base):
    __tablename__ = "function_parameters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    function_id = Column(
        UUID(as_uuid=True), ForeignKey("gpt_functions.id"), nullable=False
    )
    function = relationship("GptFunction", back_populates="parameters")
    name = Column(String, nullable=False)
    param_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    required = Column(Boolean, nullable=True, default=True)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls, handler(str))


class FunctionDelcaration(BaseModel):
    name: str
    description: str
    parameters: List[FunctionParameter] = []


class FunctionDAL:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_function(
        self, name: str, description: str, parameters: List[FunctionParameter]
    ) -> GptFunction:
        new_function = GptFunction(name=name, description=description)
        new_function.parameters = parameters
        self.db_session.add(new_function)
        await self.db_session.flush()
        return new_function

    async def list_functions(self):
        stmt = select(GptFunction)
        result = await self.db_session.execute(stmt)
        return result


@main_router.get("/time/")
async def get_local_time(offset: int = Query(..., ge=-12, le=14)):
    tz = timezone(timedelta(hours=offset))
    local_time = datetime.now(tz)
    return {"timezone": offset, "current_time": local_time}


async def _register_function(body: FunctionDelcaration) -> FunctionMetadata:
    async with async_session() as session:
        async with session.begin():
            function_dal = FunctionDAL(session)
            new_function = await function_dal.create_function(
                name=body.name, description=body.description, parameters=body.parameters
            )
            return FunctionMetadata(
                name=new_function.name,
                description=new_function.description,
                parameters=new_function.parameters,
            )


async def _list_gpt_functions() -> List[GPTToolMetadata]:
    async with async_session() as session:
        async with session.begin():
            function_dal = FunctionDAL(session)
            result = await function_dal.list_functions()

            gpt_tools = []
            for function in result.scalars():
                properties = {}
                required = []
                for param in function.parameters:
                    properties[param.name] = FunctionParameterMetadata(
                        type=param.param_type,
                        description=param.description,
                    )
                    if param.required:
                        required.append(param.name)

                gpt_tool = GPTToolMetadata(
                    type="function",
                    function=FunctionMetadata(
                        name=function.name,
                        description=function.description,
                        parameters=FunctionSignatureMetadata(
                            type="object", properties=properties, required=required
                        ),
                    ),
                )
                gpt_tools.append(gpt_tool)

            return gpt_tools


@function_registry_router.post("/", response_model=FunctionMetadata)
async def register_gpt_function(body: FunctionDelcaration) -> FunctionMetadata:
    return await _register_function(body)


@function_registry_router.get("/", response_model=List[GPTToolMetadata])
async def list_gpt_functions() -> List[GPTToolMetadata]:
    return await _list_gpt_functions()


main_router.include_router(function_registry_router, prefix="/registry")
app.include_router(main_router)
