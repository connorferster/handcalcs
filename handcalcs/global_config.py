#    Copyright 2020 Connor Ferster

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import json
from typing import Any
import pathlib

_config = {}

def _load_global_config(config_file_name: str):
    with open(config_file_name, "r") as config_file:
        _config_data = json.load(config_file)
    return _config_data

_here = pathlib.Path(__file__).parent
_config_file = _here / "config.json"
_config = _load_global_config(_config_file)

_OPTIONS = [f"{key} -> {type(value)} (default = {value})" for key, value in _config.items()]
_OPTIONS_TEXT = (
    "Configuration can be set on the following options:\n"
     + "\n".join(_OPTIONS)
)

def set_option(option: str, value: Any) -> None:
    f"""
    Returns None. Sets the value of 'option' to 'value' in the global config.

    {_OPTIONS_TEXT}
    """
    if option in _config and isinstance(value, type(_config[option])):
        _config[option] = value
    elif option in _config and not isinstance(value, type(_config[option])):
        raise ValueError(
            f"Option, {option}, must be set with a value of type {type(_config[option])},"
            f" not {type(value)}."
        )
    else:
        raise ValueError(
            f"{option} is not a valid option that can be set."
        )


def save_config() -> None:
    """
    Returns None. Saves the current global configuration as the default configuration
    that will be loaded upon module import.
    """
    with open(_config_file, 'w', newline="") as config_file:
        json.dump(_config, config_file)
        config_file.truncate()