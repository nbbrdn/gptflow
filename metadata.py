from typing import Dict, List

from pydantic import BaseModel


class TunedModel(BaseModel):
    class Config:
        from_attributes = True


class FunctionSignatureMetadata(TunedModel):
    type: str
    properties: Dict
    required: List


class FunctionParameterMetadata(TunedModel):
    type: str
    description: str


class FunctionMetadata(TunedModel):
    name: str
    description: str
    parameters: FunctionSignatureMetadata


class GPTToolMetadata(TunedModel):
    type: str
    function: FunctionMetadata
