# This class handles starts the target application in QEMU.
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

import atexit
import logging as log
import os
import subprocess
import time
from configparser import ConfigParser
from typing import Any

import networkx as nx
from GDBFuzz.gdb.GDB import GDB
from GDBFuzz.gdb.GDB_QEMU import GDB_QEMU
from GDBFuzz.modes.SUTInstance import SUTInstance


class QEMUInstance(SUTInstance):
    """SUT runs in QEMU. QEMUInstance starts QEMU with this SUT."""

    def __init__(
        self,
        config: ConfigParser,
        cfg: nx.DiGraph
    ) -> None:
        self.init_qemu(
            config['SUT']['binary_file_path'],
            config['Dependencies']['path_to_qemu'],
            config['LogsAndVisualizations']['output_directory']
        )
        super().__init__(config, cfg)

    def init_gdb(self, config: ConfigParser) -> GDB:
        gdb = GDB_QEMU(
            self.stop_responses,
            self.parse_software_breakpoint(config),
            config['GDB']['path_to_gdb'],
            config['GDB']['gdb_server_address'],
            self.qemu_process
        )
        gdb.connect()

        stop_reason, stop_info = gdb.wait_for_stop(timeout=30)
        assert stop_reason == 'stopped, no reason given', \
            f'{stop_reason=} {stop_info=}'

        return gdb

    def init_qemu(
            self,
            binary_file: str,
            path_to_qemu: str,
            output_directory: str
    ) -> None:
        self.binary_file = binary_file
        self.path_to_qemu = path_to_qemu
        self.qemu_process: Any = self.start(output_directory)
        atexit.register(self.stop)

    def start(self, output_directory: str) -> subprocess.Popen[Any]:
        # Enable coverage plugin if it exists
        coverage_plugin_path = os.path.join(
            os.path.dirname(__file__),
            '../../qemu-plugins/libbbtrace.so'
        )
        if os.path.isfile(coverage_plugin_path):
            qemu_cmd = [self.path_to_qemu, '-plugin',
                        coverage_plugin_path, '-d', 'plugin',
                        '-g', '4242', self.binary_file]
            log.info(f'Using QEMU coverage plugin: {qemu_cmd}')
        else:
            qemu_cmd = [self.path_to_qemu, '-g', '4242', self.binary_file]

        qemu_process = subprocess.Popen(
            qemu_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait a second for qemu to start the GDB server
        time.sleep(1)
        exit_code = qemu_process.poll()
        if exit_code is not None:
            raise Exception(
                f'QEMUInstance:__init__(): QEMU Process unexpectedly '
                f'terminated. {exit_code=}'
            )

        # qemu_process.stdout.close()
        # qemu_process.stderr.close()

        return qemu_process

    def __exit__(
            self,
            ex_type: Any,
            ex_value: Any,
            traceback: Any
    ) -> bool | None:
        ret = super().__exit__(ex_type, ex_value, traceback)
        try:
            self.stop()
        except Exception as e:
            log.warn(f'Failed to self.stop(): {e=}')
        return ret

    def stop(self) -> None:
        if not self.qemu_process:
            return

        atexit.unregister(self.stop)

        self.qemu_process.kill()
        self.qemu_process.wait(timeout=30)
        self.qemu_process = None
