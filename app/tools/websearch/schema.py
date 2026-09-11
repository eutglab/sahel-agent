from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class WebSearchInput(BaseModel):
    query: str = Field(min_length=1)
    max_results: int = Field(default=4, ge=1, le=10)


class SearchResultItem(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    published_date: str | None = None


class WebSearchOutput(BaseModel):
    results: List[SearchResultItem] = Field(default_factory=list)
    source: str = ""                 # "exa" | "sample (offline)"
    query_used: str = ""
    note: str = ""
