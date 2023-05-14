// This example program reads data from serial and parses it as json.
// Copyright (c) 2022 Robert Bosch GmbH
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

#include "Arduino.h"
#include <ArduinoJson.h>

#ifndef LED_BUILTIN
#define LED_BUILTIN 2
#endif

uint8_t *buf = 0;
size_t input_len = 0;
int led_state = 0;


#define FUZZ_INPUT_SIZE 2048

void setup() {
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, HIGH);
    Serial.begin(38400);

    buf = (uint8_t*)calloc(1, FUZZ_INPUT_SIZE);
    if(!buf) {
        digitalWrite(LED_BUILTIN, LOW);
        delay(1000000);
        return;
    }
}

void serial_read_bytes(uint8_t *buf, size_t length) {
    size_t bytes_read = 0;

    while (bytes_read < length) {
        if (!Serial.available()) continue;
        char byte = Serial.read();
        buf[bytes_read] = byte;
        bytes_read += 1;
    }
}

void parser(uint8_t *input, size_t input_size) {

    DynamicJsonDocument doc(FUZZ_INPUT_SIZE);
    DeserializationError ret = deserializeJson(doc, input, input_size);
    if (ret != DeserializationError::Ok)
    {
        // We could optionally also remove this DeserializationError::Ok check to se
        // how serializeJson handles DynamicJsonDocument with errors.
        return;
    }

    char buf[FUZZ_INPUT_SIZE];
    uint32_t num_bytes_written = serializeJson(doc, buf, FUZZ_INPUT_SIZE);
}

void loop() {
    if (led_state == 0) {
        digitalWrite(LED_BUILTIN, HIGH);
        led_state = 1;
    } else {
        digitalWrite(LED_BUILTIN, LOW);
        led_state = 0;
    }

    // Notify that we request a new input
    Serial.write('A');

    uint32_t response_length = 0;
    serial_read_bytes((uint8_t*)&response_length, 4);

    if (response_length > FUZZ_INPUT_SIZE)
    {
        //Serial.println("ERROR: Received input with length > 1048");
        while(1){ delay(100); }
    }
    //socket_read_bytes(connection_fd, (void *)buf, response_length);
    serial_read_bytes((uint8_t*)buf, (size_t)response_length);

    parser(buf, (size_t)response_length);
}
