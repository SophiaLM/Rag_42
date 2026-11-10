import uuid
from typing import Union

from pydantic import BaseModel, Field, model_validator


class MinimalSource(BaseModel):
    file_path: str
    first_character_index: int = Field(ge=0)
    last_character_index: int

    @model_validator(mode="after")
    def _check_range(self) -> "MinimalSource":
        """Rechaza rangos vacíos o invertidos (last <= first)."""
        if self.last_character_index <= self.first_character_index:
            raise ValueError(
                "last_character_index must be greater than "
                "first_character_index, got "
                f"[{self.first_character_index}, {self.last_character_index})"
            )
        return self


class UnansweredQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str


class AnsweredQuestion(UnansweredQuestion):
    sources: list[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    rag_questions: list[Union[AnsweredQuestion, UnansweredQuestion]]


class MinimalSearchResults(BaseModel):
    question_id: str
    question: str
    retrieved_sources: list[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    answer: str


class StudentSearchResults(BaseModel):
    search_results: list[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(BaseModel):
    search_results: list[MinimalAnswer]
    k: int
