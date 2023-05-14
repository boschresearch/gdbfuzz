# This class handles the GDB connection to a user application.
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
import os
import signal
from typing import Any

from GDBFuzz.gdb.GDB import GDB


class GDBSUTRunsOnHost(GDB):
    def __init__(
            self,
            stop_responses: mp.Queue[tuple[str, Any]],
            gdb_path: str,
            software_breakpoint_addresses: list[int],
            binary_file_path: str
    ) -> None:
        super().__init__(
            stop_responses,
            mp.Queue(),
            software_breakpoint_addresses,
            False,
            gdb_path,
            None  # No address required
        )

        self.binary_file_path = binary_file_path

    def connect(self) -> str:
        self.send(f'-file-exec-and-symbols {self.binary_file_path}')
        self.send('-exec-run --start')
        stop_reason, stop_info = self.wait_for_stop(timeout=30)
        assert stop_reason == 'breakpoint hit', stop_info

        response = self.send('-list-thread-groups')
        self.SUT_pid: str = response['payload']['groups'][0]['pid']
        return self.SUT_pid

    def disconnect(self) -> None:
        pass

    def interrupt(self) -> None:
        try:
            os.kill(int(self.SUT_pid), signal.SIGINT)
        except ProcessLookupError as e:
            log.warn(f'Catched exception {e}')
            pass

    def set_breakpoint(self, address: int, is_hardware_bp: bool = True) -> str:
        return super().set_breakpoint(address, is_hardware_bp=False)
