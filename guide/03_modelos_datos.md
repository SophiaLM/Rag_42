# 03 — Modelos de datos

Define los modelos pydantic y helpers de IO.

## 1. Código

`src/models.py`:
```python
import uuid
from typing import List, Union

from pydantic import BaseModel, Field, model_validator


class MinimalSource(BaseModel):
    file_path: str
    first_character_index: int = Field(ge=0)
    last_character_index: int

    @model_validator(mode="after")
    def _check_range(self) -> "MinimalSource":
        if self.last_character_index <= self.first_character_index:
            raise ValueError("last_character_index must be > first_character_index")
        return self


class UnansweredQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str


class AnsweredQuestion(UnansweredQuestion):
    sources: List[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    rag_questions: List[Union[AnsweredQuestion, UnansweredQuestion]]


class MinimalSearchResults(BaseModel):
    question_id: str
    question: str
    retrieved_sources: List[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    answer: str


class StudentSearchResults(BaseModel):
    search_results: List[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(BaseModel):
    search_results: List[MinimalAnswer]
    k: int
```

`src/io_utils.py`:
```python
from pathlib import Path

from pydantic import BaseModel

from src.models import RagDataset, StudentSearchResults


def load_dataset(path: str | Path) -> RagDataset:
    return RagDataset.model_validate_json(Path(path).read_text(encoding="utf-8"))


def save_model(model: BaseModel, path: str | Path) -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def load_search_results(path: str | Path) -> StudentSearchResults:
    return StudentSearchResults.model_validate_json(Path(path).read_text(encoding="utf-8"))
```

## 2. Testers

`tests/test_models.py`:
```python
from pathlib import Path

from pydantic import ValidationError
import pytest

from src.io_utils import load_dataset, save_model
from src.models import MinimalSource, UnansweredQuestion, RagDataset


ROOT_DS = "data/datasets"


def test_unanswered_dataset_loads() -> None:
    ds = load_dataset(f"{ROOT_DS}/UnansweredQuestions/dataset_docs_public.json")
    assert len(ds.rag_questions) == 100


def test_answered_dataset_loads() -> None:
    ds = load_dataset(f"{ROOT_DS}/AnsweredQuestions/dataset_code_public.json")
    assert len(ds.rag_questions) == 99


def test_roundtrip(tmp_path: Path) -> None:
    ds = load_dataset(f"{ROOT_DS}/AnsweredQuestions/dataset_docs_public.json")
    out = tmp_path / "copy.json"
    save_model(ds, out)
    assert load_dataset(out) == ds


def test_invalid_range_raises() -> None:
    with pytest.raises(ValidationError):
        MinimalSource(file_path="x.py", first_character_index=10, last_character_index=10)


def test_negative_index_raises() -> None:
    with pytest.raises(ValidationError):
        MinimalSource(file_path="x.py", first_character_index=-1, last_character_index=5)


def test_uuid_is_generated_unique() -> None:
    a = UnansweredQuestion(question="q")
    b = UnansweredQuestion(question="q")
    assert a.question_id != b.question_id
```

## 3. Checklist

- [ ] `src/models.py` y `src/io_utils.py` creados.
- [ ] Testers pasan.
- [ ] `make lint` pasa.

## 4. Tiempo estimado

**≈ 30 minutos.**
