/*
 * Blink
 * Turns on an LED on for one second,
 * then off for one second, repeatedly.
 */


#include <Arduino.h>
#include "jsmn.h"
#include <msp430.h>

#define FUZZ_INPUT_SIZE 1024

uint8_t buf[FUZZ_INPUT_SIZE];
size_t input_len = 0;
int led_state = 0;

void setup() {
    pinMode(RED_LED, OUTPUT);
    digitalWrite(RED_LED, HIGH);
    Serial.begin(115200);

    WDTCTL = WDTPW | WDTHOLD; // Stop watchdog timer
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



int parser(uint8_t *input, size_t input_size)
{
  if (input_size > FUZZ_INPUT_SIZE)
    return -1;

  int i;
  int r;
  jsmn_parser p;
  jsmntok_t t[FUZZ_INPUT_SIZE];

  jsmn_init(&p);
  r = jsmn_parse(&p, (char*) input, input_size, t,
                 sizeof(t) / sizeof(t[0]));


  return r;
}

void loop() {
    if (led_state == 0) {
        digitalWrite(RED_LED, HIGH);
        led_state = 1;
    } else {
        digitalWrite(RED_LED, LOW);
        led_state = 0;
    }

    // Notify that we request a new input
    Serial.write('A');

    uint32_t response_length = 0;
    serial_read_bytes((uint8_t*)&response_length, 4);

    if (response_length > FUZZ_INPUT_SIZE)
    {
        //Serial.println("ERROR: Received input with length > 1048");
        return;
    }
    //socket_read_bytes(connection_fd, (void *)buf, response_length);
    serial_read_bytes((uint8_t*)buf, (size_t)response_length);

    int r = parser(buf, (size_t)response_length);

    Serial.write((char)r);
}
