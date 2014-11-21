import os
import time
import unittest

from nose.plugins.attrib import attr

from tests.common import get_check


class VarnishTestCase(unittest.TestCase):
    def setUp(self):
        self.v_dump = """client_conn              42561         1.84 Client connections accepted
client_drop                  0         0.00 Connection dropped, no sess/wrk
client_req             1564940        67.82 Client requests received
cache_hit                52397         2.27 Cache hits
cache_hitpass                0         0.00 Cache hits for pass
cache_miss                5395         0.23 Cache misses
backend_conn             20191         0.88 Backend conn. success
backend_unhealthy            0         0.00 Backend conn. not attempted
backend_busy                 0         0.00 Backend conn. too many
backend_fail              1717         0.07 Backend conn. failures
backend_reuse          1490649        64.60 Backend conn. reuses
backend_toolate            771         0.03 Backend conn. was closed
backend_recycle        1491423        64.64 Backend conn. recycles
backend_retry               13         0.00 Backend conn. retry
fetch_head                   5         0.00 Fetch head
fetch_length           1052795        45.63 Fetch with Length
fetch_chunked           457998        19.85 Fetch chunked
fetch_eof                    0         0.00 Fetch EOF
fetch_bad                    0         0.00 Fetch had bad headers
fetch_close                 13         0.00 Fetch wanted close
fetch_oldhttp                0         0.00 Fetch pre HTTP/1.1 closed
fetch_zero                   0         0.00 Fetch zero len
fetch_failed                 0         0.00 Fetch failed
fetch_1xx                    0         0.00 Fetch no body (1xx)
fetch_204                    0         0.00 Fetch no body (204)
fetch_304                    0         0.00 Fetch no body (304)
n_sess_mem                 547          .   N struct sess_mem
n_sess                      29          .   N struct sess
n_object                   149          .   N struct object
n_vampireobject              0          .   N unresurrected objects
n_objectcore               168          .   N struct objectcore
n_objecthead               211          .   N struct objecthead
n_waitinglist              980          .   N struct waitinglist
n_vbc                        3          .   N struct vbc
n_wrk                       21          .   N worker threads
n_wrk_create              1999         0.09 N worker threads created
n_wrk_failed                 0         0.00 N worker threads not created
n_wrk_max               313745        13.60 N worker threads limited
n_wrk_lqueue                 0         0.00 work request queue length
n_wrk_queued              7125         0.31 N queued work requests
n_wrk_drop                   0         0.00 N dropped work requests
n_backend                    1          .   N backends
n_expired                 5237          .   N expired objects
n_lru_nuked                  0          .   N LRU nuked objects
n_lru_moved              34482          .   N LRU moved objects
losthdr                      0         0.00 HTTP header overflows
n_objsendfile                0         0.00 Objects sent with sendfile
n_objwrite             1611740        69.85 Objects sent with write
n_objoverflow                0         0.00 Objects overflowing workspace
s_sess                   42561         1.84 Total Sessions
s_req                  1564940        67.82 Total Requests
s_pipe                       0         0.00 Total pipe
s_pass                 1507148        65.32 Total pass
s_fetch                1510811        65.48 Total fetch
s_hdrbytes           462276984     20034.54 Total header bytes
s_bodybytes        26560298859   1151092.09 Total body bytes
sess_closed               2198         0.10 Session Closed
sess_pipeline                0         0.00 Session Pipeline
sess_readahead               0         0.00 Session Read Ahead
sess_linger            1563076        67.74 Session Linger
sess_herd              1285271        55.70 Session herd
shm_records          114040454      4942.38 SHM records
shm_writes             6024350       261.09 SHM writes
shm_flushes                  0         0.00 SHM flushes due to overflow
shm_cont                  1353         0.06 SHM MTX contention
shm_cycles                  46         0.00 SHM cycles through buffer
sms_nreq                  1732         0.08 SMS allocator requests
sms_nobj                     0          .   SMS outstanding allocations
sms_nbytes                   0          .   SMS outstanding bytes
sms_balloc              723976          .   SMS bytes allocated
sms_bfree               723976          .   SMS bytes freed
backend_req            1510831        65.48 Backend requests made
n_vcl                        1         0.00 N vcl total
n_vcl_avail                  1         0.00 N vcl available
n_vcl_discard                0         0.00 N vcl discarded
n_ban                        1          .   N total active bans
n_ban_add                    1         0.00 N new bans added
n_ban_retire                 0         0.00 N old bans deleted
n_ban_obj_test               0         0.00 N objects tested
n_ban_re_test                0         0.00 N regexps tested against
n_ban_dups                   0         0.00 N duplicate bans removed
hcb_nolock               57795         2.50 HCB Lookups without lock
hcb_lock                  3909         0.17 HCB Lookups with lock
hcb_insert                3909         0.17 HCB Inserts
esi_errors                   0         0.00 ESI parse errors (unlock)
esi_warnings                 0         0.00 ESI parse warnings (unlock)
accept_fail                  0         0.00 Accept failures
client_drop_late             0         0.00 Connection dropped late
uptime                   23074         1.00 Client uptime
dir_dns_lookups              0         0.00 DNS director lookups
dir_dns_failed               0         0.00 DNS director failed lookups
dir_dns_hit                  0         0.00 DNS director cached lookups hit
dir_dns_cache_full           0         0.00 DNS director full dnscache
vmods                        0          .   Loaded VMODs
n_gzip                       0         0.00 Gzip operations
n_gunzip                     0         0.00 Gunzip operations
LCK.sms.creat                1         0.00 Created locks
LCK.sms.destroy              0         0.00 Destroyed locks
LCK.sms.locks             5196         0.23 Lock Operations
LCK.sms.colls                0         0.00 Collisions
LCK.smp.creat                0         0.00 Created locks
LCK.smp.destroy              0         0.00 Destroyed locks
LCK.smp.locks                0         0.00 Lock Operations
LCK.smp.colls                0         0.00 Collisions
LCK.sma.creat                1         0.00 Created locks
LCK.sma.destroy              0         0.00 Destroyed locks
LCK.sma.locks          6474775       280.61 Lock Operations
LCK.sma.colls                0         0.00 Collisions
LCK.smf.creat                1         0.00 Created locks
LCK.smf.destroy              0         0.00 Destroyed locks
LCK.smf.locks            30590         1.33 Lock Operations
LCK.smf.colls                0         0.00 Collisions
LCK.hsl.creat                0         0.00 Created locks
LCK.hsl.destroy              0         0.00 Destroyed locks
LCK.hsl.locks                0         0.00 Lock Operations
LCK.hsl.colls                0         0.00 Collisions
LCK.hcb.creat                1         0.00 Created locks
LCK.hcb.destroy              0         0.00 Destroyed locks
LCK.hcb.locks             7801         0.34 Lock Operations
LCK.hcb.colls                0         0.00 Collisions
LCK.hcl.creat                0         0.00 Created locks
LCK.hcl.destroy              0         0.00 Destroyed locks
LCK.hcl.locks                0         0.00 Lock Operations
LCK.hcl.colls                0         0.00 Collisions
LCK.vcl.creat                1         0.00 Created locks
LCK.vcl.destroy              0         0.00 Destroyed locks
LCK.vcl.locks             3987         0.17 Lock Operations
LCK.vcl.colls                0         0.00 Collisions
LCK.stat.creat               1         0.00 Created locks
LCK.stat.destroy             0         0.00 Destroyed locks
LCK.stat.locks             547         0.02 Lock Operations
LCK.stat.colls               0         0.00 Collisions
LCK.sessmem.creat            1         0.00 Created locks
LCK.sessmem.destroy            0         0.00 Destroyed locks
LCK.sessmem.locks          43217         1.87 Lock Operations
LCK.sessmem.colls              0         0.00 Collisions
LCK.wstat.creat                1         0.00 Created locks
LCK.wstat.destroy              0         0.00 Destroyed locks
LCK.wstat.locks            74248         3.22 Lock Operations
LCK.wstat.colls                0         0.00 Collisions
LCK.herder.creat               1         0.00 Created locks
LCK.herder.destroy             0         0.00 Destroyed locks
LCK.herder.locks            5250         0.23 Lock Operations
LCK.herder.colls               0         0.00 Collisions
LCK.wq.creat                   2         0.00 Created locks
LCK.wq.destroy                 0         0.00 Destroyed locks
LCK.wq.locks             2618934       113.50 Lock Operations
LCK.wq.colls                   0         0.00 Collisions
LCK.objhdr.creat            4840         0.21 Created locks
LCK.objhdr.destroy          4629         0.20 Destroyed locks
LCK.objhdr.locks          243135        10.54 Lock Operations
LCK.objhdr.colls               0         0.00 Collisions
LCK.exp.creat                  1         0.00 Created locks
LCK.exp.destroy                0         0.00 Destroyed locks
LCK.exp.locks              33597         1.46 Lock Operations
LCK.exp.colls                  0         0.00 Collisions
LCK.lru.creat                  2         0.00 Created locks
LCK.lru.destroy                0         0.00 Destroyed locks
LCK.lru.locks               5386         0.23 Lock Operations
LCK.lru.colls                  0         0.00 Collisions
LCK.cli.creat                  1         0.00 Created locks
LCK.cli.destroy                0         0.00 Destroyed locks
LCK.cli.locks               7696         0.33 Lock Operations
LCK.cli.colls                  0         0.00 Collisions
LCK.ban.creat                  1         0.00 Created locks
LCK.ban.destroy                0         0.00 Destroyed locks
LCK.ban.locks              33611         1.46 Lock Operations
LCK.ban.colls                  0         0.00 Collisions
LCK.vbp.creat                  1         0.00 Created locks
LCK.vbp.destroy                0         0.00 Destroyed locks
LCK.vbp.locks                  0         0.00 Lock Operations
LCK.vbp.colls                  0         0.00 Collisions
LCK.vbe.creat                  1         0.00 Created locks
LCK.vbe.destroy                0         0.00 Destroyed locks
LCK.vbe.locks              43813         1.90 Lock Operations
LCK.vbe.colls                  0         0.00 Collisions
LCK.backend.creat              1         0.00 Created locks
LCK.backend.destroy            0         0.00 Destroyed locks
LCK.backend.locks        3050125       132.19 Lock Operations
LCK.backend.colls              0         0.00 Collisions
SMF.s0.c_req               12925         0.56 Allocator requests
SMF.s0.c_fail                  0         0.00 Allocator failures
SMF.s0.c_bytes         812273664     35202.98 Bytes allocated
SMF.s0.c_freed         799502336     34649.49 Bytes freed
SMF.s0.g_alloc               311          .   Allocations outstanding
SMF.s0.g_bytes          12771328          .   Bytes outstanding
SMF.s0.g_space         524099584          .   Bytes available
SMF.s0.g_smf                 383          .   N struct smf
SMF.s0.g_smf_frag             60          .   N small free smf
SMF.s0.g_smf_large            12          .   N large free smf
SMA.Transient.c_req      3010912       130.49 Allocator requests
SMA.Transient.c_fail           0         0.00 Allocator failures
SMA.Transient.c_bytes  63026331110   2731487.00 Bytes allocated
SMA.Transient.c_freed  63026331110   2731487.00 Bytes freed
SMA.Transient.g_alloc            0          .   Allocations outstanding
SMA.Transient.g_bytes            0          .   Bytes outstanding
SMA.Transient.g_space            0          .   Bytes available
VBE.default(127.0.0.1,,8080).vcls            1          .   VCL references
VBE.default(127.0.0.1,,8080).happy           0          .   Happy health probes"""

        self.xml_dump = """<?xml version="1.0"?>
        <varnishstat timestamp="2012-05-21T17:19:59">
        	<stat>
        		<name>client_conn</name>
        		<value>475607</value>
        		<flag>a</flag>
        		<description>Client connections accepted</description>
        	</stat>
        	<stat>
        		<name>client_drop</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Connection dropped, no sess/wrk</description>
        	</stat>
        	<stat>
        		<name>client_req</name>
        		<value>46007888</value>
        		<flag>a</flag>
        		<description>Client requests received</description>
        	</stat>
        	<stat>
        		<name>cache_hit</name>
        		<value>29652727</value>
        		<flag>a</flag>
        		<description>Cache hits</description>
        	</stat>
        	<stat>
        		<name>cache_hitpass</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Cache hits for pass</description>
        	</stat>
        	<stat>
        		<name>cache_miss</name>
        		<value>11551328</value>
        		<flag>a</flag>
        		<description>Cache misses</description>
        	</stat>
        	<stat>
        		<name>backend_conn</name>
        		<value>187918</value>
        		<flag>a</flag>
        		<description>Backend conn. success</description>
        	</stat>
        	<stat>
        		<name>backend_unhealthy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Backend conn. not attempted</description>
        	</stat>
        	<stat>
        		<name>backend_busy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Backend conn. too many</description>
        	</stat>
        	<stat>
        		<name>backend_fail</name>
        		<value>912</value>
        		<flag>a</flag>
        		<description>Backend conn. failures</description>
        	</stat>
        	<stat>
        		<name>backend_reuse</name>
        		<value>16078929</value>
        		<flag>a</flag>
        		<description>Backend conn. reuses</description>
        	</stat>
        	<stat>
        		<name>backend_toolate</name>
        		<value>13560</value>
        		<flag>a</flag>
        		<description>Backend conn. was closed</description>
        	</stat>
        	<stat>
        		<name>backend_recycle</name>
        		<value>16092503</value>
        		<flag>a</flag>
        		<description>Backend conn. recycles</description>
        	</stat>
        	<stat>
        		<name>backend_retry</name>
        		<value>45</value>
        		<flag>a</flag>
        		<description>Backend conn. retry</description>
        	</stat>
        	<stat>
        		<name>fetch_head</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Fetch head</description>
        	</stat>
        	<stat>
        		<name>fetch_length</name>
        		<value>12638932</value>
        		<flag>a</flag>
        		<description>Fetch with Length</description>
        	</stat>
        	<stat>
        		<name>fetch_chunked</name>
        		<value>3627795</value>
        		<flag>a</flag>
        		<description>Fetch chunked</description>
        	</stat>
        	<stat>
        		<name>fetch_eof</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Fetch EOF</description>
        	</stat>
        	<stat>
        		<name>fetch_bad</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Fetch had bad headers</description>
        	</stat>
        	<stat>
        		<name>fetch_close</name>
        		<value>36</value>
        		<flag>a</flag>
        		<description>Fetch wanted close</description>
        	</stat>
        	<stat>
        		<name>fetch_oldhttp</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Fetch pre HTTP/1.1 closed</description>
        	</stat>
        	<stat>
        		<name>fetch_zero</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Fetch zero len</description>
        	</stat>
        	<stat>
        		<name>fetch_failed</name>
        		<value>9</value>
        		<flag>a</flag>
        		<description>Fetch failed</description>
        	</stat>
        	<stat>
        		<name>fetch_1xx</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Fetch no body (1xx)</description>
        	</stat>
        	<stat>
        		<name>fetch_204</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Fetch no body (204)</description>
        	</stat>
        	<stat>
        		<name>fetch_304</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Fetch no body (304)</description>
        	</stat>
        	<stat>
        		<name>n_sess_mem</name>
        		<value>334</value>
        		<flag>i</flag>
        		<description>N struct sess_mem</description>
        	</stat>
        	<stat>
        		<name>n_sess</name>
        		<value>31</value>
        		<flag>i</flag>
        		<description>N struct sess</description>
        	</stat>
        	<stat>
        		<name>n_object</name>
        		<value>391072</value>
        		<flag>i</flag>
        		<description>N struct object</description>
        	</stat>
        	<stat>
        		<name>n_vampireobject</name>
        		<value>0</value>
        		<flag>i</flag>
        		<description>N unresurrected objects</description>
        	</stat>
        	<stat>
        		<name>n_objectcore</name>
        		<value>391086</value>
        		<flag>i</flag>
        		<description>N struct objectcore</description>
        	</stat>
        	<stat>
        		<name>n_objecthead</name>
        		<value>119540</value>
        		<flag>i</flag>
        		<description>N struct objecthead</description>
        	</stat>
        	<stat>
        		<name>n_waitinglist</name>
        		<value>42255</value>
        		<flag>i</flag>
        		<description>N struct waitinglist</description>
        	</stat>
        	<stat>
        		<name>n_vbc</name>
        		<value>13</value>
        		<flag>i</flag>
        		<description>N struct vbc</description>
        	</stat>
        	<stat>
        		<name>n_wrk</name>
        		<value>24</value>
        		<flag>i</flag>
        		<description>N worker threads</description>
        	</stat>
        	<stat>
        		<name>n_wrk_create</name>
        		<value>3718</value>
        		<flag>a</flag>
        		<description>N worker threads created</description>
        	</stat>
        	<stat>
        		<name>n_wrk_failed</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>N worker threads not created</description>
        	</stat>
        	<stat>
        		<name>n_wrk_max</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>N worker threads limited</description>
        	</stat>
        	<stat>
        		<name>n_wrk_lqueue</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>work request queue length</description>
        	</stat>
        	<stat>
        		<name>n_wrk_queued</name>
        		<value>37387</value>
        		<flag>a</flag>
        		<description>N queued work requests</description>
        	</stat>
        	<stat>
        		<name>n_wrk_drop</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>N dropped work requests</description>
        	</stat>
        	<stat>
        		<name>n_backend</name>
        		<value>17</value>
        		<flag>i</flag>
        		<description>N backends</description>
        	</stat>
        	<stat>
        		<name>n_expired</name>
        		<value>5509942</value>
        		<flag>i</flag>
        		<description>N expired objects</description>
        	</stat>
        	<stat>
        		<name>n_lru_nuked</name>
        		<value>5650303</value>
        		<flag>i</flag>
        		<description>N LRU nuked objects</description>
        	</stat>
        	<stat>
        		<name>n_lru_moved</name>
        		<value>14960592</value>
        		<flag>i</flag>
        		<description>N LRU moved objects</description>
        	</stat>
        	<stat>
        		<name>losthdr</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>HTTP header overflows</description>
        	</stat>
        	<stat>
        		<name>n_objsendfile</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Objects sent with sendfile</description>
        	</stat>
        	<stat>
        		<name>n_objwrite</name>
        		<value>46952631</value>
        		<flag>a</flag>
        		<description>Objects sent with write</description>
        	</stat>
        	<stat>
        		<name>n_objoverflow</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Objects overflowing workspace</description>
        	</stat>
        	<stat>
        		<name>s_sess</name>
        		<value>475606</value>
        		<flag>a</flag>
        		<description>Total Sessions</description>
        	</stat>
        	<stat>
        		<name>s_req</name>
        		<value>46007888</value>
        		<flag>a</flag>
        		<description>Total Requests</description>
        	</stat>
        	<stat>
        		<name>s_pipe</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Total pipe</description>
        	</stat>
        	<stat>
        		<name>s_pass</name>
        		<value>4715470</value>
        		<flag>a</flag>
        		<description>Total pass</description>
        	</stat>
        	<stat>
        		<name>s_fetch</name>
        		<value>16266754</value>
        		<flag>a</flag>
        		<description>Total fetch</description>
        	</stat>
        	<stat>
        		<name>s_hdrbytes</name>
        		<value>13489812656</value>
        		<flag>a</flag>
        		<description>Total header bytes</description>
        	</stat>
        	<stat>
        		<name>s_bodybytes</name>
        		<value>870366768630</value>
        		<flag>a</flag>
        		<description>Total body bytes</description>
        	</stat>
        	<stat>
        		<name>sess_closed</name>
        		<value>90657</value>
        		<flag>a</flag>
        		<description>Session Closed</description>
        	</stat>
        	<stat>
        		<name>sess_pipeline</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Session Pipeline</description>
        	</stat>
        	<stat>
        		<name>sess_readahead</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Session Read Ahead</description>
        	</stat>
        	<stat>
        		<name>sess_linger</name>
        		<value>45917694</value>
        		<flag>a</flag>
        		<description>Session Linger</description>
        	</stat>
        	<stat>
        		<name>sess_herd</name>
        		<value>15876611</value>
        		<flag>a</flag>
        		<description>Session herd</description>
        	</stat>
        	<stat>
        		<name>shm_records</name>
        		<value>2312772697</value>
        		<flag>a</flag>
        		<description>SHM records</description>
        	</stat>
        	<stat>
        		<name>shm_writes</name>
        		<value>97762309</value>
        		<flag>a</flag>
        		<description>SHM writes</description>
        	</stat>
        	<stat>
        		<name>shm_flushes</name>
        		<value>3</value>
        		<flag>a</flag>
        		<description>SHM flushes due to overflow</description>
        	</stat>
        	<stat>
        		<name>shm_cont</name>
        		<value>31213</value>
        		<flag>a</flag>
        		<description>SHM MTX contention</description>
        	</stat>
        	<stat>
        		<name>shm_cycles</name>
        		<value>967</value>
        		<flag>a</flag>
        		<description>SHM cycles through buffer</description>
        	</stat>
        	<stat>
        		<name>sms_nreq</name>
        		<value>88407</value>
        		<flag>a</flag>
        		<description>SMS allocator requests</description>
        	</stat>
        	<stat>
        		<name>sms_nobj</name>
        		<value>0</value>
        		<flag>i</flag>
        		<description>SMS outstanding allocations</description>
        	</stat>
        	<stat>
        		<name>sms_nbytes</name>
        		<value>0</value>
        		<flag>i</flag>
        		<description>SMS outstanding bytes</description>
        	</stat>
        	<stat>
        		<name>sms_balloc</name>
        		<value>477828</value>
        		<flag>i</flag>
        		<description>SMS bytes allocated</description>
        	</stat>
        	<stat>
        		<name>sms_bfree</name>
        		<value>477828</value>
        		<flag>i</flag>
        		<description>SMS bytes freed</description>
        	</stat>
        	<stat>
        		<name>backend_req</name>
        		<value>16266804</value>
        		<flag>a</flag>
        		<description>Backend requests made</description>
        	</stat>
        	<stat>
        		<name>n_vcl</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>N vcl total</description>
        	</stat>
        	<stat>
        		<name>n_vcl_avail</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>N vcl available</description>
        	</stat>
        	<stat>
        		<name>n_vcl_discard</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>N vcl discarded</description>
        	</stat>
        	<stat>
        		<name>n_ban</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>N total active bans</description>
        	</stat>
        	<stat>
        		<name>n_ban_add</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>N new bans added</description>
        	</stat>
        	<stat>
        		<name>n_ban_retire</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>N old bans deleted</description>
        	</stat>
        	<stat>
        		<name>n_ban_obj_test</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>N objects tested</description>
        	</stat>
        	<stat>
        		<name>n_ban_re_test</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>N regexps tested against</description>
        	</stat>
        	<stat>
        		<name>n_ban_dups</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>N duplicate bans removed</description>
        	</stat>
        	<stat>
        		<name>hcb_nolock</name>
        		<value>41204059</value>
        		<flag>a</flag>
        		<description>HCB Lookups without lock</description>
        	</stat>
        	<stat>
        		<name>hcb_lock</name>
        		<value>3053198</value>
        		<flag>a</flag>
        		<description>HCB Lookups with lock</description>
        	</stat>
        	<stat>
        		<name>hcb_insert</name>
        		<value>3053197</value>
        		<flag>a</flag>
        		<description>HCB Inserts</description>
        	</stat>
        	<stat>
        		<name>esi_errors</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>ESI parse errors (unlock)</description>
        	</stat>
        	<stat>
        		<name>esi_warnings</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>ESI parse warnings (unlock)</description>
        	</stat>
        	<stat>
        		<name>accept_fail</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Accept failures</description>
        	</stat>
        	<stat>
        		<name>client_drop_late</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Connection dropped late</description>
        	</stat>
        	<stat>
        		<name>uptime</name>
        		<value>265069</value>
        		<flag>a</flag>
        		<description>Client uptime</description>
        	</stat>
        	<stat>
        		<name>dir_dns_lookups</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>DNS director lookups</description>
        	</stat>
        	<stat>
        		<name>dir_dns_failed</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>DNS director failed lookups</description>
        	</stat>
        	<stat>
        		<name>dir_dns_hit</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>DNS director cached lookups hit</description>
        	</stat>
        	<stat>
        		<name>dir_dns_cache_full</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>DNS director full dnscache</description>
        	</stat>
        	<stat>
        		<name>vmods</name>
        		<value>0</value>
        		<flag>i</flag>
        		<description>Loaded VMODs</description>
        	</stat>
        	<stat>
        		<name>n_gzip</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Gzip operations</description>
        	</stat>
        	<stat>
        		<name>n_gunzip</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Gunzip operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sms</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sms</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sms</ident>
        		<name>locks</name>
        		<value>265221</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sms</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>smp</ident>
        		<name>creat</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>smp</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>smp</ident>
        		<name>locks</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>smp</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sma</ident>
        		<name>creat</name>
        		<value>2</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sma</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sma</ident>
        		<name>locks</name>
        		<value>74266910</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sma</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>smf</ident>
        		<name>creat</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>smf</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>smf</ident>
        		<name>locks</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>smf</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hsl</ident>
        		<name>creat</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hsl</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hsl</ident>
        		<name>locks</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hsl</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hcb</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hcb</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hcb</ident>
        		<name>locks</name>
        		<value>5991389</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hcb</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hcl</ident>
        		<name>creat</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hcl</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hcl</ident>
        		<name>locks</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>hcl</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vcl</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vcl</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vcl</ident>
        		<name>locks</name>
        		<value>82036</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vcl</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>stat</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>stat</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>stat</ident>
        		<name>locks</name>
        		<value>334</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>stat</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sessmem</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sessmem</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sessmem</ident>
        		<name>locks</name>
        		<value>480320</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>sessmem</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>wstat</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>wstat</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>wstat</ident>
        		<name>locks</name>
        		<value>1636233</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>wstat</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>herder</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>herder</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>herder</ident>
        		<name>locks</name>
        		<value>35720</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>herder</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>wq</ident>
        		<name>creat</name>
        		<value>2</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>wq</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>wq</ident>
        		<name>locks</name>
        		<value>32549458</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>wq</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>objhdr</ident>
        		<name>creat</name>
        		<value>3056380</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>objhdr</ident>
        		<name>destroy</name>
        		<value>2936840</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>objhdr</ident>
        		<name>locks</name>
        		<value>195679071</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>objhdr</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>exp</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>exp</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>exp</ident>
        		<name>locks</name>
        		<value>22976360</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>exp</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>lru</ident>
        		<name>creat</name>
        		<value>2</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>lru</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>lru</ident>
        		<name>locks</name>
        		<value>17201617</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>lru</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>cli</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>cli</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>cli</ident>
        		<name>locks</name>
        		<value>88310</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>cli</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>ban</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>ban</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>ban</ident>
        		<name>locks</name>
        		<value>22976610</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>ban</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vbp</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vbp</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vbp</ident>
        		<name>locks</name>
        		<value>1412365</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vbp</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vbe</ident>
        		<name>creat</name>
        		<value>1</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vbe</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vbe</ident>
        		<name>locks</name>
        		<value>377647</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>vbe</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>backend</ident>
        		<name>creat</name>
        		<value>17</value>
        		<flag>a</flag>
        		<description>Created locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>backend</ident>
        		<name>destroy</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Destroyed locks</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>backend</ident>
        		<name>locks</name>
        		<value>52925585</value>
        		<flag>a</flag>
        		<description>Lock Operations</description>
        	</stat>
        	<stat>
        		<type>LCK</type>
        		<ident>backend</ident>
        		<name>colls</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Collisions</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>s0</ident>
        		<name>c_req</name>
        		<value>26057659</value>
        		<flag>a</flag>
        		<description>Allocator requests</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>s0</ident>
        		<name>c_fail</name>
        		<value>732800073660</value>
        		<flag>a</flag>
        		<description>Allocator failures</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>s0</ident>
        		<name>c_bytes</name>
        		<value>506580500540</value>
        		<flag>a</flag>
        		<description>Bytes allocated</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>s0</ident>
        		<name>c_freed</name>
        		<value>500138170202</value>
        		<flag>a</flag>
        		<description>Bytes freed</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>s0</ident>
        		<name>g_alloc</name>
        		<value>791369</value>
        		<flag>i</flag>
        		<description>Allocations outstanding</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>s0</ident>
        		<name>g_bytes</name>
        		<value>6442330338</value>
        		<flag>i</flag>
        		<description>Bytes outstanding</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>s0</ident>
        		<name>g_space</name>
        		<value>120606</value>
        		<flag>i</flag>
        		<description>Bytes available</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>Transient</ident>
        		<name>c_req</name>
        		<value>12490635</value>
        		<flag>a</flag>
        		<description>Allocator requests</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>Transient</ident>
        		<name>c_fail</name>
        		<value>0</value>
        		<flag>a</flag>
        		<description>Allocator failures</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>Transient</ident>
        		<name>c_bytes</name>
        		<value>44213239981</value>
        		<flag>a</flag>
        		<description>Bytes allocated</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>Transient</ident>
        		<name>c_freed</name>
        		<value>44213169757</value>
        		<flag>a</flag>
        		<description>Bytes freed</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>Transient</ident>
        		<name>g_alloc</name>
        		<value>192</value>
        		<flag>i</flag>
        		<description>Allocations outstanding</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>Transient</ident>
        		<name>g_bytes</name>
        		<value>70224</value>
        		<flag>i</flag>
        		<description>Bytes outstanding</description>
        	</stat>
        	<stat>
        		<type>SMA</type>
        		<ident>Transient</ident>
        		<name>g_space</name>
        		<value>0</value>
        		<flag>i</flag>
        		<description>Bytes available</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>default(127.0.0.1,,80)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>default(127.0.0.1,,80)</ident>
        		<name>happy</name>
        		<value>0</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_01(10.93.67.16,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_01(10.93.67.16,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_02(10.93.67.17,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_02(10.93.67.17,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_03(10.93.67.18,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_03(10.93.67.18,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_04(10.93.67.105,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_04(10.93.67.105,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_06(10.93.67.133,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_06(10.93.67.133,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_07(10.93.67.134,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_video_prd_services_07(10.93.67.134,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_article_prd_services_01(10.93.67.75,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_article_prd_services_01(10.93.67.75,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_article_prd_services_02(10.93.67.76,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_article_prd_services_02(10.93.67.76,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_article_prd_services_03(10.93.67.77,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_article_prd_services_03(10.93.67.77,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_article_prd_services_04(10.93.67.121,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_article_prd_services_04(10.93.67.121,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_article_prd_services_05(10.93.67.122,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_article_prd_services_05(10.93.67.122,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_object_prd_services_01(10.93.66.132,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_object_prd_services_01(10.93.66.132,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_object_prd_services_02(10.93.66.150,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_object_prd_services_02(10.93.66.150,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_object_prd_services_03(10.93.67.107,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_object_prd_services_03(10.93.67.107,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_object_prd_services_04(10.93.67.125,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_object_prd_services_04(10.93.67.125,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_object_prd_services_05(10.93.67.126,,8080)</ident>
        		<name>vcls</name>
        		<value>1</value>
        		<flag>i</flag>
        		<description>VCL references</description>
        	</stat>
        	<stat>
        		<type>VBE</type>
        		<ident>media_object_prd_services_05(10.93.67.126,,8080)</ident>
        		<name>happy</name>
        		<value>18446744073709551615</value>
        		<flag>b</flag>
        		<description>Happy health probes</description>
        	</stat>
        </varnishstat>
        """

        self.config = """
init_config:

instances:
    -   varnishstat: /usr/bin/varnishstat
"""


    def test_parsing(self):
        v, instances = get_check('varnish', self.config)
        v._parse_varnishstat(self.v_dump, False)
        metrics = v.get_metrics()
        self.assertEquals([m[2] for m in metrics
            if m[0] == "varnish.n_waitinglist"][0], 980)
        assert "varnish.fetch_length" not in [m[0] for m in metrics]

        # XML parsing
        v._parse_varnishstat(self.xml_dump, True)
        metrics = v.get_metrics()
        self.assertEquals([m[2] for m in metrics
            if m[0] == "varnish.SMA.s0.g_space"][0], 120606)
        assert "varnish.SMA.transient.c_bytes" not in [m[0] for m in metrics]

    def test_check(self):
        v, instances = get_check('varnish', self.config)
        import pprint
        try:
            for i in range(3):
                v.check({"varnishstat": os.popen("which varnishstat").read()[:-1]})
                pprint.pprint(v.get_metrics())
                time.sleep(1)
        except Exception:
            pass

    def test_service_check(self):
        varnishadm_dump = """
Backend b0 is Sick
Current states  good:  0 threshold:  3 window:  5
Average responsetime of good probes: 0.000000
Oldest                                                    Newest
================================================================
4444444444444444444444444444444444444444444444444444444444444444 Good IPv4
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX Good Xmit
RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR Good Recv
---------------------------------------------------------------- Happy
Backend b1 is Sick
Current states  good:  0 threshold:  3 window:  5
Average responsetime of good probes: 0.000000
Oldest                                                    Newest
================================================================
---------------------------------------------------------------- Happy
        """
        v, instances = get_check('varnish', self.config)
        v._parse_varnishadm(varnishadm_dump)
        service_checks = v.get_service_checks()
        self.assertEquals(len(service_checks), 2)

        b0_check = service_checks[0]
        self.assertEquals(b0_check['check'], v.SERVICE_CHECK_NAME)
        self.assertEquals(b0_check['tags'], ['backend:b0'])

        b1_check = service_checks[1]
        self.assertEquals(b1_check['check'], v.SERVICE_CHECK_NAME)
        self.assertEquals(b1_check['tags'], ['backend:b1'])

if __name__ == '__main__':
    unittest.main()
