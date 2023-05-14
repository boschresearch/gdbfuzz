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
import multiprocessing as mp
from typing import Any
import struct

import usb.core
import usb.util
from GDBFuzz.connections.ConnectionBaseClass import ConnectionBaseClass


class USBBulkTransfer(ConnectionBaseClass):



    def connect(self, SUTConnection_config: configparser.SectionProxy) -> None:
        self.is_connected = False
        self.vendorID = SUTConnection_config['vendor_ID']
        self.productID = SUTConnection_config['product_ID']
        self.reset_sut()
        time.sleep(3)


    def connect_usb(self):
        retries = 15
        self.dev = None

        while retries > 0 and self.dev is None:
            # find our device
            self.dev = usb.core.find(idVendor=int(self.vendorID,16), idProduct=int(self.productID, 16))
            retries -= 1
            time.sleep(1)


        log.info(f"Connect to USB device {self.dev}")

        # was it found?
        if self.dev is None:
            log.error('Device not found')
            return

        self.interface = self.dev[0].interfaces()[0]

        if self.dev.is_kernel_driver_active(self.interface.bInterfaceNumber):
            try:
                self.dev.detach_kernel_driver(self.interface.bInterfaceNumber)
            except usb.core.USBError as e:
                log.error(
                    f"Could not detatch kernel driver from ({self.interface}): {str(e)}")
        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        self.dev.set_configuration()


        # get an endpoint instance
        cfg = self.dev.get_active_configuration()

        usb.util.claim_interface(self.dev, self.interface)
        self.epout = usb.util.find_descriptor(
            self.interface,
            # match the first OUT endpoint
            custom_match=lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_OUT)

        self.epin = usb.util.find_descriptor(
            self.interface,
            # match the first OUT endpoint
            custom_match=lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_IN)

        assert self.epout is not None
        assert self.epin is not None



        log.info(
            f'Established connection with SUT')

        self.is_connected = True
        #time.sleep(1)



    def clear_halt(self):

        try:

            self.epin.clear_halt()
            self.epout.clear_halt()
            
            usb.control.clear_feature(self.dev, usb.control.ENDPOINT_HALT, self.epout)
            usb.control.clear_feature(self.dev, usb.control.ENDPOINT_HALT, self.epin)
        except usb.USBError as error:
            pass



    def reset(self):
        if self.dev is None:
            return
        self.dev.reset()
        
        #issue Bulk-Only Mass Storage Reset
        bmRequestType = usb.util.build_request_type(
                                usb.util.CTRL_OUT,
                                usb.util.CTRL_TYPE_CLASS,
                                usb.util.CTRL_RECIPIENT_INTERFACE )

        # Seems not to be expected by some USB Stacks
        try:
            self.dev.ctrl_transfer(
                        bmRequestType = bmRequestType,
                        bRequest = 0x0ff,
                        wIndex = 0 )

        except usb.core.USBError as e:
            log.debug(f"Reset  Error: {e}")
            # So reset device if it didn't worked
            self.dev.reset()

        #Get Max LUN ctrl request
        bmRequestType = usb.util.build_request_type(
                                usb.util.CTRL_IN,
                                usb.util.CTRL_TYPE_CLASS,
                                usb.util.CTRL_RECIPIENT_INTERFACE )

        self.dev.ctrl_transfer(
                    bmRequestType = bmRequestType,
                    bRequest = 0x0fe,
                    wValue=0,
                    wIndex = 0,
                    data_or_wLength = 1, 
                    timeout = None
                    )


    def wait_for_input_request(self) -> None:
        """Blocks until SUT can receive input"""
        pass



    def send(self,  data):
        '''
        Send data on pipe
        
        @type    data: string
        @param    data: Data to send
        '''


        retry = 2
        while retry > 0:
            try:
                self.epout.write(data, timeout=1000)
                retry = 0

            except usb.core.USBError as e:

                retry -= 1
                if e.backend_error_code == -9: # LIBUSB_ERROR_PIPE
                    self.clear_halt()
                    time.sleep(0.001)

                #elif e.backend_error_code == -7 and retry == 0: # LIBUSB_ERROR_TIMEOUT 
                #    raise e
                else:
                    log.debug(f"USB Error {e.backend_error_code} when writing on EP {hex(self.epout.bEndpointAddress)} ")
        

    def receive(self, size = None) -> bytes:

        if size is None:
            size = 0x1000
            
        data = b""
        retry = 2
        while retry > 0:
            try:
                data = self.epin.read(size, timeout=100)
                retry = 0
            except usb.core.USBError as e:
                retry -= 1
                if e.backend_error_code == -9: # LIBUSB_ERROR_PIPE

                    self.clear_halt()
                    time.sleep(0.001)
                # We don't care about receive timeouts,
                # because they can be caused from incomplete data while fuzzing
                #elif e.backend_error_code == -7 and retry == 0: # LIBUSB_ERROR_TIMEOUT
                #    raise e
                else:
                    log.debug(f"USB Error {e.backend_error_code} when reading on EP {hex(self.epout.bEndpointAddress)} ")

        return data

    def send_input(self, fuzz_input: bytes) -> None:
        if not self.is_connected:
            self.connect_usb()
        self.reset()
        
        # First send length
        already_sent = 0
        while already_sent +1 < len(fuzz_input):


            packet_len = struct.unpack("<H", fuzz_input[already_sent:already_sent + 2])[0]
            already_sent += 2
            fuzz_data_left = len(fuzz_input[already_sent :])
            if packet_len <= 0:
                continue
            if fuzz_data_left < packet_len:
                packet = fuzz_input[already_sent :] + bytearray(packet_len - fuzz_data_left)
            else:
                packet = fuzz_input[already_sent : already_sent + packet_len]
            already_sent += packet_len
            self.send(packet)
            log.debug(f"Data OUT, {len(packet)} bytes")
            res = self.receive()
            log.debug(f"Data IN, {len(res)} bytes")


    def disconnect(self) -> None:
        log.info("Disconnect!")
        if self.interface and \
            self.dev:
            usb.util.release_interface(self.dev, self.interface)        
        self.is_connected = False
        self.epin = None
        self.epout = None
        self.dev = None
