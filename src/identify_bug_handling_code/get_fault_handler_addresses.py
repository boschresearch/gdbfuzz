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
import struct
import sys

from elftools.elf.elffile import ELFFile
from identify_bug_handling_code.elf_util import file_is_elf

# TODO: check if this works

# These offsets store the address to the fault handlers of the
# ARM cortex L4 processor. Other MCUs may have other offsets.
fault_handlers = [
    0xC,   # hard_fault_handler_offset
    0x10,  # MMU_fault_handler_offset
    0x14,  # bus_fault_handler_offset
    0x18   # usage_fault_handler_offset
]


def get_fault_handler_addresses(path_to_file: str) -> set[int]:
    """If 'path_to_file' is not an elf file, it must store the vector table
    at file offset 0.

    We assume addresses are 32 bit little endian.
    """
    fault_handler_addresses: set[int] = set()
    with open(path_to_file, 'rb') as f:
        file_content = f.read()
    isr_vector_file_offset = 0
    if file_is_elf(path_to_file):
        # get .isr_vector offset in file
        with open(path_to_file, 'rb') as f:
            elf_file = ELFFile(f)
            isr_vector_section = elf_file.get_section_by_name('.isr_vector')
            if not isr_vector_section:
                raise Exception(f'ELF file {path_to_file} does not include an '
                                f'.isr_vector section')
            isr_vector_file_offset = isr_vector_section.header.sh_offset

    fault_handler_offsets = []
    for handler in fault_handlers:
        fault_handler_offsets.append(isr_vector_file_offset + handler)

    for offset in fault_handler_offsets:
        fault_handler_address = struct.unpack(
            '<I',
            file_content[offset:offset + 4]
        )[0]
        thumb_bit = fault_handler_address % 2
        fault_handler_address -= thumb_bit
        fault_handler_addresses.add(fault_handler_address)
    return fault_handler_addresses


if len(sys.argv) < 2:
    print('Usage: ./get_fault_handler_addresses.py path/to/SUT.elf')
    exit(1)

if not os.path.isfile(sys.argv[1]):
    print('First CLI argument is not the path to a file')
    exit(2)

if not file_is_elf(sys.argv[1]):
    print('First CLI argument is not the path to an ELF file')
    exit(3)

print(get_fault_handler_addresses(sys.argv[1]))
