# This class manages visualizations of the fuzzing process.
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

import json
import logging
import os
import queue
import subprocess
import threading
import time
from datetime import datetime
from typing import Final

import attr
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import seaborn as sns
from GDBFuzz import graph
from GDBFuzz.FuzzerStats import FuzzerStats
from GDBFuzz.visualization.MQTTClient import MQTTClient

broker_hostname: Final = 'localhost'
broker_port: Final = 9001


class Visualizations(threading.Thread):
    """If the visualizations are enabled in the user configuration (enable_UI
    set to True), GDBFuzz sends fuzzer stats and the plotted CFG to a
    javascript web app via MQTT. This file implements plotting this CFG,
    and sending the fuzzer stats to this web app.
    """

    def __init__(
            self,
            fuzzer_stats: FuzzerStats,
            output_directory: str,
            cfg: nx.DiGraph,
            sleep_time: int = 5
    ) -> None:
        threading.Thread.__init__(self)
        self.name = 'Visualizations_thread'

        self.fuzzer_stats = fuzzer_stats
        self.output_directory = output_directory
        self.cfg = cfg

        self.mqtt_client = MQTTClient(broker_hostname, broker_port)

        self.sleep_time = sleep_time
        self.start_time = time.time()
        self.last_update_time = self.start_time

        # True if coverage has changed since the UI was last updated
        self.coverage_changed = False

        # List of (timestamp, coverage) tuples, where coverage specifies the
        # number of basic blocks covered.
        self.coverage_plot_data: list[tuple[float, int]] = []

        # In the CFG plot, the size of nodes depends on this nodes reachable
        # number.
        self.nodes_reachable = graph.NodesReachableCache(
            self.cfg
        )

    def run(self) -> None:
        while True:
            # every self.sleep_time seconds, send the current
            # fuzzer stats to the web app where they are displayed.
            self.send_fuzzer_stats()
            if (
                    self.coverage_changed or
                    self.last_update_time + 60 > time.time()
            ):
                # GDBFuzz has increased known code coverage, plot new
                # coverage over time plot. Store this plot in the output
                # directory.
                self.last_update_time = time.time()
                self.coverage_changed = False
                self.plot_coverage()
            time.sleep(self.sleep_time)

    def send_fuzzer_stats(self) -> None:
        self.mqtt_client.publish(
            'fuzzer_stats',
            json.dumps(attr.asdict(self.fuzzer_stats))
        )

    def plot_coverage(self) -> None:
        """Plot Coverage over time graph."""
        if not self.coverage_plot_data:
            return
        data = self.coverage_plot_data + \
            [(time.time() - self.start_time, len(self.coverage_plot_data))]
        frame = pd.DataFrame(
            data, columns=['Time (seconds)', 'Basic Blocks covered'])
        plot = sns.lineplot(
            data=frame, x='Time (seconds)', y='Basic Blocks covered')
        plot.set(xlim=(1, None))
        plot.set_title(f'Timestamp of last update: {str(datetime.now())}')

        path = os.path.join(
            self.output_directory,
            'coverage_over_time_plot.svg'
        )
        plot.figure.savefig(path)
        plt.clf()
        with open(path) as f:
            svg = f.read()
        self.mqtt_client.publish('coverage_over_time', svg)

    def new_coverage(self) -> None:
        """Write known code coverage to a json file in the output directory."""
        self.coverage_plot_data.append(
            (time.time() - self.start_time, len(self.coverage_plot_data) + 1)
        )
        self.coverage_changed = True

        cov_file = os.path.join(self.output_directory, 'coverage_data.json')
        with open(cov_file, 'w') as f:
            f.write(json.dumps(self.coverage_plot_data))

    def breakpoints_changed(self, breakpoints: set[int]) -> None:
        """Send 'breakpoints' to the MQTT broker with topic
        'coverage_over_time'. 'breakpoints' is a list of dictionaries with
        two keys: gdb_number and address
        """
        breakpoints_json = json.dumps(list(breakpoints))
        self.mqtt_client.publish('breakpoints', breakpoints_json)

    def draw_CFG(
            self,
            entrypoint: int,
            cfg: nx.DiGraph,
            coverage_map: set[int],
            output_filename: str = 'cfg_visualization'
    ) -> None:
        """Plot CFG, send it to the web UI via MQTT.
        This plot is in the DOT Language from Graphviz.
        """
        assert entrypoint in cfg
        dotfile_nodes: list[str] = []
        dotfile_edges: list[str] = []

        # Entrypoint is root node in cfg
        dotfile_nodes.append(
            f'{entrypoint} [label="{hex(entrypoint)}\nEntrypoint";'
            f' style=filled; fillcolor="#99ccff"]'
        )

        for node in coverage_map:
            dotfile_nodes.append(
                f'{node} [label="{hex(node)}";'
                f' style=filled; fillcolor="#99ccff"]'
            )

        # Only plot covered nodes and uncovered neighbours, i.e. parent node
        # must be covered to be included.
        uncovered_nodes = graph.uncovered_neighbours(self.cfg, coverage_map)
        # The size of a node in the plot depends on how many nodes are
        # reachable from a node.
        reachable_counts: dict[int, int] = dict()
        max_reachable = 1
        for node in uncovered_nodes:
            reachable_count = self.nodes_reachable.get(node)
            reachable_counts[node] = reachable_count
            max_reachable = max(max_reachable, reachable_count)

        for node in uncovered_nodes:
            margin = reachable_counts[node] / max_reachable
            dotfile_nodes.append(
                f'{node} [label="{hex(node)}";'
                f' margin="{margin},{margin}"; shape=invtriangle]'
            )

        for node in coverage_map:
            if node in cfg\
                    and node >= 0:
                for destination in cfg.successors(node):
                    dotfile_edges.append(
                        f'{node} -> {destination}'
                    )

        dotfile = "digraph {" + '\n'.join(list(dotfile_nodes)) + '\n' + \
                  '\n'.join(dotfile_edges) + '}'

        dotfile_path = os.path.join(self.output_directory, output_filename)
        with open(dotfile_path, 'w') as f:
            f.write(dotfile)

        svg_path = dotfile_path + '.svg'

        subprocess.check_output(
            ['dot', '-Tsvg', '-o', svg_path, dotfile_path]
        )

        with open(svg_path) as f:
            svg = f.read()
        self.mqtt_client.publish('cfg', svg)

    # Returns a dotfile as a string that displays the whole CFG, including all
    # covered and uncovered nodes.
    # 'cfg' argument can, for example, be returned from ghidra's CFG().
    # 'entrypoint' is the address of basic block that is the root node for the
    # CFG.
    def draw_complete_CFG(
            self,
            entrypoint: int,
            cfg: nx.DiGraph,
            output_filename: str = 'cfg_visualization',
    ) -> str:
        assert entrypoint in cfg
        todo: queue.Queue[int] = queue.Queue()
        todo.put(entrypoint)
        done = set()
        dotfile_nodes = set()
        dotfile_edges: list[str] = []

        while todo.qsize() > 0:
            cur_node = todo.get(block=False)

            if cur_node in done:
                continue
            done.add(cur_node)

            dotfile_nodes.add(
                f'{cur_node} [label="{hex(cur_node)}";'
                f' style=filled; fillcolor="#99ccff"]'
            )

            if cur_node not in cfg:
                logging.warning(f'{hex(cur_node)} not found in cfg')
                continue

            for i, destination in enumerate(cfg.successors(cur_node), start=1):
                todo.put(destination)
                dotfile_nodes.add(
                    f'{destination} [label="{hex(destination)}";'
                    f' style=filled; fillcolor="#99ccff"]'
                )
                dotfile_edges.append(
                    f'{cur_node} -> {destination} '
                    f'[label="{i}"]'
                )

        dotfile = "digraph {" + '\n'.join(list(dotfile_nodes)) + '\n' + \
                  '\n'.join(dotfile_edges) + '}'

        with open(output_filename, 'w') as f:
            f.write(dotfile)

        svg_filename = output_filename + '.svg'
        subprocess.check_output(
            ['dot', '-Tsvg', '-o', svg_filename, output_filename]
        )

        with open(svg_filename) as f:
            svg = f.read()
        return svg
