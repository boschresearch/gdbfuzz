#!/usr/bin/env python3
# This is the abstract breakpoint strategy class
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

import configparser
from abc import ABC
from abc import abstractmethod

import networkx as nx


class BreakpointStrategy(ABC):
    def __init__(
            self,
            entry_point: int,
            cfg: nx.DiGraph,
            exit_points: set[int],
            reverse_cfg: nx.DiGraph,
            bp_strategy_config: configparser.SectionProxy,
    ) -> None:
        self.cfg_changed(entry_point, cfg, exit_points, reverse_cfg)

    def cfg_changed(self,
                    entry_point: int,
                    cfg: nx.DiGraph,
                    exit_points: set[int],
                    reverse_cfg: nx.DiGraph) -> None:
        self.entry_point = entry_point
        self.cfg = cfg
        self.exit_points = exit_points
        self.reverse_cfg = reverse_cfg

    def report_address_reached(
            self,
            current_input: bytes,
            address: int
    ) -> None:
        pass
    
    @staticmethod
    def mark_dominated_nodes() -> bool:
        return True
    
    @staticmethod
    def coverage_guided() -> bool:
        return True

    # Return the address of a potential breakpoint position.
    # Return None if no potential breakpoint position was found

    @abstractmethod
    def get_breakpoint_address(
            self,
            covered_nodes: set[int],
            active_breakpoints: set[int],
            baseline_input: bytes
    ) -> int | None:
        pass
