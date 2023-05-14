# Makefile for installing dependencies
# Copyright (c) 2019 Robert Bosch GmbH

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
.PHONY: install
install:
	pip install -e .
	cd dependencies/ && make clean && make install
	make -C src/qemu-plugins

.PHONY: dockerimage
dockerimage:
	docker build . -t gdbfuzz:1.0

