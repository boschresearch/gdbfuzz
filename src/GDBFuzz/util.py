# This file holds some util functions.
# Copyright (c) 2022 Robert Bosch GmbH
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

import importlib.util
from typing import Any


def import_class(
        module_name: str,
        module_file_path: str,
        class_name: str
) -> Any:
    module_spec = importlib.util.spec_from_file_location(
        module_name,
        module_file_path
    )
    if not module_spec:
        raise Exception(f'Failed to import module {module_name}')
    #assert isinstance(module_spec.loader, importlib.abc.Loader)

    module = importlib.util.module_from_spec(module_spec)

    module_spec.loader.exec_module(module)

    return getattr(module, class_name)


def int_array_to_int(array: list[int], byteorder: str = 'little') -> int:
    # 'byteorder' specifies how the ints in 'array' are represented
    assert byteorder in ['little', 'big']
    _sum = 0
    for i in array:
        _sum <<= 8
        _sum += i
    sum_bytes = _sum.to_bytes(len(array), byteorder='big')
    sum_int = int.from_bytes(sum_bytes, byteorder=byteorder)
    return sum_int
