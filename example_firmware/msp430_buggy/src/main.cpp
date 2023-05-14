/*
 * Blink
 * Turns on an LED on for one second,
 * then off for one second, repeatedly.
 */


#include <Arduino.h>
#include <msp430.h>

#define FUZZ_INPUT_SIZE 1024

char buf[FUZZ_INPUT_SIZE];
size_t input_len = 0;
int led_state = 0;

void setup() {
    pinMode(RED_LED, OUTPUT);
    digitalWrite(RED_LED, HIGH);
    Serial.begin(115200);

    WDTCTL = WDTPW | WDTHOLD; // Stop watchdog timer



}

void serial_read_bytes(char *buf, size_t length) {
    size_t bytes_read = 0;

    while (bytes_read < length) {
        if (!Serial.available()) continue;
        char byte = Serial.read();
        buf[bytes_read] = byte;
        bytes_read += 1;
    }
}

void process_data(char* buffer, unsigned int length) {
	char stack_array[20];

	if( length > 0 && buffer[0] == 'b') 
		if( length > 1 && buffer[1] == 'u') 
			if( length > 2 && buffer[2] == 'g') 
				if( length > 3 && buffer[3] == '!') {
					memcpy(stack_array, buffer, length);
                    Serial.write(stack_array[3]);
				}
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
    serial_read_bytes((char*)&response_length, 4);

    if (response_length > FUZZ_INPUT_SIZE)
    {
        //Serial.println("ERROR: Received input with length > 1048");
        while(1){ delay(100); }
    }
    //socket_read_bytes(connection_fd, (void *)buf, response_length);
    serial_read_bytes(buf, (size_t) response_length);

    process_data(buf, response_length);
}
