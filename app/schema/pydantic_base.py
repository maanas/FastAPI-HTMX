from copy import deepcopy
from typing import Any, Callable, Optional, Type, TypeVar

from pydantic import BaseModel, create_model, field_validator, model_validator
from pydantic.fields import FieldInfo

Model = TypeVar("Model", bound=Type[BaseModel])


def pydantic_partial(
    exclude_fields: Optional[list[str]] = None,
) -> Callable[[Model], Model]:
    """A decorator that create a partial model.

    Args:
        model (Type[BaseModel]): BaseModel model.

    Returns:
        Type[BaseModel]: ModelBase partial model.
    """
    if exclude_fields is None:
        exclude_fields = []

    def wrapper(model: Type[Model]) -> Type[Model]:
        base_model: Type[BaseModel] = model

        if not issubclass(base_model, BaseModel):
            raise TypeError("Model must be a subclass of BaseModel")

        def make_field_optional(
            field: FieldInfo, default: Any = None
        ) -> tuple[Any, FieldInfo]:
            new = deepcopy(field)
            # pydantic 2.12+ rejects default plus default_factory: keep the factory
            if new.default_factory is None:
                new.default = default
            new.annotation = Optional[field.annotation]
            return new.annotation, new

        if exclude_fields:
            base_model = BaseModel

        # A model built on `BaseModel` has none of the source model's validators;
        # rebuild them on it (a validator on an excluded field is skipped, not an error)
        validators: dict[str, Any] = {}
        decorators = model.__pydantic_decorators__
        for name, dec in decorators.field_validators.items():
            validators[name] = field_validator(
                *dec.info.fields,
                mode=dec.info.mode,
                check_fields=False,
            )(getattr(dec.func, "__func__", dec.func))
        for name, dec in decorators.model_validators.items():
            func = getattr(dec.func, "__func__", dec.func)
            if dec.info.mode != "after":
                func = classmethod(func)
            validators[name] = model_validator(mode=dec.info.mode)(func)

        return create_model(
            model.__name__,
            __base__=base_model,
            __validators__=validators if exclude_fields else None,
            __module__=model.__module__,
            **{
                field_name: make_field_optional(field_info)
                for field_name, field_info in model.model_fields.items()
                if field_name not in exclude_fields
            },  # type: ignore
        )  # type: ignore

    return wrapper
