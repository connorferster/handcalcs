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
"""
Render arithmetic calucations in Jupyter as though they were written by hand.
"""
__version__ = "1.7.1"  #
from .decorator import handcalc
from .global_config import set_option, save_config

__all__ = ["handcalc"]
