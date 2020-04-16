#!/usr/bin/python3
"""
AscmInputFile.py: Functions for handling input files
                  (command file and input file).
"""

from typing import Dict


def check_dict_str_to_str(data: dict, dict_name: str):
    """
    Check that a given top-level element in 'data' dict is a simple str-to-str
    dict.
    """
    assert dict_name in data, \
        f"Top-level dict must contain key '{dict_name}'."
    d = data[dict_name]
    assert isinstance(dict), \
        f"Top-level sub-element '{dict_name}' must be a dict."
    assert all(isinstance(key, str) for key in d), \
        f"Keys of top-level dict '{dict_name}' must be strings."
    assert all(key != "" for key in d), \
        f"Keys of top-level dict '{dict_name}' must not be empty strings."
    assert all(isinstance(value, str) for value in d.values()), \
        f"All values of top-level dict '{dict_name}' must be strings."


def expand_vars(text: str, variables: Dict[str, str]) -> str:
    """
    Expand all variables in a given string.

    For the moment, variables must not contain variable references.
    """
    for var, value in variables.items():
        if "§{" in value:
            raise Exception(f"Variable {var} itself contains a variable marker.")
        var = "§{" + var + "}"
        text = text.replace(var, value)

    return text
