#!/usr/bin/env python3
# This program downloads Google's fuzzbench and pathes the files, such that
# they can be used for benchmarking GDBFuzz
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
import os

# 'static_suts' are statically linked, 'suts' are dynamically linked.
# Not all SUTs allow static linking. Dynamic linking means Ghidra can't
# analyze libraries that are linked at runtime.
# This is sometimes desired, and sometimes not.

suts = [
        'boringssl-2016-02-12', 
#        'c-ares-CVE-2016-5180', 
        'freetype2-2017', 
        'guetzli-2017-3-30', 
        'harfbuzz-1.3.2', 
        'json-2017-02-12',
        'lcms-2017-03-21', 
        'libarchive-2017-01-04',
        'libjpeg-turbo-07-2017', 
        'libpng-1.2.56', 
        'libssh-2017-1272',
        'libxml2-v2.9.2',      
        'sqlite-2016-11-14',
        #'openssl-1.0.1f', (Not executing :( )
        'openssl-1.0.2d', 
        'proj4-2017-08-14', 
        're2-2014-12-09',
        'vorbis-2017-12-11', 
        'woff2-2016-05-06', 
    ]

if os.path.exists('fuzzer-test-suite'):
    i = input('fuzzer-test-suite exists already. '
              'Remove old build files and create new build? [y/n]: ')
    if i != "y":
        print('exiting')
        exit(0)
    os.system('rm -rf ./fuzzer-test-suite')
    os.system('rm -r ./SUT_binaries')


def ex(cmd: str) -> None:
    exitcode = os.system(cmd)
    if exitcode != 0:
        # TODO: later exit?
        breakpoint()


os.mkdir('SUT_binaries')
os.mkdir('SUT_binaries/seeds')

ex('git clone https://github.com/google/fuzzer-test-suite.git')
ex('cd fuzzer-test-suite && '
   'git checkout 6955fc97efedfda7dcc0979658b169d7eeb5ccd6')

ex('patch fuzzer-test-suite/common.sh < GDBFuzz_wrapper/common.sh.patch')

for sut in suts:
    ex(f'cp -r GDBFuzz_wrapper/common/* fuzzer-test-suite/{sut}')

ex('patch fuzzer-test-suite/freetype2-2017/build.sh '
   '< GDBFuzz_wrapper/freetype_build.sh.patch')
ex('patch fuzzer-test-suite/libpng-1.2.56/build.sh '
   '< GDBFuzz_wrapper/libpng_build.sh.patch')
ex('patch fuzzer-test-suite/libssh-2017-1272/build.sh '
   '< GDBFuzz_wrapper/libssh_build.sh.patch')
ex('patch fuzzer-test-suite/sqlite-2016-11-14/seeds/seed '
   '< GDBFuzz_wrapper/sql_seed.patch')

#for sut in static_suts:
#    ex(f'cd fuzzer-test-suite/{sut} && mkdir b && cd b && '
#       'FUZZING_ENGINE=GDBFuzz_static ../build.sh && '
#       f'cp ./main ../../../SUT_binaries/{sut}')


for sut in suts:
    ex(f'cd fuzzer-test-suite/{sut} && mkdir b && cd b && FUZZING_ENGINE=GDBFuzz '
       f'../build.sh && cp ./main ../../../SUT_binaries/{sut}')


for sut in suts:
    seeds_dir = f'fuzzer-test-suite/{sut}/b/seeds/'
    if os.path.isdir(seeds_dir):
        ex(f'cp -r {seeds_dir} SUT_binaries/seeds/{sut}')
        continue

    seeds_dir = f'fuzzer-test-suite/{sut}/seeds/'
    if os.path.isdir(seeds_dir):
        ex(f'cp -r {seeds_dir} SUT_binaries/seeds/{sut}')


