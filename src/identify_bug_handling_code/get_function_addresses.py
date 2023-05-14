#!/usr/bin/env python3
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

import os
import sys

from elftools.elf.elffile import ELFFile
from util import file_is_elf


def get_function_addresses(
        path_to_elf_file: str,
        function_names: list[str]
) -> list[int]:
    """Return the addresses of each function in 'function_names'

    'path_to_elf_file' must be the path to an elf file that contains
    a symbol table.
    """
    addresses: set[int] = set()
    with open(path_to_elf_file, 'rb') as f:
        elf_file = ELFFile(f)
        symtab = elf_file.get_section_by_name('.symtab')
        assert symtab is not None
        for function_name in function_names:
            function_symbols = symtab.get_symbol_by_name(function_name)
            if not function_symbols:
                print(f'WARNING: Symbol {function_name} not found.')
                continue
            for symbol in function_symbols:
                if symbol.entry.st_info.type == 'STT_FUNC':
                    symbol_address = symbol.entry.st_value
                    # If address is in thumb mode, convert it to non-thumb
                    thumb_bit = symbol_address % 2
                    symbol_address -= thumb_bit
                    addresses.add(symbol_address)
    return list(addresses)


if len(sys.argv) < 3:
    print('Usage: ./get_function_addresses.py path/to/SUT.elf function_name_1'
          '[function_name_2 ...]')
    exit(1)

if not os.path.isfile(sys.argv[1]):
    print('First CLI argument is not the path to a file')
    exit(2)

if not file_is_elf(sys.argv[1]):
    print('First CLI argument is not the path to an ELF file')
    exit(3)

print(get_function_addresses(sys.argv[1], sys.argv[2:]))
