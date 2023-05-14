# This makefile builds the QEMU plugin.
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


ifndef QEMU_DIR
override QEMU_DIR = ../../dependencies/qemu
endif

# The following snippet is from QEMU v6.2.0
#   (https://github.com/qemu/qemu/blob/v6.2.0/contrib/plugins/Makefile)
# Copyright (c) 2012-2014 Awesome Inc., licensed under the GNU General Public License,
# cf. 3rd-party-licenses.txt file in the root directory of this source tree.

BUILD_DIR := $(QEMU_DIR)/build

include $(BUILD_DIR)/config-host.mak

VPATH += $(QEMU_DIR)/contrib/plugins

NAMES :=
NAMES += bbtrace
SONAMES := $(addsuffix .so,$(addprefix lib,$(NAMES)))

# The main QEMU uses Glib extensively so it's perfectly fine to use it
# in plugins (which many example do).
CFLAGS = $(GLIB_CFLAGS)
CFLAGS += -fPIC
CFLAGS += -O3
CFLAGS += -I$(QEMU_DIR)/include/qemu


all: $(SONAMES)

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

lib%.so: %.o
	$(CC) -shared -Wl,-soname,$@ -o $@ $^ $(LDLIBS)

debug: CFLAGS += -DDEBUG -g
debug: $(SONAMES)

clean:
	rm -f *.o *.so *.d
	rm -Rf .libs

.PHONY: all clean
