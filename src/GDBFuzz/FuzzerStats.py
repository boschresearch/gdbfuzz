# This class holds statistics of the fuzzing process.
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

import attr


@attr.s(auto_attribs=True)
class FuzzerStats:
    # In epoch time
    start_time_epoch: int = 0
    end_time_epoch: int = 0

    # In Human Readable format
    start_time: str = ''

    # runtime in seconds
    runtime: int = 0

    # lower-bound for basic blocks reached
    coverage: int = 0

    # crashes detected
    crashes: int = 0

    # timeouts detected
    timeouts: int = 0

    # Number of breakpoint interuptions handled
    breakpoint_interruptions: int = 0

    # Number of inputs sent to the fuzzer
    runs: int = 0

    runs_per_sec: float = 0

    # list of dict with keys: timestamp, total_basic_blocks, total_edges
    # number of basic blocks and nodes are those of the cfg with entrypoint
    # as root node of this cfg
    cfg_updates: list[dict[str, int]] = []

    # Path to the config file which was used for this run
    config_file_path: str = ''
    
    # Current corpus state
    corpus_state: list[str] = []
