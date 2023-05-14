#!/usr/bin/env python3
# This script can replay input files
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
import multiprocessing as mp
import os
import queue
from typing import Any

from GDBFuzz.connections.SUTConnection import SUTConnection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config',
        required=True,
        type=str,
        help='Path to a config file.'
    )
    parser.add_argument(
        '--input_file',
        required=True,
        type=str,
        help='Path to an input file.'
    )
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        raise Exception(f'Config file at {args.config} does not exist')

    config = configparser.ConfigParser()
    config.read(args.config)

    stop_responses: mp.Queue[tuple[str, Any]] = mp.Queue()

    connection = SUTConnection(stop_responses, config['SUTConnection'], reset)

    with open(args.input_file, "rb") as input:
        input = input.read()
        print(f" Input: {input}, len: {len(input)}")
        for i in range(5):
            print(f'Try nr. {i}')
            try:
                # Raises queue.Empty if .get() times out.
                msg = stop_responses.get(block=True, timeout=30)
                
                connection.send_input(input)
            except queue.Empty:
                print('timed out')

def reset():
    pass

if __name__ == '__main__':
    raise SystemExit(main())
