# Benchmarking GDBFuzz

Compile the benchmark targets with

    make -C benchSUTs

Modify the `benchmark.py`and `SUTs.json` to your desired parameters and start the benchmark with:

    python3 ./scripts/benchmark.py <path/to/SUT_binaries_and_seeds_directory> <path/to/SUTs.json>
