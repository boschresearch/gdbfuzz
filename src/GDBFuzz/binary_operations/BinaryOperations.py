#!/usr/bin/env python3
# This pmodule offers operations on binary program files
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

import logging as log

from elftools.elf.elffile import ELFFile

# TODO: test these functions with .bin files.
# write unit tests for .bin and elf


def get_function_addresses(
        path_to_elf_file: str,
        function_names: list[str]
) -> set[int]:
    """Return the addresses of each function in 'function_names'

    'path_to_elf_file' must be the path to an elf file that contains
    a symbol table.
    """
    ignore_addresses: set[int] = set()
    with open(path_to_elf_file, 'rb') as f:
        elf_file = ELFFile(f)
        symtab = elf_file.get_section_by_name('.symtab')
        assert symtab is not None
        for function_name in function_names:
            function_symbols = symtab.get_symbol_by_name(function_name)
            if not function_symbols:
                log.warn(f'Symbol {function_name} not found.')
                continue
            for symbol in function_symbols:
                if symbol.entry.st_info.type == 'STT_FUNC':
                    symbol_address = symbol.entry.st_value
                    # If address is in thumb mode, convert it to non-thumb
                    thumb_bit = symbol_address % 2
                    symbol_address -= thumb_bit
                    ignore_addresses.add(symbol_address)
                    log.info(
                        f'Ignore function {function_name=}, '
                        f'{symbol_address=}'
                    )
    log.info(f'{ignore_addresses=}')
    return ignore_addresses


def file_is_elf(path_to_file: str) -> bool:
    """Return True if the file at 'path_to_file' is an ELF file"""
    with open(path_to_file, 'rb') as f:
        return f.read(4) == b'\x7fELF'
