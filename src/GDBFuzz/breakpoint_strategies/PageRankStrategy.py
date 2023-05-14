#!/usr/bin/env python3
# This is the PageRank breakpoint strategy
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
from GDBFuzz.breakpoint_strategies.BreakpointStrategy import BreakpointStrategy


class PageRankStrategy(BreakpointStrategy):

    def cfg_changed(self,
                    entry_point: int,
                    cfg: nx.DiGraph,
                    exit_points: set[int],
                    reverse_cfg: nx.DiGraph) -> None:
        super().cfg_changed(entry_point, cfg, exit_points, reverse_cfg)
        self.rank = nx.algorithms.link_analysis.pagerank_alg.pagerank(cfg)
        self.all_nodes = cfg.nodes()

    # Returns None if no potential breakpoint position was found or there are
    # too many existing breakpoints.
    def get_breakpoint_address(
            self,
            covered_nodes: set[int],
            active_breakpoints: set[int],
            baseline_input: bytes
    ) -> int | None:
        candidates_set = self.all_nodes - \
            active_breakpoints - \
            covered_nodes

        candidates = list(candidates_set)

        if not candidates:
            return None

        weights = []

        for node_address in candidates:
            weights.append(self.rank[node_address])

        choice = random.choices(candidates, weights, k=1)[0]
        return choice
