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

#ifndef NAMEDPIPE_
#define NAMEDPIPE_

void init_connection(int* fromGDBFuzz_fd, int* toGDBFuzz_fd);
void fifo_read_bytes(int fd, void* buf, size_t length);
void fifo_send(int fd, void* buf, size_t length);

char* request_input(int fromGDBFuzz_fd, int toGDBFuzz_fd, size_t* input_size);

#endif // NAMEDPIPE_
