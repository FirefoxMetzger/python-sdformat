from typing import Type, Union
import warnings
import importlib
import numpy as np


class Element:
    def __init__(
        self,
        binding_class,
        required,
        default,
        *,
        removed_in: str = None,
        alternative: str = None,
    ) -> None:
        self.default = default
        self.clazz = binding_class
        self.required = required
        self.version_removed = removed_in
        self.known_alternative = alternative

    def __set_name__(self, owner, name):
        # pirated to register element

        if self.clazz is None:
            # clazz is None means the element
            # can be nested inside itself.
            self.clazz = owner

        if owner.known_children is None:
            owner.known_children = dict()

        owner.known_children[self.clazz.tag] = self.clazz
        self.name = name

    def __get__(self, instance, owner) -> None:
        if isinstance(self.clazz, str):
            self.clazz = importlib.import_module(self.clazz)

        if self.version_removed is not None:
            warning_string = (
                f"`{self.name}` is deprecated since SDFormat "
                f"v{self.version_removed}."
            )
            if self.known_alternative:
                warning_string += f" Use `{self.known_alternative}` instead."

            warnings.warn(warning_string, DeprecationWarning)

    def _find_child_element(self, instance):
        for child in instance.children:
            if isinstance(child, self.clazz):
                return child
        else:
            return None


class Attribute:
    def __init__(
        self, type: Type, required: str, *, default=None, description=None
    ) -> None:
        self.required = required
        self.clazz = type
        self.default = default
        self.description = description

    def __set_name__(self, owner, name):
        self.name = name

        if owner.known_attributes is None:
            owner.known_attributes = set()

        owner.known_attributes.add(name)

    def __get__(self, instance, owner):
        if self.name in instance.attributes:
            value = instance.attributes[self.name]
        elif self.default is not None:
            value = self.default
        else:
            return None

        if isinstance(value, str):
            return value
        elif isinstance(value, bool):
            return value in [True, "True", "true", "1"]

    def __set__(self, instance, value):
        value = str(self.clazz(value))
        if value in ["True", "False"]:
            value = value.lower()

        instance.attributes[self.name] = value


class ChildElement(Element):
    def __init__(
        self,
        binding_class,
        required,
        *,
        removed_in: str = None,
        alternative: str = None,
    ) -> None:
        super().__init__(
            binding_class,
            required,
            default=None,
            removed_in=removed_in,
            alternative=alternative,
        )

    def __get__(self, instance, owner):
        super().__get__(instance, owner)

        if self.required in ["*", "+"]:
            return self.__get_multiple__(instance, owner)
        elif self.required in ["1", "0"]:
            return self.__get_single__(instance, owner)

    def __get_multiple__(self, instance, owner):
        return tuple(x for x in instance.children if isinstance(x, self.clazz))

    def __get_single__(self, instance, owner):
        child = self._find_child_element(instance)
        if child is not None:
            return child
        else:
            child = self.clazz()
            instance.children.append(child)
            return child


class SimpleElement(Element):
    def __init__(
        self,
        required: str,
        default,
        *,
        removed_in: str = None,
        alternative: str = None,
        tag: str = None,
    ) -> None:
        self.tag = tag

        super().__init__(
            None, required, default, removed_in=removed_in, alternative=None
        )

    def __set_name__(self, owner, name):
        from .base import SdfElement

        class_name = "".join(word.title() for word in name.split("_"))
        setattr(
            owner,
            class_name,
            type(class_name, (SdfElement,), {"tag": self.tag or name}),
        )
        self.clazz = getattr(owner, class_name)

        super().__set_name__(owner, name)

    def __get__(self, instance, owner):
        super().__get__(instance, owner)

        child = self._find_child_element(instance)
        if child is not None and child.text is not None:
            text = child.text.strip()
        else:
            text = self.default

        return text


class Vector2(SimpleElement):
    def __get__(self, instance, owner):
        text = super().__get__(instance, owner)

        # combine whitespace
        text = " ".join(text.split())

        return tuple(map(float, text.split(" ", 2)))

    def __set__(self, instance, value):
        child = self._find_child_element(instance)
        if child is None:
            child = self.clazz()
            instance.children.append(child)

        if isinstance(value, str):
            child.text = value
        elif isinstance(value, (tuple, list)):
            child.text = " ".join(map(str, value))
        elif isinstance(value, np.ndarray):
            child.text = " ".join(map(str, value.tolist()))
        else:
            raise ValueError("Could not interpret input as 2-element vector.")


class Vector3(SimpleElement):
    def __get__(self, instance, owner):
        text = super().__get__(instance, owner)

        # combine whitespace
        text = " ".join(text.split())

        return tuple(map(float, text.split(" ", 3)))

    def __set__(self, instance, value):
        child = self._find_child_element(instance)
        if child is None:
            child = self.clazz()
            instance.children.append(child)

        if isinstance(value, str):
            child.text = value
        elif isinstance(value, (tuple, list)):
            child.text = " ".join(map(str, value))
        elif isinstance(value, np.ndarray):
            child.text = " ".join(map(str, value.tolist()))
        else:
            raise ValueError("Could not interpret input as 3-element vector.")


class Color(SimpleElement):
    def __get__(self, instance, owner):
        text = super().__get__(instance, owner)

        # combine whitespace
        text = " ".join(text.split())

        return tuple(map(float, text.split(" ", 4)))

    def __set__(self, instance, value):
        child = self._find_child_element(instance)
        if child is None:
            child = self.clazz()
            instance.children.append(child)

        if isinstance(value, str):
            child.text = value
        elif isinstance(value, (tuple, list)):
            child.text = " ".join(map(str, value))
        elif isinstance(value, np.ndarray):
            child.text = " ".join(map(str, value.tolist()))
        else:
            raise ValueError("Could not interpret input as a color.")


class BoolElement(SimpleElement):
    def __get__(self, instance, owner):
        text = super().__get__(instance, owner)
        return text in ["True", "true", "1"]

    def __set__(self, instance, value):
        child = self._find_child_element(instance)
        if child is None:
            child = self.clazz()
            instance.children.append(child)

        if isinstance(value, str):
            child.text = value
        elif isinstance(value, (bool, np.bool_)):
            child.text = str(value)
        else:
            raise ValueError("Could not interpret input as bool.")


class FloatElement(SimpleElement):
    def __get__(self, instance, owner):
        text = super().__get__(instance, owner)

        return float(text)

    def __set__(self, instance, value):
        child = self._find_child_element(instance)
        if child is None:
            child = self.clazz()
            instance.children.append(child)

        if isinstance(value, str):
            child.text = value
        elif isinstance(value, float):
            child.text = str(value)
        elif isinstance(value, int):
            child.text = str(value)
        else:
            raise ValueError("Could not interpret input as float.")


class IntegerElement(SimpleElement):
    def __get__(self, instance, owner):
        text = super().__get__(instance, owner)
        return int(text)

    def __set__(self, instance, value):
        child = self._find_child_element(instance)
        if child is None:
            child = self.clazz()
            instance.children.append(child)

        if isinstance(value, str):
            child.text = value
        elif isinstance(value, int):
            child.text = str(value)
        else:
            raise ValueError("Could not interpret input as int.")


class StringElement(SimpleElement):
    def __get__(self, instance, owner):
        text = super().__get__(instance, owner)
        return text

    def __set__(self, instance, value):
        child = self._find_child_element(instance)
        if child is None:
            child = self.clazz()
            instance.children.append(child)

        if isinstance(value, str):
            child.text = value
        else:
            raise ValueError("Could not interpret input as str.")


__all__ = [
    "ChildElement",
    "Vector2",
    "Vector3",
    "BoolElement",
    "Attribute",
    "FloatElement",
    "IntegerElement",
    "StringElement",
    "Color",
]
