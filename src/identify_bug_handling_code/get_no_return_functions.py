#!/usr/bin/env python3
# This file holds some util functions.
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

import ghidra_bridge

# in seconds
GHIDRA_BRIDGE_RESPONSE_TIMEOUT = 600


def get_no_return_functions() -> list[int]:
    bridge = ghidra_bridge.GhidraBridge(
        response_timeout=GHIDRA_BRIDGE_RESPONSE_TIMEOUT
    )
    flat_api = bridge.get_flat_api()

    prog = flat_api.getCurrentProgram()

    # Return list of addresses of function that do not return
    def _remote_get_non_returning_functions(prog):
        # type:(Any) -> list[int]
        non_ret_funcs = []
        function_manager = prog.getFunctionManager()
        # Iterate over all functions in the SUT (that Ghidra found).
        for function in function_manager.getFunctions(True):
            if function.hasNoReturn():
                # Function does not return.
                entrypoint = int(str(function.getEntryPoint()), 16)
                non_ret_funcs.append(entrypoint)
        return non_ret_funcs

    remote_get_non_returning_functions = bridge.remoteify(
        _remote_get_non_returning_functions
    )

    return remote_get_non_returning_functions(prog)


print(get_no_return_functions())
