# GDBFuzz: Debugger-Driven Fuzzing


This is the companion code for the paper: 'Fuzzing Embedded Systems using Debugger Interfaces'.
The paper can be found here https://publications.cispa.saarland/3944/. The code allows the users to
reproduce and extend the results reported in the paper.  Please cite the
above paper when reporting, reproducing or extending the results.

## Folder structure

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

## Purpose of the project

The idea of __GDBFuzz__ is to leverage hardware breakpoints from microcontrollers as feedback for coverage-guided fuzzing. Therefore, GDB is used as a generic interface to enable broad applicability. For binary analysis of the firmware, Ghidra is used. The code contains a benchmark setup for evaluating the method. Additionally, an example firmware is included.

# Getting Started 
GDBFuzz enable coverage-guided fuzzing for embedded systems, but - for evaluation purposes - can also fuzz arbitrary user applications. All steps have been tested on Ubuntu 20.04 

## Install local
__GDBFuzz__ has been tested on Ubuntu 20.04 LTS and Raspberry Pie OS 32-bit
Prerequisites are java and python3. Check the Dockerfile for specific requirements.
First, create a new virtual environment and install all dependencies.
~~~
virtualenv .venv
source .venv/bin/activate
make
chmod a+x ./src/GDBFuzz/main.py
~~~

## Run locally on an example program
~~~
./src/GDBFuzz/main.py --config ./example_programs/fuzz_json.cfg
~~~
All config options are explained in the config file.

## Install and run in a Docker container
The general effectiveness of the approach is shown in a large scale benchmark deployed as docker containers.
~~~
make dockerimage
~~~

__GDBFuzz__ needs a config file and the software under test (SUT) binary. You can use a Docker volume to make these accessible inside the Docker container:
~~~
docker run -it --env CONFIG_FILE=/example_programs/fuzz_json_docker_qemu.cfg -v $(pwd)/example_programs:/example_programs gdbfuzz:1.0
~~~


# Detailed Instructions
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

For your info: platformio stored an .elf file of the SUT here: ./example_firmware/stm32_disco_arduinojson/.pio/build/disco_l4s5i_iot01a/firmware.elf This .elf file is also later used in the user configuration for Ghidra.

Start a new terminal, and run the following to start the a GDB Server:
~~~
st-util
~~~

Run GDBFuzz with a user configuration for arduinojson. We can send data over the usb port to the microcontroller. The microcontroller forwards this data via serial to the SUT'. In our case `/dev/ttyACM0` is the USB device to the microcontroller board. If your system assigned another device to the microcontroller board, change `/dev/ttyACM0` in the config file to your device.
~~~
./src/GDBFuzz/main.py --config ./example_firmware/stm32_disco_arduinojson/jsonHW.cfg
~~~

Fuzzer statistics and logs are in the ./output/... directory.




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
./src/GDBFuzz/main.py --config ./example_firmware/esp32_arduinojson/jsonHW.cfg
~~~

Fuzzer statistics and logs are in the ./output/... directory.


## GDBFuzz on the CY8CKIT-062-WiFi-BT board 

Install `pyocd`:

    pip install --upgrade pip 'mbed-ls>=1.7.1' 'pyocd>=0.16'

Make sure that 'KitProg v3' is on the device and put Board into 'Arm DAPLink' Mode by pressing the appropriate button.
Start the GDB server:

    pyocd gdbserver --persist

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

Ghidra fails to analyze binaries for the TI MSP430 controller out of the box. To fix that, we import the file in the Ghidra GUI, choose MSP430X as architecture and skip the auto analysis. Next, we open the 'Symbol Table', sort them by name and delete all symbols with names like `$C$L*`. Now the auto analysis can be executed.

## USB Fuzzing

To access USB devices as non-root user with `pyusb` we add appropriate rules to udev. Paste following lines to `/etc/udev/rules.d/50-myusb.rules`:

    SUBSYSTEM=="usb", ATTRS{idVendor}=="1234", ATTRS{idProduct}=="5678" GROUP="usbusers", MODE="666"

Reload udev:

    sudo udevadm control --reload
    sudo udevadm trigger

## Compare against Fuzzware

Create a file with valid basic blocks from a control flow graph file

    cut -d " " -f1 ./cfg > valid_bbs.txt

Replay coverage against fuzzware result
    fuzzware genstats --valid-bb-file valid_bbs.txt

## GDBFuzz on an Raspberry Pi 4a (8Gb)

1. Ghidra must be modified, such that it runs on an 32-Bit OS

In file `./dependencies/ghidra/support/launch.sh:125` The `JAVA_HOME` variable must be hardcoded therefore e.g. to `JAVA_HOME="/usr/lib/jvm/default-java"`

2. STLink must be at version >= 1.7 to work properly -> Build from sources


### Run the full Benchmark

First, build the Docker image as described previously. Next adopt the benchmark settings in `benchmark/scripts/benchmark.py` to your demands and start the benchmark with:

~~~
cd ./benchmark/benchSUTs
chmod a+x setup_benchmark_SUTs.py
make dockerbenchmarkimage
cd ../scripts
./benchmark.py $(pwd)/../benchSUTs/SUTs/ SUTs.json
~~~

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
