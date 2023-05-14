// This program enables to send and receive input data from a named pipe.
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

#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <sys/mman.h>
#include <errno.h>
#include <sys/un.h>
#include <sys/types.h>
#include <sys/stat.h>

#define PIPE_FROM_GDBFuzz_FILE "/tmp/fromGDBFuzz"
#define PIPE_TO_GDBFuzz_FILE "/tmp/toGDBFuzz"

void init_connection(int* fromGDBFuzz_fd, int* toGDBFuzz_fd) {
    *fromGDBFuzz_fd = open(PIPE_FROM_GDBFuzz_FILE, O_RDWR);
    if (*fromGDBFuzz_fd < 0) {
        perror("open error ");
        exit(62);
    }

    *toGDBFuzz_fd = open(PIPE_TO_GDBFuzz_FILE, O_RDWR);
    if (*toGDBFuzz_fd < 0) {
        perror("open error ");
        exit(63);
    }
}

// Make sure len(buf) <= length.
void fifo_read_bytes(int fd, void* buf, size_t length) {
    size_t total_bytes_read = 0;
    ssize_t bytes_read;
    while (total_bytes_read < length)   {
        bytes_read = read(fd, (void*)((uint64_t)buf + total_bytes_read), length - total_bytes_read);
        if (bytes_read <= 0) {
            if (errno == EINTR) {
                // We can get interrupted via OS signal here, in that case try again
                perror("Read from pipe failed, trying again. Error was: ");
                errno = 0;
                continue;
            }
            perror("Read from pipe failed: ");
            exit(5);
        }
        total_bytes_read += bytes_read;
    }
}

void fifo_send(int fd, void* buf, size_t length) {
    size_t total_bytes_sent = 0;
    ssize_t bytes_sent;
    while (total_bytes_sent < length) {
        bytes_sent = write(fd, (void*)((uint64_t)buf + total_bytes_sent), length - total_bytes_sent);
        if (bytes_sent <= 0) {
            perror("write to fifo failed: ");
            exit(9);
        }
        total_bytes_sent += bytes_sent;
    }
}

// Returns a pointer to a buffer that containts the input, also sets
// 'input_size' accordingly.
char* request_input(int fromGDBFuzz_fd, int toGDBFuzz_fd, size_t* input_size) {
    static char *input_buffer = NULL;
    static size_t input_buffer_len = 0;

    // Send 1 byte to request an input.
    // Response has the structure | Input Length | Input |
    // Input Length is encoded in 4 bytes, specifies Input length in bytes.

    char message = 1;
    uint32_t response_length;
    fifo_send(toGDBFuzz_fd, &message, 1);
    fifo_read_bytes(fromGDBFuzz_fd, (void *)&response_length, sizeof(response_length));

    if (response_length > input_buffer_len) {
        if (input_buffer != NULL) {
            free(input_buffer);
        }
        input_buffer_len = response_length + 256;
        input_buffer = (char*)malloc(input_buffer_len);
        if (input_buffer == NULL) {
            perror("malloc() error ");
            exit(1);
        }
    }

    *input_size = (size_t)response_length;
    fifo_read_bytes(fromGDBFuzz_fd, (void *)input_buffer, response_length);
    return input_buffer;
}
