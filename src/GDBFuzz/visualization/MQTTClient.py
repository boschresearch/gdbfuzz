# This class manages MQTT connections.
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

import multiprocessing as mp

import paho.mqtt.client as mqtt

# If the visualizations are enabled in the user configuration (enable_UI
# set to True), GDBFuzz sends fuzzer stats and the plotted CFG to a
# javascript web app via MQTT. This file implements the connection to
# this web app.


class MQTTClient:
    def __init__(self, broker_hostname: str, broker_port: int):
        self.to_publish: mp.Queue[tuple[str, str]] = mp.Queue()
        self.worker = MQTTWorker(broker_hostname, broker_port, self.to_publish)
        # daemon so that it gets killed if we <CTRL>+<C> the main thread.
        self.worker.daemon = True
        self.worker.start()

    def publish(self, topic: str, message: str) -> None:
        self.to_publish.put((topic, message))


# MQTTWorker runs in a separate thread
class MQTTWorker(mp.Process):
    def __init__(self, broker_hostname: str, broker_port: int,
                 to_publish: mp.Queue[tuple[str, str]]) -> None:
        super().__init__()
        self.broker_hostname = broker_hostname
        self.broker_port = broker_port
        self.to_publish = to_publish
        self.client = mqtt.Client(transport="websockets")

    def run(self) -> None:
        self.client.connect(self.broker_hostname,
                            self.broker_port, keepalive=10)
        self.client.loop_start()
        while True:
            # Wait until messages to put onto the to_publish queue, then send
            # the message to the mqtt broker
            topic, message = self.to_publish.get()
            self.client.publish(topic, message)
