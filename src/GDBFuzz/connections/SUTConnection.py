# This is a manager class for connections to the SUT.
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

import configparser
import logging as log
import multiprocessing as mp
import os
import signal
from typing import Any

from GDBFuzz import util
from GDBFuzz.connections.ConnectionBaseClass import ConnectionBaseClass


class SUTConnection():
    """Create Process for Connection component, and this instance forwards
    generated inputs to this Connection component.
    """

    def __init__(
            self,
            stop_responses: mp.Queue[tuple[str, Any]],
            SUTConnection_config: configparser.SectionProxy,
            reset_sut
    ):
        self.inputs: mp.Queue[bytes] = mp.Queue()
        # TODO: here i want inherited func
        self.connection = self.init_connection(
            stop_responses,
            SUTConnection_config,
            reset_sut
        )
        self.connection.daemon = True
        self.connection.start()

    def init_connection(
            self,
            stop_responses: mp.Queue[tuple[str, Any]],
            SUTConnection_config: configparser.SectionProxy,
            reset_sut
    ) -> ConnectionBaseClass:
        connection_class_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            SUTConnection_config['SUT_connection_file']
        )

        connection_class_name = os.path.splitext(
            os.path.basename(connection_class_path)
        )[0]
        connection_class: Any = util.import_class(
            'imported_SUTConnection_module',
            connection_class_path,
            connection_class_name
        )
        return connection_class(
            stop_responses,
            SUTConnection_config,
            self.inputs,
            reset_sut
        )

    def send_input(self, fuzz_input: bytes) -> None:
        self.inputs.put(fuzz_input)

    def disconnect(self) -> None:
        assert self.connection.pid is not None
        os.kill(self.connection.pid, signal.SIGUSR1)
        self.connection.join(timeout=60 * 3)

        exitcode = self.connection.exitcode
        if exitcode != 0:
            log.warn(f'Connection component exited with {exitcode=}')
