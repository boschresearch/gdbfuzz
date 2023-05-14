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

from elftools.elf.elffile import ELFFile
from util import file_is_elf

BREKAPOINT_INSTRUCTION = [0xbe, 0xbe]


def set_software_breakpoints_in_file(
        path_to_input_file: str,
        path_to_output_file: str,
        breakpoint_addresses: list[int]
) -> None:
    is_elf = file_is_elf(path_to_input_file)

    # convert virtual addresses to offsets in file
    breakpoint_file_offsets = []
    if is_elf:
        with open(path_to_input_file, 'rb') as f:
            elf_file = ELFFile(f)
            text_section = elf_file.get_section_by_name('.text')
            test_start_address = text_section.header.sh_addr
            text_file_offset = text_section.header.sh_offset
            for address in breakpoint_addresses:
                breakpoint_file_offsets.append(
                    address - test_start_address + text_file_offset
                )
    else:
        # assume breakpoint_addresses are the file offsets
        breakpoint_file_offsets = breakpoint_addresses

    with open(path_to_input_file, 'rb') as f:
        file_content = bytearray(f.read())

    for offset in breakpoint_file_offsets:
        # BE BE is a breakpoint instruction in ARM Thumb
        file_content[offset:offset + len(BREKAPOINT_INSTRUCTION)] = \
            BREKAPOINT_INSTRUCTION

    with open(path_to_output_file, 'wb') as f:
        f.write(file_content)
