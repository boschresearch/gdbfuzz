# Dockerfile for evaluating GDBFuzz
# Copyright (c) 2019 Robert Bosch GmbH
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

FROM ubuntu:20.04

ENV CONFIG_FILE=""

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3 python3-pip make clang gdb wget unzip \
	default-jdk graphviz git \
	libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev ninja-build libgss-dev  \
    git wget build-essential python3 make libstdc++-7-dev clang libz-dev autotools-dev \
    libtool libarchive-dev libpng-dev \
    ragel curl libbz2-dev libxml2-dev \
    libssl-dev liblzma-dev  libgcrypt20-dev libgss-dev \
    lsb-release software-properties-common apt-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Download AFL++
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /aflpp && \
    cd /aflpp && \
    git checkout tags/3.14c -b 3.14c

# Set AFL_NO_X86 to skip flaky tests.
RUN cd /aflpp && unset CFLAGS && unset CXXFLAGS && \
    export CC=clang && export AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && make install && \
    cd qemu_mode && sed -i 's/--disable-plugins/--enable-plugins/g' build_qemu_support.sh && \
    ./build_qemu_support.sh



# Install QEMU
RUN git clone --depth 1 -j8 --branch v6.1.1 https://github.com/qemu/qemu.git \
    && cd qemu && mkdir build && cd build \
    && ../configure --disable-system --target-list=x86_64-linux-user --enable-plugins && make -j4

# Install Ghidra
RUN wget https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_10.1.4_build/ghidra_10.1.4_PUBLIC_20220519.zip -O ghidra.zip \
    && unzip ghidra.zip \
    && mv ghidra_10.1.4_PUBLIC ghidra \
    && rm ghidra.zip

# Install ghidra-bridge
RUN pip install ghidra-bridge==0.2.5 \
    && pip install --upgrade jfx-bridge==0.9.1 \
    && python3 -m ghidra_bridge.install_server ~/ghidra_scripts

COPY ./src /gdbfuzz/src

COPY ./setup.cfg /gdbfuzz/setup.cfg
COPY ./setup.py /gdbfuzz/setup.py
COPY ./dependencies/Makefile /gdbfuzz/dependencies/Makefile

RUN cd /gdbfuzz && chmod a+x ./src/GDBFuzz/main.py && pip install -e .

# Build QEMU Plugin for tracking coverage
RUN cd /gdbfuzz/src/qemu-plugins && QEMU_DIR=/aflpp/qemu_mode/qemuafl/ make && mv libbbtrace.so /aflpp/qemu_mode/libbbtrace.so


# Build QEMU Plugin for tracking coverage
RUN cd /gdbfuzz/src/qemu-plugins && QEMU_DIR=/qemu/ make

# Build libFuzzer's Mutator
RUN cd /gdbfuzz/dependencies/ && make install_libFuzzerMutator

#Create an empty folder for targets without seeds
RUN mkdir /empty_seed_folder && echo "hi" >> /empty_seed_folder/seed

CMD cd /gdbfuzz/src/GDBFuzz && ./main.py --config ${CONFIG_FILE}
