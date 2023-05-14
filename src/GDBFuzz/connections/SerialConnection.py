# This is a connection class that sends data via a serial connection.
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
import struct

import time
import serial
from GDBFuzz.connections.ConnectionBaseClass import ConnectionBaseClass


class SerialConnection(ConnectionBaseClass):
    def connect(self, SUTConnection_config: configparser.SectionProxy) -> None:
        self.serial = serial.Serial(
            SUTConnection_config['port'],
            SUTConnection_config.getint('baud_rate',), 
            #xonxoff=0, 
            #rtscts=0
        )
        self.serial.reset_input_buffer()
        # Do a reset, so that the SUT requests an input now
        self.reset_sut()
        log.info(f'Established connection with SUT via Serial at port '
                 f'{self.serial.name}')

    def wait_for_input_request(self) -> None:
        # SUT sends 'A' whenever it requests and input
        read = ''
        while not read or read[-1] != 65:
            read = self.serial.read_all()
        log.debug(f'READ: {read}')

    def send_input(self, fuzz_input: bytes) -> None:
        # First send length
        log.debug(f"Sending input: {fuzz_input}")
        input_len = struct.pack("I", len(fuzz_input))
        self.serial.write(input_len)

        # After that input
        self.serial.write(fuzz_input)
        
        self.serial.flush()

    def disconnect(self) -> None:
        self.serial.close()
