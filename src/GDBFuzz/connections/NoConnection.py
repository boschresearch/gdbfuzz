# This is a dummy connection class.
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
import socket
import struct
import time

from GDBFuzz.connections.ConnectionBaseClass import ConnectionBaseClass


class NoConnection(ConnectionBaseClass):
    def wait_for_input_request(self) -> None:
        time.sleep(1)

    def send_input(self, fuzz_input: bytes) -> None:
        pass
