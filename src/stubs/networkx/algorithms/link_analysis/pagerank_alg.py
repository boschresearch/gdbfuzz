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
from __future__ import annotations

from typing import Any

import networkx as nx


def pagerank(
    G: nx.DiGraph,
    alpha: float = 0.85,
    personalization: dict[Any, Any] | None = None,
    max_iter: int = 100,
    tol: float = 1.0e-6,
    nstart: dict[Any, Any] | None = None,
    weight: str = "weight",
    dangling: dict[Any, Any] | None = None
) -> dict[int, float]:
    ...
