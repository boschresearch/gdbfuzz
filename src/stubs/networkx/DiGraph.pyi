# This class contains type anotations for networkx.
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

class DiGraph:
    def __init__(self, incoming_graph_data: list[tuple[int, int]] | ItemsView[int, int] | None = None) -> None: ...
    def add_node(self, node_for_adding: int) -> None: ...
    def add_edge(self, u_of_edge: int, v_of_edge: int) -> None: ...
    def successors(self, n: int) -> list[int]: ...
    def out_degree(self, n: int) -> int: ...
    def subgraph(self, nodes: Any) -> nx.DiGraph: ...
    def predecessors(self, i: int) -> list[int]: ...
    def nodes(self) -> set[int]: ...
    def __iter__(self) -> Iterator[int]: ...
    def __contains__(self, i: int) -> bool: ...
    def __len__(self) -> int: ...
