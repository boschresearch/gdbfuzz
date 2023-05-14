#!/usr/bin/env python3
# This program starts a benchmark run using AFL++
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
from __future__ import annotations

import json
import os
import subprocess
import sys
import time


def docker_run_command(container_name: str, command : str, core_id: int) -> str:
    return f'docker run -d --name {container_name}' \
        f' --cpuset-cpus "{core_id}" ' \
        f' --env AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1 --env AFL_SKIP_CPUFREQ=1 --env AFL_QEMU_CUSTOM_BIN=1  --env AFL_NO_AFFINITY=1' \
        f' -v {suts_dir}:/SUTs/' \
        f' gdbfuzz:1.0' \
        f' {command}'


if len(sys.argv) < 3:
    print('Usage: ./benchmark.py '
          '/path/to/SUT_binaries_and_seeds_directory /path/to/SUTs.json')
    exit(1)

cores_available = 30
trials = 10
seconds_per_trial =  24 * 60 * 60

free_cores = set(range(cores_available))
# Names of docker containers that are currently running.
running_containers: list[tuple[str, int]] = []

suts_dir = sys.argv[1]
assert(os.path.isdir(suts_dir))


with open(sys.argv[2]) as f:
    SUTs = json.loads(f.read())

work = []
for SUT in SUTs:
        for trial_id in range(trials):
            work.append(
                (SUT, trial_id)
            )

timestamp = time.strftime('%Y_%m_%d-%H_%M_%S', time.localtime())
output_directory = timestamp
os.mkdir(output_directory)

while work or running_containers:
    # check finished containers
    to_delete = []
    for running_con, core_id in running_containers:
        if os.system(f'docker ps -a | grep {running_con} | grep Exited') == 0:
            to_delete.append((running_con, core_id))
    if not to_delete and not free_cores:
        time.sleep(10)
        continue
    for i, core_id in to_delete:
        running_containers.remove((i, core_id ))

        # get coverage data and fuzzer stats, then remove container
        dst = os.path.join(output_directory, 'replayed_' +i)
        ret = os.system(f'docker cp -L {i}:/output/replayed_coverage_data {dst}')
        if ret != 0:
            # raise Exception(f'docker cp cov failed with exit code {ret}')
            print(f'docker cp cov failed with exit code {ret}')
            
        dst = os.path.join(output_directory, i)
        ret = os.system(f'docker cp -L {i}:/output/coverage_data {dst}')
        if ret != 0:
            # raise Exception(f'docker cp cov failed with exit code {ret}')
            print(f'docker cp cov failed with exit code {ret}')

        dst = os.path.join(output_directory, 'stats_' + i)
        ret2 = os.system(
            f'docker cp -L {i}:/output/default/fuzzer_stats {dst}')
        if ret2 != 0:
            # raise Exception(f'docker cp stats failed with exit code {ret}')
            print(f'docker cp stats failed with exit code {ret2}')
            
        dst = os.path.join(output_directory, 'plot_' + i)
        ret3 = os.system(
            f'docker cp -L {i}:/output/default/plot_data {dst}')
        if ret3 != 0:
            # raise Exception(f'docker cp stats failed with exit code {ret}')
            print(f'docker cp stats failed with exit code {ret3}')
            
        dst = os.path.join(output_directory, 'queue_' + i)
        ret4 = os.system(
            f'docker cp -L {i}:/output/default/queue {dst}')
        if ret4 != 0:
            # raise Exception(f'docker cp stats failed with exit code {ret}')
            print(f'docker cp stats failed with exit code {ret4}')

        # dont rm if any command failed or the container exited
        # with a status != 0
        container_exitcode = subprocess.check_output(
            ['docker', 'inspect', i, "--format='{{.State.ExitCode}}'"],
            encoding='utf-8'
        ).strip('\'\n')
        if container_exitcode != '0':
            print(f'container {i} exitcode {container_exitcode}')
        if ret2 == 0 and container_exitcode == '0':
            ret4 = os.system(f'docker rm {i}')
            if ret4 != 0:
                print(f'docker rm failed with exit code {ret4}')
        to_delete.remove((i,core_id))
        free_cores.add(core_id)

    if not work:
        continue

    SUT, trial_id = work.pop(0)

    container_name = f'bench{SUT["SUT_name"]}AFLpp{trial_id}'
    if not SUT["seeds_directory"]:
        SUT["seeds_directory"] = "/empty_seed_folder"
        
                # Start everything in a bash console
                # AFL++ commands
                # Target command
                # Replay command
    command =   f'/bin/bash -c "' \
                f'/aflpp/afl-fuzz -i {SUT["seeds_directory"]} -o /output -Q -V {seconds_per_trial} -t 10000+ -- ' \
                f'/aflpp/afl-qemu-trace -d plugin -plugin /aflpp/qemu_mode/libbbtrace.so {SUT["binary_file_path"]} AFL++ ' \
                f'&& cp /tmp/coverage_data /output/coverage_data ' \
                f'&& /gdbfuzz/src/analysis/replay_AFLpp_corpus.py /output/default/queue /output/replayed_coverage_data {SUT["binary_file_path"]} "'
                
                
                #-d plugin -plugin /gdbfuzz/src/qemu-plugins/libbbtrace.so
    core_id = free_cores.pop()
    cmd = docker_run_command(container_name, command, core_id)
    running_containers.append((container_name, core_id))
    ret = os.system(cmd)
    if ret != 0:
        print(f'error: {cmd} returned {ret}')
        raise Exception(f'{cmd} failed with exit code {ret}')


print('Benchmark done')
