# This makefile downloads and install als dependencies
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


.PHONY: install
install: install_qemu install_ghidra install_libFuzzerMutator

install_qemu:
	echo ***** Clone qemu
	git clone --depth 1 -j8 --branch v5.2.0 https://github.com/qemu/qemu.git
	echo ***** Install qemu
	cd qemu && mkdir build && cd build && ../configure --disable-system --target-list=x86_64-linux-user,arm-linux-user,armeb-linux-user --enable-plugins && make -j4


install_ghidra:
	echo ***** Download Ghidra
	wget https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_10.1.4_build/ghidra_10.1.4_PUBLIC_20220519.zip  -O ghidra.zip
	unzip ghidra.zip
	rm ghidra.zip
	mv ghidra_10.1.4_PUBLIC ghidra
	echo ***** Install Ghidra Bridge
	python3 -m ghidra_bridge.install_server ~/ghidra_scripts
	cd ghidra/Ghidra/Processors && git clone https://github.com/IridiumXOR/ghidra-xtensa Xtensa && \
	cd Xtensa && make

install_libFuzzerMutator:
	echo '***** Download libFuzzer Mutator (AFL++ git repo stores libFuzzer Mutator code)'
	git clone --branch dev https://github.com/AFLplusplus/AFLplusplus.git
	cd AFLplusplus && git checkout 550ba4d77294e61597a5259d00769c61281e0042
	cp -r AFLplusplus/custom_mutators/libfuzzer libFuzzerSrc
	echo "use our own Makefile instead of AFL++'s Makefile, because AFL++'s Makefile links in AFL++ related code which we don't need"
	cp ../src/GDBFuzz/fuzz_wrappers/libfuzzer/Makefile libFuzzerSrc/Makefile
	cd libFuzzerSrc && make -j4

clean:
	rm -rf ghidra libFuzzerSrc qemu AFLplusplus
