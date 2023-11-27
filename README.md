# GDBFuzz: Debugger-Driven Fuzzing


This is the companion code for the paper: 'Fuzzing Embedded Systems using Debugger Interfaces'.
A preprint of the paper can be found here https://publications.cispa.saarland/3950/. The code allows the users to
reproduce and extend the results reported in the paper.  Please cite the
above paper when reporting, reproducing or extending the results.

## Folder structure
~~~
.
    ├── benchmark               # Scripts to build Google's fuzzer test suite and run experiments
    ├── dependencies            # Contains a Makefile to install dependencies for GDBFuzz
    ├── evaluation              # Raw exeriment data, presented in the paper
    ├── example_firmware        # Embedded example applications, used for the evaluation 
    ├── example_programs        # Contains a compiled example program and configs to test GDBFuzz
    ├── src                     # Contains the implementation of GDBFuzz
    ├── Dockerfile              # For creating a Docker image with all GDBFuzz dependencies installed
    ├── LICENSE                 # License
    ├── Makefile                # Makefile for creating the docker image or install GDBFuzz locally
    └── README.md               # This README file
~~~
## Purpose of the project

The idea of __GDBFuzz__ is to leverage hardware breakpoints from microcontrollers as feedback for coverage-guided fuzzing. Therefore, GDB is used as a generic interface to enable broad applicability. For binary analysis of the firmware, Ghidra is used. The code contains a benchmark setup for evaluating the method. Additionally, example firmware files are included.

# Getting Started 
GDBFuzz enables coverage-guided fuzzing for embedded systems, but - for evaluation purposes - can also fuzz arbitrary user applications. For fuzzing on microcontrollers we recommend a local installation of GDBFuzz to be able to send fuzz data to the device under test flawlessly.

## Install local
__GDBFuzz__ has been tested on Ubuntu 20.04 LTS and Raspberry Pie OS 32-bit.
Prerequisites are java and python3. First, create a new virtual environment and install all dependencies.
~~~
virtualenv .venv
source .venv/bin/activate
make
chmod a+x ./src/GDBFuzz/main.py
~~~

## Run locally on an example program
GDBFuzz reads settings from a config file with the following keys.

~~~
[SUT]
# Path to the binary file of the SUT.
# This can, for example, be an .elf file or a .bin file.
binary_file_path = <path>

# Address of the root node of the CFG.
# Breakpoints are placed at nodes of this CFG.
# e.g. 'LLVMFuzzerTestOneInput' or 'main'
entrypoint = <entrypoint>

# Number of inputs that must be executed without a breakpoint hit until
# breakpoints are rotated.
until_rotate_breakpoints = <number>


# Maximum number of breakpoints that can be placed at any given time.
max_breakpoints = <number>

# Blacklist functions that shall be ignored.
# ignore_functions is a space separated list of function names e.g. 'malloc free'.
ignore_functions = <space separated list>

# One of {Hardware, QEMU, SUTRunsOnHost}
# Hardware: An external component starts a gdb server and GDBFuzz can connect to this gdb server.
# QEMU: GDBFuzz starts QEMU. QEMU emulates binary_file_path and starts gdbserver.
# SUTRunsOnHost: GDBFuzz start the target program within GDB.
target_mode = <mode>

# Set this to False if you want to start ghidra, analyze the SUT,
# and start the ghidra bridge server manually.
start_ghidra = True


# Space separated list of addresses where software breakpoints (for error
# handling code) are set. Execution of those is considered a crash.
# Example: software_breakpoint_addresses = 0x123 0x432
software_breakpoint_addresses = 


# Whether all triggered software breakpoints are considered as crash
consider_sw_breakpoint_as_error = False

[SUTConnection]
# The class 'SUT_connection_class' in file 'SUT_connection_path' implements
# how inputs are sent to the SUT.
# Inputs can, for example, be sent over Wi-Fi, Serial, Bluetooth, ...
# This class must inherit from ./connections/SUTConnection.py.
# See ./connections/SUTConnection.py for more information.
SUT_connection_file = FIFOConnection.py

[GDB]
path_to_gdb = gdb-multiarch
#Written in address:port
gdb_server_address = localhost:4242

[Fuzzer]
# In Bytes
maximum_input_length = 100000
# In seconds
single_run_timeout = 20
# In seconds
total_runtime = 3600

# Optional
# Path to a directory where each file contains one seed. If you don't want to
# use seeds, leave the value empty.
seeds_directory = 

[BreakpointStrategy]
# Strategies to choose basic blocks are located in 
# 'src/GDBFuzz/breakpoint_strategies/'
# For the paper we use the following strategies
# 'RandomBasicBlockStrategy.py' - Randomly choosing unreached basic blocks
# 'RandomBasicBlockNoDomStrategy.py' - Like previous, but doesn't use dominance relations to derive transitively reached nodes.
# 'RandomBasicBlockNoCorpusStrategy.py' - Like first, but prevents growing the input corpus and therefore behaves like blackbox fuzzing with coverage measurement.
# 'BlackboxStrategy.py', - Doesn't set any breakpoints
breakpoint_strategy_file = RandomBasicBlockStrategy.py

[Dependencies]
path_to_qemu = dependencies/qemu/build/x86_64-linux-user/qemu-x86_64
path_to_ghidra = dependencies/ghidra


[LogsAndVisualizations]
# One of {DEBUG, INFO, WARNING, ERROR, CRITICAL}
loglevel = INFO

# Path to a directory where output files (e.g. graphs, logfiles) are stored.
output_directory = ./output

# If set to True, an MQTT client sends UI elements (e.g. graphs)
enable_UI = False
~~~

An example config file is located in `./example_programs/` together with an example program that was compiled using our fuzzing harness in `benchmark/benchSUTs/GDBFuzz_wrapper/common/`. 
Start fuzzing for one hour with the following command.

~~~
chmod a+x ./example_programs/json-2017-02-12
./src/GDBFuzz/main.py --config ./example_programs/fuzz_json.cfg
~~~
We first see output from Ghidra analyzing the binary executable and susequently messages when breakpoints are relocated or hit.


## Fuzzing Output 

Depending on the specified `output_directory` in the config file, there should now be a folder `trial-0` with the following structure
~~~
.
    ├── corpus            # A folder that contains the input corpus.
    ├── crashes           # A folder that contains crashing inputs - if any.
    ├── cfg               # The control flow graph as adjacency list.
    ├── fuzzer_stats      # Statistics of the fuzzing campaign.
    ├── plot_data         # Table showing at which relative time in the fuzzing campaign which basic block was reached.
    ├── reverse_cfg       # The reverse control flow graph.
~~~

## Using Ghidra in GUI mode
By setting `start_ghidra = False` in the config file, GDBFuzz connects to a Ghidra instance running in GUI mode. Therefore, the ghidra_bridge plugin needs to be started manually from the script manager. During fuzzing, reached program blocks are highlighted in green.


## GDBFuzz on Linux user programs
For fuzzing on Linux user applications, GDBFuzz leverages the standard `LLVMFuzzOneInput` entrypoint that is used by almost all fuzzers like AFL, AFL++, libFuzzer,....
In `benchmark/benchSUTs/GDBFuzz_wrapper/common` There is a wrapper that can be used to compile any compliant fuzz harness into a standalone program that fetches input via a named pipe at `/tmp/fromGDBFuzz`.
This allows to simulate an embedded device that consumes data via a well defined input interface and therefore run GDBFuzz on any application. For convenience we created a script in `benchmark/benchSUTs` that compiles all programs from our evaluation with our wrapper as explained later. 
> **_NOTE:_** GDBFuzz is not intended to fuzz Linux user applications. Use AFL++ or other fuzzers therefore. The wrapper just exists for evaluation purposes to enable running benchmarks and comparisons on a scale!

## Install and run in a Docker container
The general effectiveness of our approach is shown in a large scale benchmark deployed as docker containers.
~~~
make dockerimage
~~~

To run the above experiment in the docker container (for one hour as specified in the config file), map the `example_programs`and `output` folder as volumes and start GDBFuzz as follows.
~~~
chmod a+x ./example_programs/json-2017-02-12
docker run -it --env CONFIG_FILE=/example_programs/fuzz_json_docker_qemu.cfg -v $(pwd)/example_programs:/example_programs -v $(pwd)/output:/output gdbfuzz:1.0
~~~
An output folder should appear in the current working directory with the structure explained above.

# Detailed Instructions
Our evaluation is split in two parts. 
1. GDBFuzz on its intended setup, directly on the hardware.
2. GDBFuzz in an emulated environment to allow independend analysis and comparisons of the results.


GDBFuzz can work with any GDB server and therefore most debug probes for microcontrollers.

## GDBFuzz vs. Blackbox (RQ1)
Regarding RQ1 from the paper, we execute GDBFuzz on different microcontrollers with different firmwares located in `example_firmware`.
For each experiment we run GDBFuzz with the `RandomBasicBlock` and with the `RandomBasicBlockNoCorpus` strategy. The latter behaves like fuzzing without feedback, but we can still measure the achieved coverage.
For answering RQ1, we compare the achieved coverage of the `RandomBasicBlock` and the `RandomBasicBlockNoCorpus` strategy.
Respective config files are in the corresponding subfolders and we now explain how to setup fuzzing on the four development boards.

## GDBFuzz on STM32  B-L4S5I-IOT01A board

GDBFuzz requires access to a GDB Server. In this case the B-L4S5I-IOT01A and its on-board debugger are used. This on-board debugger sets up a GDB server via the 'st-util' program, and enables access to this GDB server via localhost:4242.


- Install the STLINK driver [link](https://www.st.com/content/st_com/en/products/development-tools/software-development-tools/stm32-software-development-tools/stm32-utilities/stsw-link009.html)
- Connect MCU board and PC via USB (on MCU board, connect to the USB connector that is labeled as 'USB STLINK')


~~~
sudo apt-get install stlink-tools gdb-multiarch
~~~


Build and flash a firmware for the STM32 B-L4S5I-IOT01A, for example the arduinojson project.

Prerequisite: Install [platformio (pio)](https://docs.platformio.org/en/latest//core/installation.html#super-quick-mac-linux)
~~~
cd ./example_firmware/stm32_disco_arduinojson/
pio run --target upload
~~~

For your info: platformio stored an .elf file of the SUT here: `./example_firmware/stm32_disco_arduinojson/.pio/build/disco_l4s5i_iot01a/firmware.elf` This .elf file is also later used in the user configuration for Ghidra.

Start a new terminal, and run the following to start the a GDB Server:
~~~
st-util
~~~

Run GDBFuzz with a user configuration for arduinojson. We can send data over the usb port to the microcontroller. The microcontroller forwards this data via serial to the SUT'. In our case `/dev/ttyACM0` is the USB device to the microcontroller board. If your system assigned another device to the microcontroller board, change `/dev/ttyACM0` in the config file to your device.
~~~
./src/GDBFuzz/main.py --config ./example_firmware/stm32_disco_arduinojson/fuzz_serial_json.cfg
~~~

Fuzzer statistics and logs are in the ./output/... directory.


## GDBFuzz on the CY8CKIT-062-WiFi-BT board 

Install `pyocd`:

    pip install --upgrade pip 'mbed-ls>=1.7.1' 'pyocd>=0.16'

Make sure that 'KitProg v3' is on the device and put Board into 'Arm DAPLink' Mode by pressing the appropriate button.
Start the GDB server:

    pyocd gdbserver --persist
    
Flash a firmware and start fuzzing e.g. with 
~~~
gdb-multiarch
    target remote :3333
    load ./example_firmware/CY8CKIT_json/mtb-example-psoc6-uart-transmit-receive.elf
    monitor reset
./src/GDBFuzz/main.py --config ./example_firmware/CY8CKIT_json/fuzz_serial_json.cfg
~~~
## GDBFuzz on ESP32 and Segger J-Link

- Install the [ESP32 SDK](https://docs.espressif.com/projects/esp-idf/en/v4.4.1/esp32/get-started/index.html#installation-step-by-step)


Build and flash a firmware for the ESP32, for instance the arduinojson example with platformio.

~~~
cd ./example_firmware/esp32_arduinojson/
pio run --target upload
~~~

Add following line to the openocd config file for the J-Link debugger: `jlink.cfg`

~~~
adapter speed 10000
~~~


Start a new terminal, and run the following to start the GDB Server:
~~~
get_idf
openocd -f interface/jlink.cfg -f target/esp32.cfg -c "telnet_port 7777" -c "gdb_port 8888"
~~~

Run GDBFuzz with a user configuration for arduinojson. We can send data over the usb port to the microcontroller. The microcontroller forwards this data via serial to the SUT'. In our case `/dev/ttyUSB0` is the USB device to the microcontroller board. If your system assigned another device to the microcontroller board, change `/dev/ttyUSB0` in the config file to your device.
~~~
./src/GDBFuzz/main.py --config ./example_firmware/esp32_arduinojson/fuzz_serial.cfg
~~~

Fuzzer statistics and logs are in the ./output/... directory.



## GDBFuzz on MSP430F5529LP


Install TI MSP430 GCC from https://www.ti.com/tool/MSP430-GCC-OPENSOURCE


Start GDB Server
~~~
./gdb_agent_console libmsp430.so
~~~

or (more stable). Build mspdebug from https://github.com/dlbeer/mspdebug/ and use:

~~~
until mspdebug --fet-skip-close --force-reset tilib "opt gdb_loop True" gdb ; do sleep 1 ; done
~~~

Ghidra fails to analyze binaries for the TI MSP430 controller out of the box. To fix that, we import the file in the Ghidra GUI, choose MSP430X as architecture and skip the auto analysis. Next, we open the 'Symbol Table', sort them by name and delete all symbols with names like `$C$L*`. Now the auto analysis can be executed. After analysis, start the ghidra bridge from the Ghidra GUI manually and then start GDBFuzz.

~~~
./src/GDBFuzz/main.py --config ./example_firmware/msp430_arduinojson/fuzz_serial.cfg
~~~

## USB Fuzzing

To access USB devices as non-root user with `pyusb` we add appropriate rules to udev. Paste following lines to `/etc/udev/rules.d/50-myusb.rules`:

    SUBSYSTEM=="usb", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678" GROUP="usbusers", MODE="666"

Reload udev:

    sudo udevadm control --reload
    sudo udevadm trigger

## Compare against Fuzzware (RQ2)
In RQ2 from the paper, we compare GDBFuzz against the emulation based approach [Fuzzware](https://github.com/fuzzware-fuzzer/fuzzware). First we execute GDBFuzz and Fuzzware as described previously on the shipped firmware files.
For each GDBFuzz experiment, we create a file with valid basic blocks from the control flow graph files as follows:

    cut -d " " -f1 ./cfg > valid_bbs.txt

Now we can replay coverage against fuzzware result
    fuzzware genstats --valid-bb-file valid_bbs.txt

## Finding Bugs (RQ3)
When crashing or hanging inputs are found, the are stored in the `crashes` folder. During evaluation, we found the following three bugs:

1. An [infinite loop in the STM32 USB device stack](https://github.com/STMicroelectronics/STM32CubeL4/issues/69), caused by counting a uint8_t index variable to an attacker controllable uint32_t variable within a for loop.
2.  A [buffer overflow in the Cypress JSON parser](https://github.com/Infineon/connectivity-utilities/issues/2), caused by missing length checks on a fixed size internal buffer.
3. A [null pointer dereference in the Cypress JSON parser](https://github.com/Infineon/connectivity-utilities/issues/1), caused by missing validation checks.

## GDBFuzz on an Raspberry Pi 4a (8Gb)
GDBFuzz can also run on a Raspberry Pi host with slight modifications:

1. Ghidra must be modified, such that it runs on an 32-Bit OS

In file `./dependencies/ghidra/support/launch.sh:125` The `JAVA_HOME` variable must be hardcoded therefore e.g. to `JAVA_HOME="/usr/lib/jvm/default-java"`

2. STLink must be at version >= 1.7 to work properly -> Build from sources


## GDBFuzz on other boards
To fuzz software on other boards, GDBFuzz requires 

1. A microcontroller with hardware breakpoints and a GDB compliant debug probe
1. The firmware file.
2. A running GDBServer and suitable GDB application.
3. An entry point, where fuzzing should start e.g. a parser function or an address
4. An input interface (see `src/GDBFuzz/connections`) that triggers execution of the code at the entry point e.g. serial connection

All these properties need to be specified in the config file.

### Run the full Benchmark (RQ4 - 8)
For RQ's 4 - 8 we run a large scale benchmark.
First, build the Docker image as described previously and compile applications from  Google's [Fuzzer Test Suite](https://github.com/google/fuzzer-test-suite) with our fuzzing harness in `benchmark/benchSUTs/GDBFuzz_wrapper/common`. 

~~~
cd ./benchmark/benchSUTs
chmod a+x setup_benchmark_SUTs.py
make dockerbenchmarkimage
~~~

Next adopt the benchmark settings in `benchmark/scripts/benchmark.py` and `benchmark/scripts/benchmark_aflpp.py` to your demands (especially `number_of_cores`, `trials`, and `seconds_per_trial`) and start the benchmark with:


~~~
cd ./benchmark/scripts
./benchmark.py $(pwd)/../benchSUTs/SUTs/ SUTs.json
./benchmark_aflpp.py $(pwd)/../benchSUTs/SUTs/ SUTs.json
~~~

A folder appears in `./benchmark/scripts` that contains plot files (coverage over time), fuzzer statistic files, and control flow graph files for each experiment as in `evaluation/fuzzer_test_suite_qemu_runs`. 


## [Optional] Install Visualization and Visualization Example

GDBFuzz has an optional feature where it plots the control flow graph of covered nodes. This is disabled by default. You can enable it by following the instructions of this section and setting 'enable_UI' to 'True' in the user configuration.

On the host:

Install
~~~
sudo apt-get install graphviz
~~~

Install *a recent version of* node, for example *Option 2* from [here](https://www.digitalocean.com/community/tutorials/how-to-install-node-js-on-ubuntu-20-04-de). Use Option 2 and *not* option 1. This should install both node and npm. For reference, our version numbers are (but newer versions should work too):
~~~
➜ node --version
v16.9.1
➜ npm --version
7.21.1
~~~

Install web UI dependencies:
~~~
cd ./src/webui
npm install
~~~

Install mosquitto MQTT broker, e.g. see [here](http://www.steves-internet-guide.com/install-mosquitto-linux/)

Update the mosquitto broker config: Replace the file /etc/mosquitto/conf.d/mosquitto.conf with the following content:
~~~
listener 1883
allow_anonymous true

listener 9001
protocol websockets
~~~

Restart the mosquitto broker:
~~~
sudo service mosquitto restart
~~~

Check that the mosquitto broker is running:
~~~
sudo service mosquitto status
~~~
The output should include the text 'Active: active (running)'

Start the web UI:

~~~
cd ./src/webui
npm start
~~~
Your web browser should open automatically on 'http://localhost:3000/'.

Start GDBFuzz and use a user config file where enable_UI is set to True. You can use the Docker container and arduinojson SUT from above. But make sure to set 'enable_UI' to 'True'.


The nodes covered in 'blue' are covered. White nodes are not covered. We only show uncovered nodes if their parent is covered (drawing the complete control flow graph takes too much time if the control flow graph is large).


## License

GDBFuzz is open-sourced under the AGPL-3.0 license. See the
[LICENSE](LICENSE) file for details.

For a list of other open source components included in GDBFuzz, see the
file [3rd-party-licenses.txt](3rd-party-licenses.txt).
