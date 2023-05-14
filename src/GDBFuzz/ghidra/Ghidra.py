# This class handles the connection and functionality to Ghidra.
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

import atexit
import logging as log
import os
import random
import signal
import string
import subprocess
import time
from functools import lru_cache
from typing import Any
from typing import TYPE_CHECKING

import GDBFuzz.binary_operations.BinaryOperations as BinaryOps
import ghidra_bridge
import networkx as nx
from GDBFuzz.connections.SUTConnection import SUTConnection
from GDBFuzz.gdb.GDB import GDB
from GDBFuzz.ghidra.CFGUpdateCandidate import CFGUpdateCandidate
from GDBFuzz.SUTException import SUTException
from GDBFuzz.util import int_array_to_int

if TYPE_CHECKING:
    import _bridged_ghidra.program.database.ProgramDB as ghidra_ProgramDB
    import jfx_bridge.bridge._bridged_ghidra.program.model \
                     .address.GenericAddress as ghidra_GenericAddress

GHIDRA_BRIDGE_RESPONSE_TIMEOUT = 60 * 30  # 30 minutes timeout


class Ghidra:
    def __init__(
        self,
        binary_file: str,
        start_ghidra: bool,
        entrypoint: int,
        ignore_functions: list[str],
        path_to_ghidra: str,
        output_directory: str,
        ghidra_port: int
    ) -> None:
        self.entrypoint = entrypoint
        path_to_ghidra = os.path.expanduser(path_to_ghidra)
        self.output_directory = output_directory
        self.start_ghidra = start_ghidra
        
        if not ghidra_port:
            ghidra_port = ghidra_bridge.ghidra_bridge.DEFAULT_SERVER_PORT
        if start_ghidra:
            self.start_ghidra_instance(binary_file, path_to_ghidra, output_directory, ghidra_port)

        self.cfg: nx.DiGraph | None = None
        self.reverse_cfg: nx.DiGraph | None = None
        self.exit_points: set[int] | None = None

        self.ignore_addresses: set[int] = set()
        if BinaryOps.file_is_elf(binary_file):
            self.ignore_addresses = BinaryOps.get_function_addresses(
                binary_file,
                ignore_functions
            )

        self.bridge = ghidra_bridge.GhidraBridge(
            response_timeout=GHIDRA_BRIDGE_RESPONSE_TIMEOUT,
            interactive_mode=True,
            connect_to_port=ghidra_port,
            loglevel=log.INFO
        )
        
        if not self.start_ghidra:
            self.bridge.get_flat_api().start()
            self.bridge.remote_exec(
                "getState().getTool()"\
                ".getService(ghidra.app.plugin.core.colorizer.ColorizingService)"\
                ".clearAllBackgroundColors()")
            self.bridge.get_flat_api().end(True)

        RemoteGhidraClass = self.bridge.remoteify(RemoteGhidra)
        self.remote_ghidra = RemoteGhidraClass()

        # List of addresses of branch instructions for which Ghidra has not
        # found any destination.
        self.unknown_edges = self.remote_ghidra.unknown_edge_destinations()

        self.cfg_update_candidates: list[CFGUpdateCandidate] = []

        # This is set to true if the Ghidra analysis took to long last time.
        # In this case, we continue with the previous/old CFG.
        # By default the Ghidra timeout (GHIDRA_BRIDGE_RESPONSE_TIMEOUT) is
        # 10 minutes.
        self.ghidra_analysis_fails = 0

    # Start a ghidra process, create a ghidra project for 'binary_file', and
    # start ghidra_bridge
    def start_ghidra_instance(self, binary_file: str, path_to_ghidra: str, output_directory: str, ghidra_port: int) -> None:
        ghidra_cli_script = os.path.join(
            path_to_ghidra,
            'support/analyzeHeadless'
        )
        if not os.path.isfile(ghidra_cli_script):
            raise Exception(f'No such file {ghidra_cli_script=}')

        # Read in the config file
        with open(ghidra_cli_script) as file:
            ghidra_config_data = file.read()

        # Replace the target string -> Seems not to be required
        #ghidra_config_data = ghidra_config_data \
        #    .replace('MAXMEM=2G', 'MAXMEM=10G')

        # Write the config file out again
        with open(ghidra_cli_script, 'w') as file:
            file.write(ghidra_config_data)

        server_scripts_dir = os.path.expanduser('~/ghidra_scripts')

        ghidra_bridge_script = os.path.join(
            server_scripts_dir,
            'ghidra_bridge_server.py'
        )
        if not os.path.isfile(ghidra_bridge_script):
            raise Exception(f'No such file {ghidra_bridge_script=}')
        
        with open(os.path.join(
            server_scripts_dir,
            'ghidra_bridge_port.py'), "w") as port_config:
            port_config.write(f'DEFAULT_SERVER_PORT = {ghidra_port}')

        ghidra_projects_dir = os.path.join(
            output_directory,
            'ghidra_projects'
        )
        if not os.path.isdir(ghidra_projects_dir):
            os.mkdir(ghidra_projects_dir)

        project_name = os.path.basename(binary_file)

        run_command = [
            ghidra_cli_script, ghidra_projects_dir, project_name,
            '-import', binary_file,
            '-scriptPath', server_scripts_dir,
            '-postscript', 'ghidra_bridge_server.py'
        ]

        process = subprocess.Popen(
            run_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        self.ghidra_process = process
        atexit.register(self.kill_ghidra_process)

        # Wait until the ghidra bridge/server is running
        ghidra_bridge_running = False
        while not ghidra_bridge_running:
            exit_code = process.poll()
            if exit_code is not None:
                stdout, _ = process.communicate(timeout=1)
                raise Exception(f'Ghidra process has unexpectedly '
                                f'terminated with {exit_code=} {stdout=}')
            if process.stdout:
                for line in process.stdout:
                    log.info('Ghidra process output:' + str(line))
                    if b'INFO:jfx_bridge.bridge:serving!' in line:
                        ghidra_bridge_running = True
                        log.info('Ghidra bridge connected')
                        return
            log.info('Ghidra process bridge server has not started yet.'
                     ' Trying again in 3 seconds.')
            time.sleep(3)



    def kill_ghidra_process(self) -> None:
        if (
                self.ghidra_process is not None and
                self.ghidra_process.poll() is None
        ):
            os.killpg(os.getpgid(self.ghidra_process.pid), signal.SIGTERM)

    def prog(self, bridge: Any) -> ghidra_ProgramDB:
        return bridge.get_flat_api().getCurrentProgram()

    def _to_address(self, address: int, bridge: Any) -> ghidra_GenericAddress:
        prog = bridge.get_flat_api().getCurrentProgram()
        addr_space = prog.getAddressFactory().getDefaultAddressSpace()
        return addr_space.getAddress(address)

    def CFG(self) -> nx.DiGraph:
        if self.cfg is None:
            self.infer_CFG_and_reverse_CFG()
        return self.cfg

    def reverse_CFG(self) -> nx.DiGraph:
        if self.reverse_cfg is None:
            self.infer_CFG_and_reverse_CFG()
        return self.reverse_cfg

    def exit_Points(self) -> set[int]:
        if self.exit_points is None:
            self.infer_CFG_and_reverse_CFG()
        return self.exit_points

    def infer_CFG_and_reverse_CFG(self) -> None:

        cfg_path = os.path.abspath(os.path.join(self.output_directory, 'cfg'))
        reverse_cfg_path = os.path.abspath(
            os.path.join(self.output_directory, 'reverse_cfg'))

        try:
            log.info('Generating CFG of SUT. (This might take a while...)')
            self.remote_ghidra.CFG(
                self.entrypoint,
                self.ignore_addresses,
                cfg_path
            )
            self.cfg = nx.read_adjlist(
                cfg_path, nodetype=hex_int, create_using=nx.DiGraph)

            log.info('Generating reverse CFG of SUT. (This might take a while...)')
            self.exit_points = self.remote_ghidra.reverse_CFG(
                self.entrypoint,
                self.ignore_addresses,
                reverse_cfg_path
            )
            self.reverse_cfg = nx.read_adjlist(
                reverse_cfg_path, nodetype=hex_int, create_using=nx.DiGraph)

        except Exception as e:
            log.info(
                'Ghidra Analysis Exception, continue with previous CFG.',
                f'Exception: {e}'
            )
            self.ghidra_analysis_fails += 1
            return

        log.info(f'CFG: ({self.cfg.number_of_nodes()}, {self.cfg.number_of_edges()}), reverse CFG ({self.reverse_cfg.number_of_nodes()}, {self.reverse_cfg.number_of_edges()}), exit_points: ({self.exit_points})')

    def add_reference(self, source_addr: int, destination_addr: int) -> None:

        source = self._to_address(source_addr, self.bridge)
        destination = self._to_address(destination_addr, self.bridge)

        ghidra = self.bridge.get_ghidra_api()
        flat_api = self.bridge.get_flat_api()
        bb_model = ghidra.program.model.block.SimpleBlockModel(
            flat_api.getCurrentProgram()
        )
        task_monitor = ghidra.util.task.ConsoleTaskMonitor()
        block = bb_model.getFirstCodeBlockContaining(source, task_monitor)
        flowtype = block.getFlowType()

        # ghidra transaction required
        flat_api.start()
        flat_api.addInstructionXref(source, destination, 0, flowtype)
        flat_api.end(True)

    def report_address_reached(
        self,
        current_input: bytes,
        address: int
    ) -> None:
        
        if not self.start_ghidra:
            flat_api = self.bridge.get_flat_api()
            flat_api.start()
            self.remote_ghidra.mark_block(address)
            flat_api.end(True)
        if address not in self.unknown_edges:
            return

        # Note that report_coverage is always called with unique 'address'
        # parameter values, so we do not append multiple candidates for
        # the same address/edge.
        self.cfg_update_candidates.append(
            CFGUpdateCandidate(current_input, self.unknown_edges[address])
        )

    def cfg_changed(self) -> None:

        try:

            flat_api = self.bridge.get_flat_api()
            flat_api.analyzeChanges(flat_api.getCurrentProgram())

            flat_api.saveProgram(flat_api.getCurrentProgram())

            self.unknown_edges = self.remote_ghidra.unknown_edge_destinations()
            log.info(f"Looking for {len(self.unknown_edges)} unknown edges")
        except Exception as e:
            log.info(
                'Ghidra Analysis timeout, continue with previous CFG.',
                f'Exception: {e}'
            )
            self.ghidra_analysis_fails += 1
            return
        self.infer_CFG_and_reverse_CFG()
        self.cfg_update_candidates = []

    def update_cfg(
        self,
            gdb: GDB,
            SUT_connection: SUTConnection,
            candidate: CFGUpdateCandidate
    ) -> None:
        """Obtain the address of the instruction that is executed after
        the unknown_edg address.
        """

        # Halt at unknown edge.
        bp_id = gdb.set_breakpoint(candidate.unknown_edge_address)

        gdb.continue_execution()
        stop_reason, stop_info = gdb.wait_for_stop(timeout=30)

        if stop_reason == 'input request':
            
            # candidate.SUT_input previously covered the unknown edge.
            # Send this input.
            SUT_connection.send_input(candidate.SUT_input)

            stop_reason, stop_info = gdb.wait_for_stop(timeout=30)

        else:
            log.warn(
                f'cfg_update for edge at {candidate.unknown_edge_address} '
                f'unexpected {stop_reason=} {stop_info=}.'
                f'Expected stop_reason="input request".'
            )


        if stop_reason not in {'breakpoint hit', 'interrupt'}:
            log.warn(
                f'cfg_update for edge at {candidate.unknown_edge_address} '
                f'unexpected {stop_reason=} {stop_info=}.'
                f'Expected stop_reason="breakpoint hit".'
            )
            return

        if stop_info != bp_id:
            return

        # We hit the breakpoint that was set at the start of this function,
        # i.e. the breakpoint at the unknown edge.
        gdb.step_instruction()
        # Now the target system's program counter is at one of the possible
        # destiantions of this unknown edge.
        stop_reason, stop_info = gdb.wait_for_stop(timeout=30)
        if stop_reason != 'step instruction done':
            raise SUTException(
                'Expected stop reason step instruction done, '
                f' got {stop_reason=} {stop_info=}'
            )
        # Read target system's program counter. This information is included
        # in the stop_info from the single step.
        current_pc = int(stop_info['frame']['addr'], 16)
        log.info(
            f'Found edge {candidate.unknown_edge_address} -> {current_pc}'
        )

        # Notify Ghidra about the edge.
        self.add_reference(candidate.unknown_edge_address, current_pc)

    @lru_cache(maxsize=None)
    def basic_block_at_address(self, address: int) -> int:
        """Return the address of the basic block of which the instruction
        at 'address' is part of.
        """

        ghidra = self.bridge.get_ghidra_api()
        flat_api = self.bridge.get_flat_api()
        bb_model = ghidra.program.model.block.SimpleBlockModel(
            flat_api.getCurrentProgram()
        )
        task_monitor = ghidra.util.task.ConsoleTaskMonitor()
        bbs = bb_model.getCodeBlocksContaining(
            self._to_address(address, self.bridge),
            task_monitor
        )
        if len(bbs) != 1:
            raise Exception(
                f'Failed to get basic block at {address=} {bbs=}'
            )
        bb_start_address = bbs[0].getFirstStartAddress()
        return int(str(bb_start_address), 16)


class RemoteGhidra:

    def mark_block(self, address):

        
        simple_block_model = ghidra.program.model.block.SimpleBlockModel(
            currentProgram
        )
        bbs = simple_block_model.getFirstCodeBlockContaining(
            self._to_address(address),
            monitor
        )
        if bbs:
            service = getState().getTool().getService(ghidra.app.plugin.core.colorizer.ColorizingService)
            service.setBackgroundColor(bbs, java.awt.Color.GREEN)
            
    def _to_address(self, address):
        # currentProgam is defined in ghidra environment
        addr_space = currentProgram.getAddressFactory().getDefaultAddressSpace()
        return addr_space.getAddress(address)

    def _to_int(self, address):
        return int(str(address), 16)

    def _write_to_file(self, graph, file_path):

        # write adjacency list in decimal for easier parsing
        with open(file_path, 'w') as out:
            out.write('#Adjacency list in hexadecimal')
            if self.function_names:
                for func in self.function_names:
                    out.write(func + " ")
            out.write('\n')
            for node in graph.keys():
                out.write(hex(node))
                out.write(' ')
                for dest in graph[node]:
                    out.write(hex(dest))
                    out.write(' ')
                out.write('\n')

    def CFG(self, entrypoint, ignore_addresses, file_path):
        # type:(int, set[int], str) -> None
        # dict keys are addresses.
        # dict values are list of edge destination addresses
        # currentProgram and monitor are present variables

        self.EXTERNAL_CALL_SITE_DUMMY = -1
        self.EXTERNAL_RETURN_BLOCK_DUMMY = -2

        # currentProgram and monitor are present variables
        flat_api = ghidra.program.flatapi.FlatProgramAPI(
            currentProgram,
            monitor
        )

        functions_worklist = set()

        # Global variables
        self.functions_done = set()
        self.returns = {}
        self.cfg = {}
        self.function_names = []

        simple_block_model = ghidra.program.model.block.SimpleBlockModel(
            currentProgram
        )

        # entrypoint must not be at the entry point of a function
        # Therefore get entry function
        entry_function = flat_api.getFunctionContaining(
            self._to_address(entrypoint)
        )
        # Add entry function's entry point to worklist
        # Address object is not hashable, so we translate it to an int
        entry_function_address = self._to_int(entry_function.getEntryPoint())
        functions_worklist.add(entry_function_address)

        # Go through functions in a BFS style
        while functions_worklist:
            # Get next untraversed function
            current_function_address = functions_worklist.pop()
            # Add to done functions to prevent recursions
            self.functions_done.add(current_function_address)

            self.returns[current_function_address] = set()

            # Translate address to ghidra address object
            current_function = flat_api.getFunctionAt(
                self._to_address(current_function_address)
            )

            if current_function is None:
                # Ghidra did not find function at current_function_address
                continue

            self.function_names.append(current_function.getName())
            # Get all BB's of the function
            code_block_iterator = simple_block_model.getCodeBlocksContaining(
                current_function.getBody(),
                monitor
            )

            # Go through all BB's of the function
            while code_block_iterator.hasNext():
                code_block = code_block_iterator.next()
                code_block_address = self._to_int(
                    code_block.getFirstStartAddress()
                )
                self.cfg[code_block_address] = set()

                # Get Destinations of current BB
                edges_iterator = code_block.getDestinations(monitor)

                # Check if current block is a returning block.
                # That is the case, when ghidra marks it as terminal
                # and not a call, or if block has no outgoing edges.
                # The no outgoing edges heuristic is a bit scetchy,
                # since it can result from unrecognized control flow as well.
                # But like this we are on the safe side.
                if (
                        code_block.getFlowType().isTerminal() and
                        not code_block.getFlowType().isCall() or
                        not edges_iterator.hasNext()
                ):
                    self.returns[current_function_address].add(
                        code_block_address
                    )

                # Go through all destinations
                while edges_iterator.hasNext():
                    edge = edges_iterator.next()

                    # Insert destination as edge
                    destination_address = self._to_int(
                        edge.getDestinationAddress()
                    )
                    if (
                            destination_address not in ignore_addresses and
                            not code_block.getFlowType().isTerminal()
                    ):
                        # destination_addresses.append(destination_address)
                        self.cfg[code_block_address].add(
                            destination_address)

                    # If destination is a call, add function to worklist
                        if edge.getFlowType().isCall():
                            if destination_address not in self.functions_done:
                                # set does take care of duplicates here
                                functions_worklist.add(destination_address)

        # Add edge from entrypoint to external call site dummy
        self.cfg[entrypoint].add(self.EXTERNAL_CALL_SITE_DUMMY)
        self.cfg[self.EXTERNAL_CALL_SITE_DUMMY] = set()

        for current_function in self.functions_done:
            # Add eventual call sites outside of our scope
            function_entry_block = simple_block_model.getCodeBlockAt(
                self._to_address(current_function),
                monitor
            )

            # Get Source of function's entry block
            codeBlockReferenceSourceIterator = function_entry_block\
                .getSources(monitor)

            # Go through all sources
            while codeBlockReferenceSourceIterator.hasNext():
                codeBlockReference = codeBlockReferenceSourceIterator\
                    .next()
                sourceAddress = int(str(
                    codeBlockReference.getSourceAddress()
                ), 16)
                # If function is also called from external locations
                if codeBlockReference.getFlowType().isCall() \
                        and sourceAddress not in self.cfg:
                    # Insert an edge from dummy call site to function
                    self.cfg[self.EXTERNAL_CALL_SITE_DUMMY].add(
                        current_function)

        self._write_to_file(self.cfg, file_path)

    def reverse_CFG(self, entrypoint, ignore_addresses, file_path):
        # type:(int, set[int], str) -> set[int]

        # currentProgram and monitor are present variables
        flat_api = ghidra.program.flatapi.FlatProgramAPI(
            currentProgram,
            monitor
        )

        simple_block_model = ghidra.program.model.block.SimpleBlockModel(
            currentProgram
        )

        reverse_cfg = {}

        while self.functions_done:
            current_function_address = self.functions_done.pop()

            # Translate address to ghidra address object
            current_function_address_object = self._to_address(
                current_function_address)
            current_function = flat_api.getFunctionAt(
                current_function_address_object
            )

            if current_function is None:
                # Ghidra did not find function at current_function_address
                continue

            # Get all BB's of the function
            codeBlockIterator = simple_block_model.getCodeBlocksContaining(
                current_function.getBody(),
                monitor
            )

            # Go through all BB's of the function
            while codeBlockIterator.hasNext():
                codeBlock = codeBlockIterator.next()
                codeBlock_address = self._to_int(
                    codeBlock.getFirstStartAddress())

                # Init source list
                reverse_cfg[codeBlock_address] = set()

                # Get Source of current BB
                codeBlockReferenceSourceIterator = codeBlock\
                    .getSources(monitor)

                # Go through all sources
                while codeBlockReferenceSourceIterator.hasNext():
                    codeBlockReference = codeBlockReferenceSourceIterator\
                        .next()

                    # Insert destination as edge
                    sourceAddress = self._to_int(
                        codeBlockReference.getSourceAddress())

                    # Skip nodes that are not reachable from the entry point
                    if sourceAddress not in self.cfg:
                        continue

                    # Skip call edges in reversed cfg
                    if not codeBlockReference.getFlowType().isCall():
                        # Add reversed edge
                        reverse_cfg[codeBlock_address].add(sourceAddress)

                        # If source block is a call, we need all returning edges to the current block
                        if codeBlockReference.getSourceBlock().getFlowType().isCall() and \
                                not codeBlockReference.getSourceBlock().getFlowType().isTerminal():
                            # First, Get address of called function
                            called_function_address = 0
                            destination_iterator = codeBlockReference.getSourceBlock().getDestinations(monitor)
                            while destination_iterator.hasNext():  # Go through all destinations
                                dest_reference = destination_iterator.next()
                                if dest_reference.getFlowType().isCall():  # Take first call reference
                                    called_function_address = self._to_int(
                                        dest_reference.getDestinationAddress())
                                    break

                            if called_function_address in ignore_addresses \
                                    or called_function_address == 0:
                                continue

                            # Next, go thorugh all returning blocks
                            if called_function_address not in self.returns:
                                print('No returning blocks for function at',
                                      hex(called_function_address), ' called from ', hex(sourceAddress))
                                continue

                            # Add edges to each returning block
                            for ret_block_address in self.returns[called_function_address]:
                                reverse_cfg[codeBlock_address].add(
                                    ret_block_address)

        # Add return edges to exteral call sites
        reverse_cfg[self.EXTERNAL_RETURN_BLOCK_DUMMY] = set()

        # all external called called functions
        for external_called_function in self.cfg[self.EXTERNAL_CALL_SITE_DUMMY]:

            # For all returning blocks of external called function
            for external_return in self.returns[external_called_function]:
                reverse_cfg[self.EXTERNAL_RETURN_BLOCK_DUMMY].add(
                    external_return)

        # Add external return dummy block to exit points
        self.returns[entrypoint].add(self.EXTERNAL_RETURN_BLOCK_DUMMY)

        # Write graph to file
        self._write_to_file(reverse_cfg, file_path)

        return self.returns[entrypoint]

    # Returned keys are basic block addresses, values are jump or call
    # instruction addresses who's jump or call destination is not known.
    def unknown_edge_destinations(self):

        # currentProgram and monitor are present variables
        flat_api = ghidra.program.flatapi.FlatProgramAPI(
            currentProgram,
            monitor
        )
        simple_block_model = ghidra.program.model.block.SimpleBlockModel(
            currentProgram
        )

        unknown_edges = {}
        code_block_iter = simple_block_model.getCodeBlocks(monitor)
        while code_block_iter.hasNext():
            code_block = code_block_iter.next()
            num_edges = code_block.getNumDestinations(monitor)
            

            if (
                    code_block.getFlowType().isCall() and
                    code_block.getFlowType().hasFallthrough()
            ):
                num_edges -= 1

            if (
                    (
                        code_block.getFlowType().isCall() or
                        code_block.getFlowType().isJump()
                    ) and
                    num_edges == 0
            ):
                code_block_address = self._to_int(
                    code_block.getFirstStartAddress()
                )
                branch_instr = flat_api.getInstructionContaining(
                    code_block.getMaxAddress()
                )
                branch_address = self._to_int(branch_instr.getMinAddress())

                unknown_edges[code_block_address] = branch_address
        return unknown_edges


class hex_int(int):
    # Trick, to let networkx parse hexadecimal adjacency lists
    def __new__(cls, value, *args, **kwargs):
        if value[-1] == 'L':
            value = value[0:-1]
        return super(cls, cls).__new__(cls, value, base=16)
