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

from .DiGraph import DiGraph as DiGraph
from .algorithms.link_analysis import pagerank_alg
from . import algorithms as algorithms

def immediate_dominators(G: DiGraph, start: int) -> dict[int, int]: ...
def bfs_tree(G: DiGraph, source: int) -> DiGraph: ...
def edge_bfs(G: DiGraph, source: int) -> Iterator[tuple[int, int]]: ...
def all_simple_paths(G: DiGraph, source: int, target: int) -> Any: ...
def single_source_shortest_path_length(G: DiGraph, source: int) -> dict[int, int]: ...
