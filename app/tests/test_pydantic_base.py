from typing import Optional

import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from ..schema.pydantic_base import pydantic_partial


class TestPartialModel:
    # The function returns a new BaseModel with all fields optional if exclude_fields is
    # None.
    def test_all_fields_optional_if_exclude_fields_is_none(self):
        # Arrange
        class MyModel(BaseModel):
            field1: int
            field2: str

        # Act
        partial = pydantic_partial()(MyModel)

        # Assert
        props = partial.model_json_schema()["properties"]
        assert issubclass(partial, BaseModel)
        assert "field1" in props
        assert "field2" in props
        if "type" in props["field1"]:
            assert props["field1"]["type"] == "integer"
        if "type" in props["field2"]:
            assert props["field2"]["type"] == "string"

    # The function returns a new BaseModel with specified fields optional if
    # exclude_fields is a list of field names.
    def test_specified_fields_optional_if_exclude_fields_is_list(self):
        # Arrange
        class MyModel(BaseModel):
            field1: int
            field2: str
            field3: float

        # Act
        partial = pydantic_partial(exclude_fields=["field1", "field3"])(MyModel)

        # Assert
        assert issubclass(partial, BaseModel)
        assert "field1" not in partial.__annotations__
        assert partial.__annotations__["field2"] == Optional[str]
        assert "field3" not in partial.__annotations__

    # The function returns a new BaseModel with the same name and module as the original
    # model.
    def test_same_name_and_module_as_original_model(self):
        # Arrange
        class MyModel(BaseModel):
            field1: int
            field2: str

        # Act
        partial = pydantic_partial()(MyModel)

        # Assert
        assert partial.__name__ == "MyModel"
        assert partial.__module__ == MyModel.__module__

    # The function returns a new BaseModel with no fields if exclude_fields is an empty
    # list.
    def test_no_fields_if_exclude_fields_is_empty_list(self):
        # Arrange
        class MyModel(BaseModel):
            field1: int
            field2: str

        # Act
        partial = pydantic_partial(exclude_fields=[])(MyModel)

        # Assert
        assert issubclass(partial, BaseModel)
        assert len(partial.__annotations__) == 2

    # The function returns a new BaseModel with no fields if exclude_fields contains all
    # field names.
    def test_no_fields_if_exclude_fields_contains_all_field_names(self):
        # Arrange
        class MyModel(BaseModel):
            field1: int
            field2: str

        # Act
        partial = pydantic_partial(exclude_fields=["field1", "field2"])(MyModel)

        # Assert
        assert issubclass(partial, BaseModel)
        assert len(partial.__annotations__) == 0

    # A field with a default_factory keeps its factory and does not get a None default.
    def test_field_with_default_factory_keeps_factory(self):
        # Arrange
        class MyModel(BaseModel):
            field1: int
            tags: list[str] = Field(default_factory=lambda: ["a"])

        # Act
        partial = pydantic_partial()(MyModel)

        # Assert
        assert partial(field1=1).tags == ["a"]
        assert partial().field1 is None
        assert partial(tags=None).tags is None

    # The function raises an exception if the original model is not a subclass of
    # BaseModel.
    def test_exception_if_original_model_not_subclass_of_BaseModel(self):
        # Arrange
        class MyModel:
            field1: int
            field2: str

        # Act & Assert
        with pytest.raises(TypeError):
            pydantic_partial()(MyModel)


class TestPartialKeepsValidators:
    def test_field_validator_runs_on_the_partial(self):
        class MyModel(BaseModel):
            size: int
            other: int

            @field_validator("size")
            @classmethod
            def positive(cls, v):
                if v <= 0:
                    raise ValueError("must be positive")
                return v

        partial = pydantic_partial(exclude_fields=["other"])(MyModel)
        with pytest.raises(ValidationError):
            partial(size=-1)
        assert partial(size=3).size == 3
        assert partial().size is None

    def test_model_validator_runs_on_the_partial(self):
        class MyModel(BaseModel):
            a: int
            b: int
            c: int

            @model_validator(mode="after")
            def a_below_b(self):
                if self.a is not None and self.b is not None and self.a >= self.b:
                    raise ValueError("a must be below b")
                return self

        partial = pydantic_partial(exclude_fields=["c"])(MyModel)
        with pytest.raises(ValidationError):
            partial(a=5, b=1)
        assert partial(a=1, b=5).b == 5

    def test_upload_schema_refuses_a_file_over_10_mb(self):
        from ..schema.uploads import FileCreate

        base = {"name": "report.pdf", "unique_name": "abc.pdf", "file_type": "x/y"}
        with pytest.raises(ValidationError):
            FileCreate(**base, source="s", file_size=10_000_001)
        assert FileCreate(**base, source="s", file_size=10).file_size == 10
