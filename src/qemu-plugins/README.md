# QEMU plugins

The bbtrace plugin prints out a hashed fingerprint of all translated basic blocks from qemu.

## Install dependencies
```

sudo apt-get install -y git libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev ninja-build

```

## Clone qemu and compile user mode with plugins enabled
```
git clone https://github.com/qemu/qemu
cd qemu
mkdir build
cd build

../configure --disable-system --target-list=x86_64-linux-user,arm-linux-user,armeb-linux-user --enable-plugins
make -j 4

```

## Export the QEMU PATH and ML_FUZZ_PATH
```
export QEMU_PATH=/path/to/qemu
```


# compile qemu plugins
```
make -C qemu-plugins
```



## Generate bb traces with qemu

```
$QEMU_PATH/build/x86_64-linux-user/qemu-x86_64 -plugin ./qemu-plugins/libbbtrace.so -d plugin <application>
```
