#!/usr/bin/env python3
"""
Script for replaying an AFL++ corpus with our QEMU plugin
"""
import argparse
import pathlib
import subprocess
from typing import Any, Sequence, Set, List
import time
import os
import sys
import struct
from threading import Timer

PIPE_FROM_GDBFuzz_FILE = '/tmp/fromGDBFuzz'
PIPE_TO_GDBFuzz_FILE = '/tmp/toGDBFuzz'
QEMU_COVERAGE_FILE = '/tmp/coverage_data'


qemu_command = "/qemu/build/x86_64-linux-user/qemu-x86_64 -d plugin -plugin /gdbfuzz/src/qemu-plugins/libbbtrace.so "

def get_timestamp_millis_from_filename(filename: str) -> int:
    """
    Extracts the timestamp that AFL++ encodes into the filenames of the queue files.

    Args:
        filename: Full path to the seed.
    """
    for token in filename.split(","):
        key_val = token.split(":")
        if key_val[0] == "time":
            return int(key_val[1])

    return 0


def main(argv: Sequence[str] = tuple(sys.argv)) -> None:
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("input", help="path to input corpus", type=str)
    parser.add_argument("output", help="path and name of the output plot file", type=str)
    parser.add_argument(
        "target",
        help="target program and arguments",
        type=str,
        nargs=argparse.REMAINDER,
        metavar="target [target_args]",
    )
    args = parser.parse_args(argv[1:])

    target_with_args = args.target
    queue_path = pathlib.Path(args.input)
    seed_list = [seed for seed in queue_path.glob("*") if seed.is_file() and seed.name != ".cur_input"]
    # Order by timestamp in filename
    seed_list = sorted(seed_list, key=lambda f: get_timestamp_millis_from_filename(f.name))

    out_file = open(args.output, "w")
    #out_file.write("# relative_time, edges_found\n")

    if os.path.exists(PIPE_FROM_GDBFuzz_FILE):
        os.remove(PIPE_FROM_GDBFuzz_FILE)

    if os.path.exists(PIPE_TO_GDBFuzz_FILE):
        os.remove(PIPE_TO_GDBFuzz_FILE)

    os.mkfifo(PIPE_FROM_GDBFuzz_FILE, 0o777)
    os.mkfifo(PIPE_TO_GDBFuzz_FILE, 0o777)

    if os.path.exists(QEMU_COVERAGE_FILE):
        os.remove(QEMU_COVERAGE_FILE)   



    reached_bbs = set()

    for seed in seed_list:
        
        qemu_process = subprocess.Popen(
            qemu_command.split() + target_with_args,
           
        )
    

        fifo_to_GDBFuzz = open(PIPE_TO_GDBFuzz_FILE, 'rb')
        fifo_from_GDBFuzz = open(PIPE_FROM_GDBFuzz_FILE, 'wb')


        print(f"replay {seed}")
        with open(seed, 'rb') as seed_file:

            timer = Timer(10, qemu_process.kill)
            timer.start()
            fifo_to_GDBFuzz.read(1) #blocking read
            
            seed_content = seed_file.read()
            input_len = struct.pack("I", len(seed_content))
            fifo_from_GDBFuzz.write(input_len)
            fifo_from_GDBFuzz.write(seed_content)
            fifo_from_GDBFuzz.flush()
            
            fifo_to_GDBFuzz.read(1) #blocking read
            with open(QEMU_COVERAGE_FILE, "r") as coverage_file:
                for line in coverage_file.readlines():
                    line = line.rstrip('\n')
                    epoch_s, addr_s = line.split()
                    addr = int(addr_s, 16)
                    if addr not in reached_bbs:
                        reached_bbs.add(addr)
                        out_file.write(
                            f"{int(get_timestamp_millis_from_filename(seed.name) / 1000)} {addr_s}\n"
                        )

        fifo_from_GDBFuzz.close()
        fifo_to_GDBFuzz.close()
        
        qemu_process.kill()
        qemu_process.communicate()

    if os.path.exists(PIPE_FROM_GDBFuzz_FILE):
        os.remove(PIPE_FROM_GDBFuzz_FILE)

    if os.path.exists(PIPE_TO_GDBFuzz_FILE):
        os.remove(PIPE_TO_GDBFuzz_FILE)
        
    qemu_process.terminate()
    out_file.close()

if __name__ == "__main__":
    main()
