from __future__ import annotations

from typing import TypeVar


class ComplexUnionError(Exception):
    def __init__(self, value_in_fault: list | dict):
        # to try output actual data related to the exception
        # rather than a spec itself
        if type(value_in_fault) is dict:
            value_in_fault = {k: v.initial_value
                              if type(v) is Primitive else v
                              for k, v in value_in_fault.items()}
        else:
            value_in_fault = [x.initial_value
                              if type(x) is Primitive else x
                              for x in value_in_fault]
        self.value_in_fault = value_in_fault

    def __str__(self):
        return f'union types with arrays or objects are forbidden (value in fault: {self.value_in_fault})'


class Primitive:
    NULL: Primitive = None

    """To represent a primitive type."""
    def __new__(cls, value):
        if type(value).__name__ == 'NoneType':
            if Primitive.NULL is None:
                Primitive.NULL = super().__new__(cls)
            return Primitive.NULL

        return super().__new__(cls)

    def __init__(self, value):
        self.initial_value = value
        self.value_type = type(value)

    def is_nonetype(self):
        return self is Primitive.NULL

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented

        return self.value_type == other.value_type

    def __repr__(self):
        return 'null' if self.is_nonetype() else self.value_type.__name__


Primitive.NULL = Primitive(None)


class Union:
    values_types: list[Primitive | list | dict]

    def __new__(cls, *values: Primitive | Union | list | dict):
        v_types = []

        for i, v_type in enumerate(values):
            if type(v_type) is Union:
                v_types += v_type.values_types
            elif v_type not in v_types:
                if type(v_type) in [list, dict] and v_types:
                    raise ComplexUnionError(v_type)
                v_types.append(v_type)

        if Primitive.NULL in v_types:  # null, if presented, should be at the end
            v_types.remove(Primitive.NULL)
            v_types.append(Primitive.NULL)

        if len(v_types) == 1:
            return v_types[0]

        this = super().__new__(cls)
        this.values_types = v_types
        return this

    def __repr__(self):
        return ' | '.join(obj.__repr__() for obj in self.values_types)


class NestedArray(list):
    """To represent an undefined nested array."""

    def __repr__(self):
        return '[...]'


class NestedObject(dict):
    """To represent an undefined nested dictionary."""

    def __repr__(self):
        return '{...}'


Toplevel = TypeVar('Toplevel', dict, list)
Spec = TypeVar('Spec', dict[str, Primitive | Union | list | dict], list[Primitive | Union | list | dict])
ObjectSpec = TypeVar('ObjectSpec', bound=dict[str, Primitive | Union | list | dict])
ArraySpec = TypeVar('ArraySpec', bound=list[Primitive | Union | list | dict])


def parse_primitive(value) -> Primitive:
    return Primitive(value)


def parse_array(data: list, max_depth: int) -> list[str | list | dict]:
    if max_depth <= 0:
        return NestedArray()

    result_spec = []
    for value in data:
        if type(value) is dict:
            dtype = parse_dict(value, max_depth - 1)
        elif type(value) is list:
            dtype = parse_array(value, max_depth - 1)
        else:
            dtype = parse_primitive(value)

        if dtype in result_spec:
            continue
        result_spec.append(dtype)

    return result_spec


def parse_dict(data: dict, max_depth: int) -> dict[str, str | list | dict]:
    if max_depth <= 0:
        return NestedObject()

    result_spec = {}
    for field, value in data.items():
        if type(value) is dict:
            dtype = parse_dict(value, max_depth - 1)
        elif type(value) is list:
            dtype = parse_array(value, max_depth - 1)
        else:
            dtype = parse_primitive(value)
        result_spec[field] = dtype

    return result_spec


def validate_dict_specs(spec1: ObjectSpec, spec2: ObjectSpec, *, spec2_i: int) -> None:
    spec1_keys = set(spec1.keys())
    spec2_keys = set(spec2.keys())
    if spec1_keys != spec2_keys:
        missing_in_1 = spec2_keys - spec1_keys
        missing_in_2 = spec1_keys - spec2_keys

        err_msg = ''
        if missing_in_1:
            err_msg += f'dataset {spec2_i - 1} missing fields: {missing_in_1}'
        if missing_in_2:
            err_msg += f'dataset {spec2_i} missing fields: {missing_in_2}'
        raise TypeError(err_msg)


def union_dict_specs(spec1: ObjectSpec, spec2: ObjectSpec) -> ObjectSpec:
    united_spec = {}

    for field, dtype1 in spec1.items():
        dtype2 = spec2[field]
        if type(dtype1) in [list, dict]:
            united_spec[field] = union_specs(dtype1, dtype2)
        else:
            united_spec[field] = Union(dtype1, dtype2)

    return united_spec


def union_array_specs(spec1: ArraySpec, spec2: ArraySpec) -> ArraySpec:
    united_spec = []
    dicts_to_be_checked = []

    for value in spec1:
        if type(value) is dict and value not in dicts_to_be_checked:
            dicts_to_be_checked.append(value)
            continue

        if type(value) is list:
            dtype = value
        else:
            dtype = value

        if dtype in united_spec:
            continue
        united_spec.append(dtype)

    for value in spec2:
        if type(value) is dict and value not in dicts_to_be_checked:
            dicts_to_be_checked.append(value)
            continue

        if type(value) is list:
            dtype = value
        else:
            dtype = value

        if dtype in united_spec:
            continue
        united_spec.append(dtype)

    dicts_to_be_checked = list(dicts_to_be_checked)
    ignored_dicts_indexes = set()
    resolved_dicts = []
    for i, dic1 in enumerate(dicts_to_be_checked):
        if i in ignored_dicts_indexes:
            continue

        for j, dic2 in enumerate(dicts_to_be_checked):
            if i == j:
                continue

            if dic1.keys() == dic2.keys():
                ignored_dicts_indexes.add(j)

                dic1 = {k: Union(v, dic2[k]) for k, v in dic1.items()}

                # dic1 = {k: f'{v} | {dic2[k]}' if v != dic2[k] else v
                #         for k, v in dic1.items()}
        if dic1 not in resolved_dicts:
            resolved_dicts.append(dic1)

    return united_spec + resolved_dicts


def union_specs(spec1: Spec, spec2: Spec, *, _spec2_i: int = 1) -> Spec:
    if type(spec1) is list:
        return union_array_specs(spec1, spec2)

    validate_dict_specs(spec1, spec2, spec2_i=_spec2_i)
    return union_dict_specs(spec1, spec2)


def _unsafe_generate_spec(*datas: Toplevel, max_depth: int) -> Spec:
    dtype = type(datas[0])

    if dtype is list:
        specs = [parse_array(data, max_depth) for data in datas]
    else:
        specs = [parse_dict(data, max_depth) for data in datas]

    result_spec = specs[0]
    for i, spec in enumerate(specs[1:], 1):
        result_spec = union_specs(result_spec, spec, _spec2_i=i)

    return result_spec


def generate_spec(*datas: Toplevel, max_depth: int = 10) -> Spec:
    types = set(type(data) for data in datas)

    if len(types) > 1:
        raise TypeError('all datasets must be equal type')

    dtype = list(types)[0]
    if dtype not in [dict, list]:
        raise TypeError('datasets must be a type of dict or list')

    if max_depth <= 0:
        return dtype()

    return _unsafe_generate_spec(*datas, max_depth=max_depth)


def arrayspec_to_json(arr: ArraySpec) -> list[str | list | dict]:
    result = []
    for dtype in arr:
        if type(dtype) in [NestedArray, NestedObject]:
            result.append(dtype)
        elif type(dtype) is list:
            result.append(arrayspec_to_json(dtype))
        elif type(dtype) is dict:
            result.append(objectspec_to_json(dtype))
        else:
            result.append(str(dtype))

    return result


def objectspec_to_json(obj: ObjectSpec) -> dict[str, str | list | dict]:
    result = {}
    for field, dtype in obj.items():
        if type(dtype) in [NestedArray, NestedObject]:
            result[field] = dtype
        elif type(dtype) is list:
            result[field] = arrayspec_to_json(dtype)
        elif type(dtype) is dict:
            result[field] = objectspec_to_json(dtype)
        else:
            result[field] = str(dtype)

    return result


def spec_to_json(spec: Spec) -> dict[str, str | list | dict] | list[str | list | dict]:
    if type(spec) is list:
        return arrayspec_to_json(spec)

    return objectspec_to_json(spec)


def print_with_tab(data, level=0, end='\n'):
    print(level * '\t' + str(data), end=end)


def pprint_arrayspec(arr: ArraySpec, *, _key='', _level=0):
    if not arr:
        print_with_tab(_key + '[]', _level)
        return

    print_with_tab(_key + '[', _level)
    for i, element in enumerate(arr):
        if type(element) in [list, dict]:
            pprint_spec(element, _level=_level + 1)
        else:
            print_with_tab(str(element) + ',', _level + 1)
    print_with_tab(']', _level)


def pprint_objectspec(obj: ObjectSpec, *, _key='', _level=0):
    if not obj:
        print_with_tab(_key + '{}', _level)
        return

    print_with_tab(_key + '{', _level)
    for k, element in obj.items():
        if type(element) in [list, dict]:
            pprint_spec(element, _key=f'{k}: ', _level=_level + 1)
        else:
            print_with_tab(f'{k}: {element},', _level + 1)
    print_with_tab('}', _level)


def pprint_spec(spec: Spec, *, _key='', _level=0):
    if type(spec) is list:
        pprint_arrayspec(spec, _key=_key, _level=_level)

    pprint_objectspec(spec, _key=_key, _level=_level)
