#!/usr/bin/env python3
# This is the main file to start GDBFuzz.
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

import argparse
import configparser
import logging as log
import os
import pathlib
import time
from configparser import ConfigParser
from hashlib import new

import GDBFuzz.binary_operations.BinaryOperations as BinaryOps
from GDBFuzz.GDBFuzzer import GDBFuzzer


def uniquify(path):
    counter = 0

    new_path = path

    while True:
        new_path = path + "-" + str(counter)
        counter += 1
        if not os.path.exists(new_path):
            return new_path

    return path


def create_output_directory(output_directory_base: str) -> str:
    output_directory = uniquify(output_directory_base + "/trial")
    pathlib.Path(output_directory).mkdir(parents=True, exist_ok=True)
    return output_directory


def setup_logging(output_directory: str, loglevel: str) -> None:

    logger = log.getLogger()
    formatter = log.Formatter(
        '%(asctime)s [%(levelname)s %(filename)s:%(lineno)s '
        '%(funcName)s()] %(message)s'
    )

    file_logger = log.FileHandler(
        os.path.join(output_directory, 'out.log')
    )
    file_logger.setLevel(loglevel)
    file_logger.setFormatter(formatter)
    logger.addHandler(file_logger)

    stdout_logger = log.StreamHandler()
    stdout_logger.setLevel(loglevel)
    stdout_logger.setFormatter(formatter)
    logger.addHandler(stdout_logger)

    log.root.setLevel(loglevel)


def entrypoint_to_int(config: ConfigParser) -> int:
    """ Convert entrypoint to an integer.

    The user can specify the entrypoint as a decimal number,
    hex number, or the user can specify a symbol name.
    This function converts all of these to an integer, and returns
    this integer.
    """
    entrypoint: str = config['SUT']['entrypoint']
    if entrypoint.isdigit():
        return int(entrypoint)

    # Check it entrypoint is in hex
    try:
        entrypoint_i = int(entrypoint, 16)
        return entrypoint_i
    except ValueError:
        pass

    # Lastly, check if the entrypoint is the name of a symbol
    # This only works if the SUT is an ELF file
    binary_file = config['SUT']['binary_file_path']
    if BinaryOps.file_is_elf(binary_file):
        # Get symbol address
        entrypoint_set = BinaryOps.get_function_addresses(
            binary_file,
            [entrypoint]
        )
        if entrypoint_set:
            return list(entrypoint_set)[0]

    raise Exception('User config error: {entrypoint=} does not exist.')


def process_entrypoint(config: ConfigParser) -> str:
    """Parse entrypoint to a decimal number.

    The use could e.g. specify the entrypoint in hex or as a symbol name
    """
    entrypoint = entrypoint_to_int(config)

    if config['SUT'].getboolean('SUT_is_arm_thumb'):
        # entrypoints may be ARM THUMB encoded, meaning that '1' is added
        # to the entrypoint. Remove this '1' in this case.
        entrypoint = entrypoint - (entrypoint % 2)

    return str(entrypoint)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config',
        required=True,
        type=str,
        help='Path to a config file.'
    )
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        raise Exception(f'Config file at {args.config} does not exist')

    config = configparser.ConfigParser()
    config.read(args.config)

    output_directory = create_output_directory(
        config['LogsAndVisualizations']['output_directory']
    )

    config['LogsAndVisualizations']['output_directory'] = output_directory

    setup_logging(
        config['LogsAndVisualizations']['output_directory'],
        config['LogsAndVisualizations']['loglevel']
    )

    # 'software_breakpoint_addresses' is an optional user config setting.
    # Note that we can always detect e.g. timeouts when e.g. the default
    # arduino fault handler is triggered.
    if 'software_breakpoint_addresses' not in config['SUT']:
        log.info('No software breakpoint in user configuration specified')
        config['SUT']['software_breakpoint_addresses'] = ''

    # Expand user home directory '~' in paths
    config['SUT']['binary_file_path'] = os.path.expanduser(
        config['SUT']['binary_file_path']
    )
    config['Fuzzer']['seeds_directory'] = os.path.expanduser(
        config['Fuzzer']['seeds_directory']
    )

    # Convert entrypoint to a decimal number.
    config['SUT']['entrypoint'] = process_entrypoint(config)

    log.info(f'Using configfile {args.config}')

    GDBFuzzer(config, args.config)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
