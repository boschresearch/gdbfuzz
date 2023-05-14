# This Docker image is used for building the benchmark targets
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

FROM ubuntu:20.04

ENV mount_path = "/tmp/SUTs"

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
	    git wget build-essential python3 make libstdc++-7-dev clang libz-dev autotools-dev \
        automake autoconf autoconf-archive libtool libarchive-dev cmake nasm libpng-dev \
        ragel libglib2.0-dev golang-go curl libbz2-dev libxml2-dev \
        libssl-dev liblzma-dev subversion  libgcrypt20-dev libgss-dev \
        lsb-release software-properties-common apt-utils llvm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://apt.llvm.org/llvm.sh \
    && chmod +x llvm.sh \
    && export CC=clang && CXX=clang++ \
    && ./llvm.sh 12


RUN update-alternatives --install /usr/bin/clangd clangd /usr/bin/clangd-12 100 \
    && update-alternatives --install /usr/bin/clang clang /usr/bin/clang-12 100 \
    && update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-12 100 \
    && update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-12 100 


COPY . /benchSUTs


# chmod allows non-root users to delete ${mount_path} directory
CMD cd /benchSUTs && ./setup_benchmark_SUTs.py && cp -r /benchSUTs/SUT_binaries/* ${mount_path} && chmod -R o+w ${mount_path}
