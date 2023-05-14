# This is a connection class that sends data via domain sockets.
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
import os
import socket
import struct
import time

from GDBFuzz.connections.ConnectionBaseClass import ConnectionBaseClass


class DomainSocketConnection(ConnectionBaseClass):
    def connect(self, SUTConnection_config: configparser.SectionProxy) -> None:
        UDS_FILE = '/tmp/sock.uds'

        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        is_connected = False
        while not os.path.exists(UDS_FILE):
            log.info(f'Waiting for SUT to open domain socket at {UDS_FILE}')
            time.sleep(0.5)
        while not is_connected:
            # We need to wait until the SUT started, which may take a while
            try:
                self.s.connect(UDS_FILE)
                is_connected = True
            except ConnectionRefusedError as e:
                log.info(f'Waiting for SUT to open server socket {e}')
                time.sleep(0.5)
        log.info(f'Established connection with SUT at {UDS_FILE=}')

    def wait_for_input_request(self) -> None:
        # SUT sends 1 byte whenever it requests and input
        self.s.recv(1)

    def send_input(self, fuzz_input: bytes) -> None:
        # First send length
        input_len = struct.pack("I", len(fuzz_input))
        self.s.send(input_len)

        # After that input
        self.s.send(fuzz_input)

    def disconnect(self) -> None:
        self.s.close()
