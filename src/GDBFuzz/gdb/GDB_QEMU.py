# This class handles the GDB connection to QEMU.
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
import multiprocessing as mp
import signal
from typing import Any

from GDBFuzz.gdb.GDB import GDB


class GDB_QEMU(GDB):
    def __init__(
            self,
            stop_responses: mp.Queue[tuple[str, Any]],
            software_breakpoint_addresses: list[int],
            gdb_path: str,
            gdb_server_address: str,
            qemu_process: Any
    ) -> None:
        super().__init__(
            stop_responses,
            mp.Queue(),
            software_breakpoint_addresses,
            False,
            gdb_path,
            gdb_server_address
        )
        self.qemu_process = qemu_process

    def interrupt(self) -> None:
        exit_code = self.qemu_process.poll()
        if exit_code is not None:
            stdout, stderr = self.qemu_process.communicate(timeout=1)
            error_msg = (
                f'QEMU Process unexpectedly '
                f'terminated. QEMU process {exit_code} {stdout=} {stderr=}'
            )
            log.error(error_msg)
            raise Exception(error_msg)

        self.qemu_process.send_signal(signal.SIGINT)

    # Hardware breakpoints slow down QEMU tremendously -> use sw bkpts
    def set_breakpoint(self, address: int, is_hardware_bp: bool = True) -> str:
        return super().set_breakpoint(address, is_hardware_bp=False)
