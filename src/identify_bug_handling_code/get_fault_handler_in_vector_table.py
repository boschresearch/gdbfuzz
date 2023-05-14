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

from typing import TYPE_CHECKING

import ghidra_bridge

if TYPE_CHECKING:
    import jfx_bridge.bridge._bridged_ghidra.program.model \
        .address.GenericAddress as ghidra_GenericAddress

print('Note that you must start the Ghidra Bridge Server, and analyze the SUT')

# in seconds
GHIDRA_BRIDGE_RESPONSE_TIMEOUT = 600

# These offsets store the address to the fault handlers of the
# ARM cortex L4 processor. Other MCUs may have other offsets.
fault_handlers = [
    0xC,   # hard_fault_handler_offset
    0x10,  # MMU_fault_handler_offset
    0x14,  # bus_fault_handler_offset
    0x18   # usage_fault_handler_offset
]

# Addresses in ARM THUMB have '1' added to them.
SUT_is_arm_thumb = True

# Setup Ghidra Bridge Client.
bridge = ghidra_bridge.GhidraBridge(
    response_timeout=GHIDRA_BRIDGE_RESPONSE_TIMEOUT
)
flat_api = bridge.get_flat_api()


def _to_address(address: int) -> ghidra_GenericAddress:
    """Convert integer to Ghidra Address"""
    prog = flat_api.getCurrentProgram()
    addr_space = prog.getAddressFactory().getDefaultAddressSpace()
    return addr_space.getAddress(address)


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


def read_int(address: int, length: int = 4) -> int:
    # Read 'length' bytes at 'address', returned as int.
    # This function takes care of the little endian conversion
    addr = _to_address(address)
    array = flat_api.getBytes(addr, length)
    return int_array_to_int(array, byteorder='little')


def get_fault_handler_in_vector_table() -> list[int]:
    fault_handler_addresses = []
    for handler in fault_handlers:
        addr = read_int(handler)
        if SUT_is_arm_thumb:
            # Convert from thumb mode address to actual address
            addr -= addr % 2
        fault_handler_addresses.append(addr)

    return fault_handler_addresses


print(get_fault_handler_in_vector_table())
