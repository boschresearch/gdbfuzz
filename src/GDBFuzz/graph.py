# This file holds utility functions for graph algorithms.
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

import collections
import queue

import networkx as nx

# Returns uncovered nodes that are 1 edge away from a covered node.


def uncovered_neighbours(
        cfg: nx.DiGraph,
        coverage_map: set[int]
) -> set[int]:
    uncovered_neighbours: set[int] = set()
    for node_address in coverage_map:
        if node_address in cfg \
                and node_address >= 0:
            for destination in cfg.successors(node_address):
                if destination not in coverage_map:
                    uncovered_neighbours.add(destination)
    return uncovered_neighbours

# Returns uncovered nodes that are 1 edge away from node at 'address'.


def uncovered_neighbours_near_node(
        address: int,
        cfg: nx.DiGraph,
        coverage_map: set[int]
) -> set[int]:
    uncovered_neighbours: set[int] = set()
    if address not in cfg:
        return uncovered_neighbours
    for destination in cfg.successors(address):
        if destination not in coverage_map:
            uncovered_neighbours.add(destination)
    return uncovered_neighbours

# If 'cfg' changes, cache entries become invalid


class NodesReachableCache:
    def __init__(
            self,
            cfg: nx.DiGraph,
    ) -> None:
        self.cfg = cfg
        self.entries: dict[int, int] = {}

    def set(self, key: int, value: int) -> None:
        self.entries[key] = value

    def get(self, key: int) -> int:
        if key in self.entries:
            return self.entries[key]

        nr = nodes_reachable(
            key,
            self.cfg
        )
        self.entries[key] = nr
        return nr


def nodes_reachable(
        entrypoint: int,
        cfg: nx.DiGraph
) -> int:
    assert entrypoint in cfg
    return len(nx.bfs_tree(cfg, entrypoint))


class UncoveredNodesReachableCache:
    def __init__(
            self,
            cfg: nx.DiGraph,
            covered_nodes: set[int]
    ) -> None:
        self.cfg = cfg
        self.covered_nodes = covered_nodes
        self.entries: dict[int, int] = {}

    def set(self, key: int, value: int) -> None:
        self.entries[key] = value

    def get(self, key: int) -> int:
        if key in self.entries:
            return self.entries[key]

        nr = uncovered_nodes_reachable(
            key,
            self.cfg,
            self.covered_nodes
        )
        self.entries[key] = nr
        return nr


def uncovered_nodes_reachable(
        entrypoint: int,
        cfg: nx.DiGraph,
        covered_nodes: set[int]
) -> int:
    assert entrypoint in cfg
    todo: queue.Queue[int] = queue.Queue()

    visited = set()
    todo.put(entrypoint)
    while todo.qsize():
        node = todo.get(block=False)
        for destination in cfg.successors(node):
            if (
                destination not in visited and
                destination not in covered_nodes
            ):
                todo.put(destination)
                visited.add(destination)
    return len(visited)


def edges_reachable(
        entrypoint: int,
        cfg: nx.DiGraph
) -> int:
    num_edges = 0
    assert entrypoint in cfg
    todo: queue.Queue[int] = queue.Queue()
    visited = set()
    todo.put(entrypoint)
    while todo.qsize():
        node = todo.get(block=False)
        # out_degree is the number of edges pointing out of the node.
        num_edges += cfg.out_degree(node)
        for destination in cfg.successors(node):
            if (
                destination not in visited
            ):
                todo.put(destination)
                visited.add(destination)
    return num_edges


def edges_to_target(
        cfg: nx.DiGraph,
        target_address: int,
        coverage_map: set[int]
) -> list[int]:
    """Return the addresses of all covered basic blocks that have an outgoing
    edge to 'target_address'.
    """
    ret = []
    for bb_address in coverage_map:
        for destination in cfg.successors(bb_address):
            if destination == target_address:
                ret.append(bb_address)
                break
    return ret


def get_parents(
        entrypoint: int,
        cfg: nx.DiGraph
) -> dict[int, int]:
    """For each node, get the nodes' parent address.
    Returned dictionary keys are node addresses, the value is the address
    of the key's parent node.
    """
    ret: dict[int, int] = {}
    assert entrypoint in cfg
    todo: queue.Queue[int] = queue.Queue()
    visited = set()
    todo.put(entrypoint)
    while todo.qsize():
        node = todo.get(block=False)
        for destination in cfg.successors(node):
            if (
                destination not in visited
            ):
                todo.put(destination)
                visited.add(destination)
                ret[destination] = node
    return ret


def pre_dominator_graph(G: nx.DiGraph, entry_point):
    return nx.DiGraph(nx.immediate_dominators(G, entry_point).items()).reverse(copy=False)


def post_dominator_graph(reverse_cfg: nx.DiGraph, exit_points: set):
    # Add a virtual exit point, since we can have multiple exit nodes
    exit_edges = [(-42, n) for n in exit_points]

    reverse_cfg.add_edges_from(exit_edges)

    PoD = pre_dominator_graph(reverse_cfg, -42)

    reverse_cfg.remove_node(-42)

    return PoD


def get_semi_global_dominator_graph(
        entrypoint: int,
        cfg: nx.DiGraph,
        exit_points: set[int],
        reverse_cfg: nx.DiGraph,
) -> nx.DiGraph:
    """
    Returns the dominator relation of the control flow graph.

    Args
    -----
    entrypoint : The entrypoint of the control flow graph.

    cfg: The control flow graph

    exit_points : The exit points of the control flow graph.

    reverse_cfg: The reversed control flow graph


    Returns
    -------
    The dominator relation. The artificial exit_point is '0'
    """

    PrD = pre_dominator_graph(cfg, entrypoint)

    PoD = post_dominator_graph(reverse_cfg, exit_points)

    return nx.algorithms.operators.compose(PrD, PoD)


def subgraph(G: nx.DiGraph, s: int, t: int) -> nx.DiGraph:
    paths_between = nx.all_simple_paths(G, source=s, target=t)
    nodes_between_set = {node for path in paths_between for node in path}
    return G.subgraph(nodes_between_set)


def mark_all_dominating_nodes(hit_nodes: set, marked_nodes: set, dominator_graph: nx.DiGraph):
    for node in hit_nodes:
        if node not in marked_nodes:
            marked_nodes.add(node)
            mark_all_dominating_nodes(dominator_graph.predecessors(
                node), marked_nodes, dominator_graph)


def get_dominator_tree_leaf_nodes(
    cfg: nx.DiGraph,
    entrypoint: int
) -> set[int]:
    leaf_nodes = set()

    domi_tree = nx.DiGraph()
    for dst, src in nx.immediate_dominators(cfg, entrypoint).items():
        domi_tree.add_edge(src, dst)

    for node in domi_tree:
        if len(list(domi_tree.successors(node))) == 0:
            leaf_nodes.add(node)

    return leaf_nodes


def get_dominating_childs(
    entry_point: int,
    cfg: nx.DiGraph,
    exit_points: set[int],
    reverse_cfg: nx.DiGraph,
) -> set[int]:

    childs = set()

    dom_graph = get_semi_global_dominator_graph(
        entry_point, cfg, exit_points, reverse_cfg)
    for x in dom_graph:
        if len(list(dom_graph.successors(x))) == 0:
            childs.add(x)

    return childs


def get_dominating_childs_plus(
    entry_point: int,
    cfg: nx.DiGraph,
    exit_points: set[int],
    reverse_cfg: nx.DiGraph,
) -> set[int]:

    marked = set()

    dom_graph = get_semi_global_dominator_graph(
        entry_point, cfg, exit_points, reverse_cfg)
    for x in dom_graph:
        if len(list(dom_graph.successors(x))) == 0:
            marked.add(x)

    for node in cfg:
        if node in marked:
            continue
        for succ in cfg.successors(node):
            if node not in dom_graph \
                    or succ not in dom_graph\
                    or not nx.has_path(dom_graph, node, succ):
                marked.add(node)
                break
    return marked


def dominator_tree_rank(
        entrypoint: int,
        cfg: nx.DiGraph
) -> collections.defaultdict[int, int]:
    ret: collections.defaultdict[int, int] = collections.defaultdict(lambda: 1)

    dominator_tree_edges: list[tuple[int, int]] = []
    immediate_doms = nx.immediate_dominators(cfg, entrypoint).items()
    for dst, src in immediate_doms:
        if dst == src:
            continue
        dominator_tree_edges.append((src, dst))

    dominator_tree = nx.DiGraph(
        incoming_graph_data=dominator_tree_edges
    )
    for _, src in immediate_doms:
        ret[src] = len(nx.bfs_tree(dominator_tree, src))

    return ret


def reverse_dominator_tree_rank(
        entrypoint: int,
        cfg: nx.DiGraph
) -> collections.defaultdict[int, int]:
    ret: collections.defaultdict[int, int] = collections.defaultdict(lambda: 1)

    dominator_tree_edges: list[tuple[int, int]] = []
    immediate_doms = nx.immediate_dominators(cfg, entrypoint).items()
    for src, dst in immediate_doms:
        if dst == src:
            continue
        dominator_tree_edges.append((src, dst))

    dominator_tree = nx.DiGraph(dominator_tree_edges)
    for _, src in immediate_doms:
        ret[src] = len(nx.bfs_tree(dominator_tree, src))

    return ret
