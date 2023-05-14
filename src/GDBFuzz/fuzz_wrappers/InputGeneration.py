# This class manages the input generation.
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
from dataclasses import dataclass

import logging as log
import math
import os
import random

import _pylibfuzzer

@dataclass
class CorpusEntry:
    content: bytes
    fname: str
    origin: int
    depth: int
    hit_blocks: int = 0
    num_fuzzed: int = 0
    num_childs: int = 0
    weight: float = 1
    burn_in: int = 5
    
    def compute_weight(self, total_hit_blocks: int, total_corpus_entries: int):
        self.weight = 1.0
        
        # Adapted from AFL
        #if self.num_fuzzed:
        #    self.weight *= math.log10(self.num_fuzzed) + 1
        
        # More childs indicate a good seed
        #if self.num_childs:
        #    self.weight *= self.num_childs / float(total_corpus_entries) + 1
        
        # More hit blocks indicate a good seed
        #if self.hit_blocks:
        #    self.weight *= self.hit_blocks / float(total_hit_blocks) + 1
            
        # The deeper, the better
        #if self.depth:
        #    self.weight *= math.log(self.depth) + 1
                
        if self.burn_in:
            self.weight *= self.burn_in
            
                
    def __str__(self) -> str:
        return f'{self.fname}, depth={self.depth}, hit_blocks={self.hit_blocks}, num_fuzzed={self.num_fuzzed}, childs={self.num_childs}, weight={self.weight}, burn_in={self.burn_in}'
    
class InputGeneration:
    
 
        
    def __init__(
            self,
            output_directory: str,
            seeds_directory: str | None = None,
            max_input_length: int = 1024,
            libfuzzer_so_path: str | None = None
    ):
        if libfuzzer_so_path is None:
            libfuzzer_so_path = os.path.join(
                os.path.dirname(__file__),
                '../../../dependencies/libFuzzerSrc/libfuzzer-mutator.so'
            )
            # _pylibfuzzer reads this env var to know where
            # libfuzzer-mutate.so is located.
            os.environ['libfuzzer_mutator_so_path'] = libfuzzer_so_path

        # maximum length of generated inputs in bytes.
        self.max_input_length = max_input_length

        # Corpus entries are stored on disk in this directory.
        self.corpus_directory = os.path.join(output_directory, 'corpus')
        os.mkdir(self.corpus_directory)

        if not os.path.exists(libfuzzer_so_path):
            raise Exception(f'{libfuzzer_so_path=} does not exist.')

        if seeds_directory is not None:
            if not os.path.exists(seeds_directory):
                raise Exception(f'{seeds_directory=} does not exist.')

        # set is for fast contains checks, list is for fast 'random.choice',
        # i.e. selecting random element.
        self.corpus: list[CorpusEntry] = []
        
        # For the initialization phase, we keep these values to -1
        # The currently selected base input
        self.current_base_input_index: int = -1
        
        # Index of corpus entry we need to retry (because we target new addresses)
        self.retry_corpus_input_index: int = -1
        
        # For statistic purposes
        self.total_hit_blocks = 0
        
        
        if seeds_directory:
            self.add_seeds(seeds_directory)

        if len(self.corpus) == 0:
            # No seeds were specified or all seeds in seeds_directory are too
            # large
            self.add_corpus_entry(b"hi", 0, 0) # Default from fuzzbench :)

        # Setup stared libfuzzer object.
        _pylibfuzzer.initialize(max_input_length)

    def add_seeds(self, seeds_directory: str) -> None:
        """Add each seed in seeds_directory to the corpus.

        Inputs larger than self.max_input_length are not added.
        """
        for filename in sorted(os.listdir(seeds_directory)):
            filepath = os.path.join(seeds_directory, filename)
            if not os.path.isfile(os.path.join(filepath)):
                continue
            with open(filepath, 'rb') as f:
                seed = f.read()
                if len(seed) > self.max_input_length:
                    log.warning(
                        f'Seed {filepath=} was not added to the corpus '
                        f'because the seed length ({len(seed)}) was too large'
                        f' {self.max_input_length=}.'
                    )
                    continue
                log.debug(f'Seed {filepath=} added.')
                if seed not in self.corpus:
                    self.add_corpus_entry(seed, 0, 0)

    def add_corpus_entry(self, input: bytes, address: int, timestamp:int) -> CorpusEntry:
        

        filepath = os.path.join(
            self.corpus_directory,
            f'id:{str(len(self.corpus))},orig:{self.current_base_input_index},addr:{hex(address)},time:{timestamp}'
        )
        with open(filepath, 'wb') as f:
            f.write(input)
            
            
        depth = 0
        if self.current_base_input_index >= 0: 
            depth = self.corpus[self.current_base_input_index].depth + 1
            self.corpus[self.current_base_input_index].num_childs +=1
            
        entry = CorpusEntry(input, filepath, self.current_base_input_index, depth)
        self.corpus.append(entry)
        
        return entry

    def choose_new_baseline_input(self):
        
        # Breakpoints have been reset, so lets try corpus files again
        if self.retry_corpus_input_index > 0:
            self.retry_corpus_input_index = 0
        #self.current_base_input_index = random.randint(0, len(self.corpus) -1)
        
        energy_sum = 0
        cum_energy = []
        for i in self.corpus:
            i.compute_weight(self.total_hit_blocks, len(self.corpus))
            energy_sum += i.weight
            cum_energy.append(energy_sum)
        
        # Draw new corpus entry according to energy
        self.current_base_input_index =  random.choices(range(len(cum_energy)), cum_weights=cum_energy).pop()
        
        chosen_entry = self.corpus[self.current_base_input_index]
        chosen_entry.num_fuzzed += 1
        if chosen_entry.burn_in:
            chosen_entry.burn_in -= 1
        
    def get_baseline_input(self) -> bytes: 
        return self.corpus[self.current_base_input_index].content

    def generate_input(self) -> bytes:
        
        # After a reset, we first try all corpus files again
        if self.retry_corpus_input_index < len(self.corpus):
            input = self.corpus[self.retry_corpus_input_index].content
            self.retry_corpus_input_index += 1
            return input
        
        generated_inp = _pylibfuzzer.mutate(self.corpus[self.current_base_input_index].content)
        return generated_inp

    def report_address_reached(self, current_input: bytes, address: int, timestamp:int) -> None:
        
        self.total_hit_blocks +=1 
        # If we have 
        for i in self.corpus:
            if i.content == current_input:
                i.hit_blocks +=1
                return

        #A breakpoint was hit, so try all corpus files again
        self.retry_corpus_input_index = 0
        entry = self.add_corpus_entry(current_input, address, timestamp)
        entry.hit_blocks +=1
        log.debug(f'New Corpus entry {current_input!r}')
