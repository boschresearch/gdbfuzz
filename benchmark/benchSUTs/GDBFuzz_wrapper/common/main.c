// This program enables to execute fuzz targets that read input data from a named pipe.
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


#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>

#include "namedpipe.h"


// libFuzzer interface is thin, so we don't include any libFuzzer headers.

// libFuzzer interface is thin, so we don't include any libFuzzer headers.
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);
__attribute__((weak)) int LLVMFuzzerInitialize(int *argc, char ***argv);


// Following code is copied from AFL++ afl_qemu_driver.c
#define kMaxAflInputSize (1 * 1024 * 1024)
static uint8_t AflInputBuf[kMaxAflInputSize];

void __attribute__((noinline)) afl_qemu_driver_stdin_input(void) {

  size_t l = read(0, AflInputBuf, kMaxAflInputSize);
  LLVMFuzzerTestOneInput(AflInputBuf, l);

}

int main(int argc, char *argv[]) {
    size_t input_len = 0;
    int fromGDBFuzz_fd;
    int toGDBFuzz_fd;

 
    if (LLVMFuzzerInitialize) LLVMFuzzerInitialize(&argc, &argv);

    if (argc == 1) { //Per default we read from named pipe
       init_connection(&fromGDBFuzz_fd, &toGDBFuzz_fd);

        for (;;) {
            char *buf = request_input(fromGDBFuzz_fd, toGDBFuzz_fd, &input_len);

            if (input_len == 0) continue;

            LLVMFuzzerTestOneInput((const uint8_t*)buf, (size_t)input_len);
        }
    } else if (argc == 2 && strcmp(argv[1], "AFL++") == 0) { // For AFL ++ we expect it as CLI arg

        afl_qemu_driver_stdin_input();

  }
 

    return 0;
}

