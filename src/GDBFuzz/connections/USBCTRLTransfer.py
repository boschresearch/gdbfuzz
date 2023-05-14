# This is a connection class that sends data via USB Frames.
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
import time
from xxlimited import new

import usb.core
import usb.util
from GDBFuzz.connections.ConnectionBaseClass import ConnectionBaseClass


class USBCTRLTransfer(ConnectionBaseClass):
    
    def connect(self, SUTConnection_config: configparser.SectionProxy) -> None:
        self.is_connected = False
        self.vendorID = SUTConnection_config['vendor_ID']
        self.productID = SUTConnection_config['product_ID']
        self.reset_sut()
        time.sleep(1)

    
    def connect_async(self):
        retries = 15
        self.dev = None

        while retries > 0 and self.dev is None:
            time.sleep(1)
            # find our device
            self.dev = usb.core.find(idVendor=int(self.vendorID,16), idProduct=int(self.productID, 16))
            retries -= 1


        log.info(f"Connect to USB device {self.dev}")

        # was it found?
        if self.dev is None:
            raise ValueError('Device not found')

        interface = self.dev[0].interfaces()[0]

        #self.dev.reset()

        if self.dev.is_kernel_driver_active(interface.bInterfaceNumber):
            try:
                self.dev.detach_kernel_driver(interface.bInterfaceNumber)
            except usb.core.USBError as e:
                log.error(
                    f"Could not detach kernel driver from ({interface}): {str(e)}")
        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        self.dev.set_configuration()

        # get an endpoint instance
        cfg = self.dev.get_active_configuration()


        log.info(
            f'Established connection with SUT {cfg}')
        self.is_connected = True

    def wait_for_input_request(self) -> None:
        """Blocks until SUT can receive input"""
        while not self.is_connected:
            time.sleep(0.5)
        self.dev.reset()

    def send_input(self, fuzz_input: bytes) -> None:
        # First send length
        log.debug("Send input: " + str(fuzz_input))
        already_sent = 0
        new_offset = 0
        while already_sent + 8 < len(fuzz_input):
            try:
                if (fuzz_input[already_sent] & 0x80 ) : # read
                    new_offset = already_sent + 8
                    self.dev.ctrl_transfer(
                        bmRequestType = fuzz_input[already_sent],
                        bRequest = fuzz_input[already_sent + 1],
                        wValue= int.from_bytes(fuzz_input[already_sent + 2 : already_sent + 3], byteorder='little'),
                        wIndex = int.from_bytes(fuzz_input[already_sent + 4 : already_sent + 5], byteorder='little'),
                        data_or_wLength = int.from_bytes(fuzz_input[already_sent + 6 : already_sent + 7], byteorder='little'), 
                        timeout = None
                    )
                    
                else: # write
                    write_len = int.from_bytes(fuzz_input[already_sent + 6 : already_sent + 7], byteorder='little')
                    write_len = min(len(fuzz_input) - (already_sent + 8), write_len) #prevent buffer overflow
                    new_offset = already_sent + 8 + write_len
                    self.dev.ctrl_transfer(
                        bmRequestType = fuzz_input[already_sent],
                        bRequest = fuzz_input[already_sent + 1],
                        wValue= int.from_bytes(fuzz_input[already_sent + 2 : already_sent + 3], byteorder='little'),
                        wIndex = int.from_bytes(fuzz_input[already_sent + 4 : already_sent + 5], byteorder='little'),
                        data_or_wLength = fuzz_input[already_sent + 8 : already_sent + 8 + write_len], 
                        timeout = None
                    )
            except usb.USBError as error:
                #print("halt " + str(already_sent))
                #self.dev.reset()
                log.debug(error)
            already_sent = new_offset

    def disconnect(self) -> None:
        self.ep = None
