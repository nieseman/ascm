#!/usr/bin/python3

from typing import Dict


def check_dict_str_to_str(data: dict, dict_name: str):
    """
    Check that a given top-level element in 'data' dict is a simple str-to-str
    dict.
    """
    assert dict_name in data, \
        f"Top-level dict must contain key '{dict_name}'."
    d = data[dict_name]
    assert type(d) is dict, \
        f"Top-level sub-element '{dict_name}' must be a dict."
    assert all(type(key) is str for key in d), \
        f"Keys of top-level dict '{dict_name}' must be strings."
    assert all(key != "" for key in d), \
        f"Keys of top-level dict '{dict_name}' must not be empty strings."
    assert all(type(value) is str for value in d.values()), \
        f"All values of top-level dict '{dict_name}' must be strings."


def expand_vars(s: str, vars: Dict[str, str]) -> str:
    """
    Expand all variables in a given string.

    For the moment, variables must not contain variable references.
    """
    for var, value in vars.items():
        if "§{" in value:
            error(f"Variable {var} itself contains a variable marker.")
        var = "§{" + var + "}"
        s = s.replace(var, value)

    return s
