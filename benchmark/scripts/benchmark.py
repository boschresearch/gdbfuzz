#!/usr/bin/env python3
# This program starts a benchmark run
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


def docker_run_command(config_in_Docker: str, container_name: str, core_id:int ) -> str:
    return f'docker run -d --name {container_name} --env CONFIG_FILE={config_in_Docker}' \
        f' --cpuset-cpus "{core_id}" ' \
        f' -v {suts_dir}:/SUTs/' \
        f' -v \"$(pwd)/{cfg_dir}:/configs/\" gdbfuzz:1.0 ' \
        f'bash -c " /gdbfuzz/src/GDBFuzz/main.py --config {config_in_Docker} ' \
        f'&& (cp /tmp/coverage_data /output/trial-0/coverage_data || :) ' \
        f'&& for f in /output/trial-0/corpus/* ; do mv \\$f \\${{f}}000 ; done ' \
        f'&& /gdbfuzz/src/analysis/replay_AFLpp_corpus.py /output/trial-0/corpus /output/trial-0/replayed_coverage_data {SUT["binary_file_path"]} "'


if len(sys.argv) < 3:
    print('Usage: ./benchmark.py '
          '/path/to/SUT_binaries_and_seeds_directory /path/to/SUTs.json')
    exit(1)

cores_available = 40
trials = 10
seconds_per_trial = 24 * 60 * 60
strategies = [
    'RandomBasicBlock',
    'RandomBasicBlockNoDom',
   # 'PageRank',
   # 'NearPath',
   # 'DominatorChild',
   # 'DominatorChildPlus',
  #  'DominatorChildPlusPageRank',
  #  'DominatorChildPlusNearPath',
    'Blackbox',
]

num_bps = [8]

#template_file = '../../src/GDBFuzz/configs/dockerTemplate.cfg'
template_file = '../../src/GDBFuzz/configs/dockerQEMUTemplate.cfg'


free_cores = set(range(cores_available))
# Names of docker containers that are currently running.
running_containers: list[tuple[str, int]] = []

suts_dir = sys.argv[1]
assert(os.path.isdir(suts_dir))


with open(sys.argv[2]) as f:
    SUTs = json.loads(f.read())

work = []
for SUT in SUTs:
    for strategy in strategies:
        for bkpts in num_bps:
            for trial_id in range(trials):
                work.append(
                    (SUT, strategy, bkpts, trial_id)
                )

timestamp = time.strftime('%Y_%m_%d-%H_%M_%S', time.localtime())
output_directory = timestamp
os.mkdir(output_directory)

# This has to be an absolute path
cfg_dir = os.path.join(output_directory, 'configs/')
if not os.path.isdir(cfg_dir):
    os.mkdir(cfg_dir)


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
        running_containers.remove((i, core_id))

        # get coverage data and fuzzer stats, then remove container
        dst = os.path.join(output_directory, i)
        ret = os.system(f'docker cp -L {i}:/output/trial-0/coverage_data {dst}')
        if ret != 0:
            # raise Exception(f'docker cp cov failed with exit code {ret}')
            print(f'docker cp cov failed with exit code {ret}')
            
        # get coverage data and fuzzer stats, then remove container
        dst1 = os.path.join(output_directory, 'replayed_' +i)
        ret1 = os.system(f'docker cp -L {i}:/output/trial-0/replayed_coverage_data {dst1}')
        if ret1 != 0:
            # raise Exception(f'docker cp cov failed with exit code {ret}')
            print(f'docker cp cov failed with exit code {ret1}')

        dst = os.path.join(output_directory, 'stats_' + i)
        ret2 = os.system(
            f'docker cp -L {i}:/output/trial-0/fuzzer_stats {dst}')
        if ret2 != 0:
            # raise Exception(f'docker cp stats failed with exit code {ret}')
            print(f'docker cp stats failed with exit code {ret2}')

        dst = os.path.join(output_directory, 'plot_' + i)
        ret3 = os.system(f'docker cp -L {i}:/output/trial-0/plot_data {dst}')
        if ret3 != 0:
            # raise Exception(f'docker cp stats failed with exit code {ret}')
            print(f'docker cp stats failed with exit code {ret3}')

        dst = os.path.join(output_directory, 'cfg_' + i)
        ret4 = os.system(f'docker cp -L {i}:/output/trial-0/cfg {dst}')
        if ret4 != 0:
            # raise Exception(f'docker cp stats failed with exit code {ret}')
            print(f'docker cp stats failed with exit code {ret4}')
            
        dst = os.path.join(output_directory, 'queue_' + i)
        ret5 = os.system(
            f'docker cp -L {i}:/output/trial-0/corpus {dst}')
        if ret5 != 0:
            # raise Exception(f'docker cp stats failed with exit code {ret}')
            print(f'docker cp stats failed with exit code {ret5}')

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

        free_cores.add(core_id)
        to_delete.remove((i, core_id))

    if not work:
        continue

    SUT, strategy, bkpts, trial_id = work.pop(0)

    # create new config, add, commit, and push
    config_file_name = f'{SUT["SUT_name"]}{strategy}_{bkpts}bp_Benchmark.cfg'
    config_file = os.path.join(
        cfg_dir, config_file_name)

    with open(template_file) as f:
        config = f.read()

    config = config.replace('BINARY_FILE_PATH', SUT['binary_file_path'])
    config = config.replace('ENTRYPOINT', SUT['entrypoint'])
    config = config.replace('MAXIMUM_INPUT_LENGHT',
                            SUT['maximum_input_length'])
    config = config.replace('TOTAL_RUNTIME', str(seconds_per_trial))
    config = config.replace('SEEDS_DIRECTORY', SUT['seeds_directory'])
    config = config.replace('MAX_BREAKPOINTS', str(bkpts))
    config = config.replace('STRATEGY', strategy)

    with open(config_file, 'w') as f:
        print(f'{config_file=}')
        f.write(config)

    container_name = f'bench{SUT["SUT_name"]}{strategy}_{bkpts}bp{trial_id}'
    config_in_docker = f'/configs/{config_file_name}'
    core_id = free_cores.pop()
    cmd = docker_run_command(config_in_docker, container_name, core_id)
    running_containers.append((container_name, core_id))
    ret = os.system(cmd)
    if ret != 0:
        print(f'error: {cmd} returned {ret}')
        raise Exception(f'{cmd} failed with exit code {ret}')


print('Benchmark done')
