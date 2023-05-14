#!/usr/bin/env python3
# This is the DominatorChildPlusNearPath breakpoint strategy
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
import random
from collections import Counter
from collections import defaultdict
from typing import Any

import networkx as nx
from GDBFuzz import graph
from GDBFuzz.breakpoint_strategies.BreakpointStrategy import BreakpointStrategy


class DominatorChildPlusNearPathStrategy(BreakpointStrategy):
    def __init__(
            self,
            entry_point: int,
            cfg: nx.DiGraph,
            exit_points: set[int],
            reverse_cfg: nx.DiGraph,
            bp_strategy_config: configparser.SectionProxy,
    ):
        super().__init__(entry_point,
                         cfg,
                         exit_points,
                         reverse_cfg,
                         bp_strategy_config)

        # Store inverted path lenghts from reached nodes \
        # from specific inputs
        self.input_to_inverted_path_lenghts: \
            defaultdict[bytes, list[Counter[Any]]] = defaultdict(list)

    def cfg_changed(self,
                    entry_point: int,
                    cfg: nx.DiGraph,
                    exit_points: set[int],
                    reverse_cfg: nx.DiGraph) -> None:
        super().cfg_changed(entry_point, cfg, exit_points, reverse_cfg)
        self.all_nodes = cfg.nodes()

        self.br_candidates = graph.get_dominating_childs_plus(
            entry_point,
            cfg,
            exit_points,
            reverse_cfg,
        )

    def get_nodes_near_path(
            self,
            candidates: set[int],
            baseline_input: bytes
    ) -> int | None:
        if baseline_input not in self.input_to_inverted_path_lenghts:
            return None

        # Keep only nodes that are in our candidates
        candidates_inverted_path_lengths = \
            {k: self.input_to_inverted_path_lenghts[k]
             for k in self.input_to_inverted_path_lenghts if k in candidates}

        # Check if candiates left
        if not candidates_inverted_path_lengths:
            return None

        # unzip nodes -> weights
        connected_nodes, weights = zip(
            *candidates_inverted_path_lengths.items()
        )

        # Choose weighted to inverted path lengths
        choice = random.choices(connected_nodes, weights)[0]
        return choice

    # Returns None if no potential breakpoint position was found
    def get_breakpoint_address(
            self,
            covered_nodes: set[int],
            active_breakpoints: set[int],
            baseline_input: bytes
    ) -> int | None:
        candidates_set = self.br_candidates - \
            active_breakpoints - \
            covered_nodes

        if not candidates_set:
            return None

        node_near_path: int | None = self.get_nodes_near_path(
            candidates_set,
            baseline_input
        )

        if node_near_path is not None:
            return node_near_path
        else:
            return random.choice(list(candidates_set))

    def report_address_reached(
            self,
            current_input: bytes,
            address: int
    ) -> None:
        # Accumulate shortest path lengths from all prev hit nodes for the
        # input
        path_lenths = nx.single_source_shortest_path_length(self.cfg, address)

        # Sometimes it is possible, that nodes are \
        # not included in the reverse cfg
        if address in self.reverse_cfg:
            path_lenths.update(nx.single_source_shortest_path_length(
                self.reverse_cfg, address))

        # Invert path_lens to prefer shorter ones
        inverted_path_lengths = \
            {node: 1 / len for node, len in path_lenths.items() if len != 0}
        self.input_to_inverted_path_lenghts[current_input] += \
            Counter(inverted_path_lengths)
