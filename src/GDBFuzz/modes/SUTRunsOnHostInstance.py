# This class starts a user application with GDB.
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

from configparser import ConfigParser

from GDBFuzz.connections.SUTConnection import SUTConnection
from GDBFuzz.gdb.GDB import GDB
from GDBFuzz.gdb.GDBSUTRunsOnHost import GDBSUTRunsOnHost
from GDBFuzz.modes.SUTInstance import SUTInstance


class SUTRunsOnHostInstance(SUTInstance):

    def reset(self):
        # Reset target
        # Seems not to work on plain GDB
        #self.gdb.send('reset')
        pass

    def init_gdb(self, config: ConfigParser) -> GDB:
        gdb =  GDBSUTRunsOnHost(
            self.stop_responses,
            config['GDB']['path_to_gdb'],
            self.parse_software_breakpoint(config),
            config['SUT']['binary_file_path']
        )
        return gdb

    def init_SUT_connection(self, config: ConfigParser) -> SUTConnection:
        connection = super().init_SUT_connection(config)

        # The workaround for missing reset functionality is to start GDB after the connection is settled
        SUT_pid = self.gdb.connect()
        config['SUTConnection']['SUT_pid'] = SUT_pid

        return connection
