#!/usr/bin/env python3
# This is the DominatorChild breakpoint strategy
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

import random

import networkx as nx
from GDBFuzz import graph
from GDBFuzz.breakpoint_strategies.BreakpointStrategy import BreakpointStrategy


class DominatorChildStrategy(BreakpointStrategy):

    def cfg_changed(self,
                    entry_point: int,
                    cfg: nx.DiGraph,
                    exit_points: set[int],
                    reverse_cfg: nx.DiGraph) -> None:
        super().cfg_changed(entry_point, cfg, exit_points, reverse_cfg)
        self.all_nodes = cfg.nodes()
        self.br_candidates = graph.get_dominating_childs(
            entry_point,
            cfg,
            exit_points,
            reverse_cfg,
        )

    # Returns None if no potential breakpoint position was found or there are
    # too many existing breakpoints.
    def get_breakpoint_address(
            self,
            covered_nodes: set[int],
            active_breakpoints: set[int],
            baseline_input: bytes
    ) -> int | None:

        candidates_set = self.br_candidates - \
            active_breakpoints - \
            covered_nodes
        candidates = list(candidates_set)

        if not candidates:
            return None

        choice = random.choice(candidates)
        return choice
