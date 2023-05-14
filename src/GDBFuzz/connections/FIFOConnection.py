# This is a connection class that sends data via named pipes.
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
import struct
import time
import signal
import multiprocessing as mp
from matplotlib.pyplot import connect
from GDBFuzz.connections.ConnectionBaseClass import ConnectionBaseClass


class FIFOConnection(ConnectionBaseClass):

    
    def connect_async(self) -> None:
        self.connected: bool = False
        self.PIPE_FROM_GDBFuzz_FILE = '/tmp/fromGDBFuzz'
        self.PIPE_TO_GDBFuzz_FILE = '/tmp/toGDBFuzz'

        if os.path.exists(self.PIPE_FROM_GDBFuzz_FILE):
            os.remove(self.PIPE_FROM_GDBFuzz_FILE)

        if os.path.exists(self.PIPE_TO_GDBFuzz_FILE):
            os.remove(self.PIPE_TO_GDBFuzz_FILE)

        os.mkfifo(self.PIPE_FROM_GDBFuzz_FILE, 0o777)
        os.mkfifo(self.PIPE_TO_GDBFuzz_FILE, 0o777)

        # Reset SUT such that it connects to the FIFO now
        self.reset_sut()

        self.fifo_from_GDBFuzz = open(self.PIPE_FROM_GDBFuzz_FILE, 'wb')
        self.fifo_to_GDBFuzz = open(self.PIPE_TO_GDBFuzz_FILE, 'rb')

        log.info(
            f'Established connection with SUT {self.PIPE_TO_GDBFuzz_FILE=}')


    def wait_for_input_request(self) -> None:
        # SUT sends 1 byte whenever it requests and input
        while self.fifo_to_GDBFuzz is None:
            # Give connection some time to start
            time.sleep(0.5)
        recv = self.fifo_to_GDBFuzz.read(1)
        assert len(recv) == 1, f'invalid recv len {len(recv)}'

    def send_input(self, fuzz_input: bytes) -> None:
        # First send length
        input_len = struct.pack("I", len(fuzz_input))
        self.fifo_from_GDBFuzz.write(input_len)

        # After that input
        self.fifo_from_GDBFuzz.write(fuzz_input)
        self.fifo_from_GDBFuzz.flush()

    def disconnect(self) -> None:
        self.fifo_from_GDBFuzz.close()
        self.fifo_to_GDBFuzz.close()

        if os.path.exists(self.PIPE_FROM_GDBFuzz_FILE):
            os.remove(self.PIPE_FROM_GDBFuzz_FILE)

        if os.path.exists(self.PIPE_TO_GDBFuzz_FILE):
            os.remove(self.PIPE_TO_GDBFuzz_FILE)
