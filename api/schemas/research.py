from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class ResearchSourceOut(BaseModel):
    id: UUID
    title: str
    authors: List[str]
    journal: Optional[str]
    doi: Optional[str]
    year: Optional[int]
    citation_apa: Optional[str]
    topics: List[str]
    url: Optional[str]

    class Config:
        from_attributes = True

class KGNodeOut(BaseModel):
    id: UUID
    node_type: str
    name: str
    properties: dict

    class Config:
        from_attributes = True
