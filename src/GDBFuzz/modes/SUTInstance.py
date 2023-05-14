# This class manages all stuff regarding the SUT.
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
import traceback
import time
from configparser import ConfigParser
from types import TracebackType
from typing import Any

import networkx as nx
from GDBFuzz.connections.SUTConnection import SUTConnection
from GDBFuzz.gdb.GDB import GDB


EXCEPTION_COUNT = 0


class SUTInstance:
    """When this class is instantiated, it instantiates the GDB Python class,
    Connection, and the ConcolicExecution component.
    When this class is deleted, it deletes these components.
    This class is delected when the target system restarts.
    """

    def __init__(
            self,
            config: ConfigParser,
            cfg: nx.DiGraph
    ) -> None:
        # Maps GDB Breakpoint IDs (key) to addresses (value) where this
        # breakpoint is placed.
        self.breakpoints: dict[str, int] = dict()

        self.stop_responses: mp.Queue[tuple[str, Any]] = mp.Queue()

        # Some GDB Server implementations (especially ESP32) do not report hit breakpoints
        # correctly in the GDB response. With the ESP32 GDB server, for instance,
        # the real hit breakpoint is reported in a seperate message and the current PC
        # of the first CPU core is reported via the standard  GDB response.
        # Therefore this queue is introduced as a workaround 
        self.aditional_hit_addresses: mp.Queue[int] = mp.Queue()
        self.gdb: GDB = self.init_gdb(config)

        self.SUT_connection = self.init_SUT_connection(config)

    def reset(self):
        # Reset target
        self.gdb.send('delete breakpoints')
        self.gdb.send('monitor reset halt')
        self.gdb.send('flushregs')


    def parse_software_breakpoint(self, config: ConfigParser) -> list[int]:
        """User configuration can include the addresses where software
        breakpoints are set. Return these addresses. These software
        breakpoints are set at error handling code.
        """

        software_breakpoint_addresses: list[int] = []
        sw_bps = config['SUT']['software_breakpoint_addresses'].split()
        for sw_bp in sw_bps:
            if sw_bp.isdigit():
                software_breakpoint_addresses.append(int(sw_bp))
            else:
                # Assume sw_bp is a hexstring, raise Exception if not.
                software_breakpoint_addresses.append(int(sw_bp, 16))
        return software_breakpoint_addresses

    # Subclasses may override init_gdb
    def init_gdb(self, config: ConfigParser) -> GDB:
        
        retries = 3 
        
        while retries > 0:
            try:
                gdb = GDB(
                    self.stop_responses,
                    self.aditional_hit_addresses,
                    self.parse_software_breakpoint(config),
                    config['SUT']['consider_sw_breakpoint_as_error'] == 'True',
                    config['GDB']['path_to_gdb'],
                    config['GDB']['gdb_server_address']
                )

                gdb.connect()

                stop_reason, stop_info = gdb.wait_for_stop(timeout=30)
                assert stop_reason == 'stopped, no reason given', \
                    f'{stop_reason=} {stop_info=}'

                return gdb
            except Exception as e:
                log.warning(f"Exception while connecting to GDB: {e}")
                retries -= 1
                time.sleep(5)
                if retries == 0:
                    raise e
        

    # Subclasses may override init_SUT_connection
    def init_SUT_connection(self, config: ConfigParser) -> SUTConnection:
        return SUTConnection(
            self.stop_responses,
            config['SUTConnection'],
            self.reset
        )

    def get_additional_hit_bbs(self) -> list[int]:
        ret: list[int] = []
        while self.aditional_hit_addresses.qsize() > 0:
            ret.append(self.aditional_hit_addresses.get())
        
        return ret

    def __enter__(self) -> SUTInstance:
        return self

    def __exit__(
            self,
            ex_type: type,
            ex_value: Exception,
            ex_traceback: TracebackType
    ) -> bool:
        """Perform cleanup (disconnect etc.) of the components that are about
        to be deleted.
        Some of these may fail because the target system may have crashed.
        """
 
        try:
            self.SUT_connection.disconnect()
        except Exception as e:
            log.warn(f'Failed to SUT_connection.disconnect() {e=}')

        try:
            self.gdb.interrupt()
        except Exception as e:
            log.warn(f'Failed to interrupt GDB {e=}')

        try:
            self.gdb.wait_for_stop(10)
        except Exception as e:
            log.warn(f'Timeout, waiting for GDB to stop {e=}')

        try:
            self.gdb.disconnect()
        except Exception as e:
            log.warn(f'Failed to GDB.disconnect() {e=}')

        try:
            self.gdb.stop()
        except Exception as e:
            log.warn(f'Failed to gdb.stop() {e=}')

        # global EXCEPTION_COUNT
        # if ex_value is not None:
        #     # Exception was raised
        #     exception_traceback = traceback.format_exc()
        #     log.error(f'{ex_type=} {ex_value=} {exception_traceback=}')

        #     EXCEPTION_COUNT += 1
        #     if EXCEPTION_COUNT < 1000:
        #         # Don't reraise the Exception if we have not encoutnered too
        #         # many Exception recently.
        #         return True

        # EXCEPTION_COUNT -= 1

        return True
