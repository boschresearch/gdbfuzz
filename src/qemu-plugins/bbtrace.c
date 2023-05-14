// Plugin for QEMU to forward translated basic blocks to honggfuzz.
// libhfuzz.so must be linked for proper function!
// Copyright (c) 2019 Robert Bosch GmbH
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

#include <inttypes.h>
#include <glib.h>

#include <qemu-plugin.h>

#include <stdio.h>
#include <time.h>
#include <unistd.h>

#define COVERAGE_DATA_FILE "/tmp/coverage_data"
#define MAX_LINE_SIZE 1024

FILE *fp;

QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;
static GMutex lock;

time_t start_time;

GHashTable* hit_addresses;

static void vcpu_tb_trans(qemu_plugin_id_t id, struct qemu_plugin_tb *tb)
{
    /**
     * Tracing newly translated blocks is sufficient for bb coverage
     * */
    g_mutex_lock(&lock);

    struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, 0);
    uint64_t vaddr = (uint64_t)qemu_plugin_insn_haddr(insn);


    if(!g_hash_table_contains(hit_addresses, (void*)  vaddr)) {
        g_hash_table_add(hit_addresses, (void*) vaddr);

        fprintf(fp, "%d %lx\n", (int)time(NULL), vaddr);
        fflush(fp);
    }

    g_mutex_unlock(&lock);
}


static void plugin_exit(qemu_plugin_id_t id, void *p)
{
    g_mutex_lock(&lock);

    g_hash_table_destroy(hit_addresses);
    g_mutex_unlock(&lock);

}


QEMU_PLUGIN_EXPORT
int qemu_plugin_install(qemu_plugin_id_t id, const qemu_info_t *info,
                        int argc, char **argv)
{
    g_mutex_init(&lock);
    hit_addresses = g_hash_table_new(g_direct_hash, g_direct_equal);

    fp = fopen(COVERAGE_DATA_FILE, "a+");
    if (fp == NULL) {
        fprintf(stderr, "Failed to open COVERAGE_DATA_FILE\n");
        exit(1);
    }

    //Read in previousy reached addresses
    char line[MAX_LINE_SIZE];
    while (fgets(line, MAX_LINE_SIZE, fp))
    {
        char* timestamp = strtok(line, " ");
        char* addr = strtok(NULL, " ");

        uint64_t vaddr = g_ascii_strtoll(addr, NULL, 16);

        g_hash_table_add(hit_addresses, (void*) vaddr);
    }

    qemu_plugin_register_vcpu_tb_trans_cb(id, vcpu_tb_trans);
    qemu_plugin_register_atexit_cb(id, plugin_exit, NULL);


    return 0;
}
