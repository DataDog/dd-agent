#
# requires pyst2 for Asterisk Manager Interface
# https://github.com/rdegges/pyst2
#
# requires re for regular expression matching on asterisk output
#
#

import asterisk.manager
import re
from checks import AgentCheck

class AsteriskCheck(AgentCheck):

    def check(self, instance):

        if 'host' not in instance:
            instance['host'] = 'localhost'
        if 'manager_user' not in instance:
            self.log.error('manager_user not defined, skipping')
            return
        if 'manager_secret' not in instance:
            self.log.error('manager_secret not defined, skipping')
            return


######  Connect
        mgr = asterisk.manager.Manager()
        try:
            if 'port' in instance:
                mgr.connect(instance['host'],instance['port'])
            else:
                mgr.connect(instance['host'])
            mgr.login(instance['manager_user'],instance['manager_secret'])
        except asterisk.manager.ManagerSocketException as e:
            self.log.error('Error connecting to Asterisk Manager Interface')
            mgr.close()
            return
        except asterisk.manager.ManagerAuthException as e:
            self.log.error('Error Logging in to Asterisk Manager Interface')
            mgr.close()
            return

##### Call Volume
        call_volume = mgr.command('core show calls')

        current_call_vol = call_volume.data.split('\n')

        current_call_vol = current_call_vol[0].replace('active call','')
        current_call_vol = current_call_vol.replace('s','')
        current_call_vol = current_call_vol.replace(' ','')

        self.gauge('asterisk.callvolume',current_call_vol)

##### SIP Peers
        sip_result = mgr.command('sip show peers')

        sip_results = sip_result.data.split('\n')

        siptotals = sip_results[len(sip_results)-3]

        siptotal = re.findall(r'([0-9]+) sip peer',siptotals)[0]

        monitored_peers = re.findall(r'Monitored: ([0-9]+) online, ([0-9]+) offline',siptotals)[0]
        unmonitored_peers = re.findall(r'Unmonitored: ([0-9]+) online, ([0-9]+) offline',siptotals)[0]

        self.gauge('asterisk.sip.peers',siptotal)
        self.gauge('asterisk.sip.monitored.online',monitored_peers[0])
        self.gauge('asterisk.sip.monitored.offline',monitored_peers[1])
        self.gauge('asterisk.sip.unmonitored.online',unmonitored_peers[0])
        self.gauge('asterisk.sip.unmonitored.offline',unmonitored_peers[1])
        
##### SIP Trunks (You have to add '-trunk' string into your SIP trunk name to detect it as a Trunk)
        sip_total_trunks = 0
        sip_online_trunks = 0
        sip_offline_trunks = 0


        for chan in sip_results:
            if chan != None:
                chan_data = chan.split()

                if len(chan_data) > 1:
                    if "-trunk" in chan_data[0]:
                        sip_total_trunks += 1
                        if len(chan_data) > 2 and "OK" in chan_data[5]:
                            sip_online_trunks += 1
                        if len(chan_data) > 2 and chan_data[5] == "UNREACHABLE":
                            sip_offline_trunks += 1
                            
        self.gauge('asterisk.sip.trunks.total',sip_total_trunks)
        self.gauge('asterisk.sip.trunks.online',sip_online_trunks)
        self.gauge('asterisk.sip.trunks.offline',sip_offline_trunks)

##### PRI In Use

        pri = mgr.command('pri show channels')

        pri_channels = pri.data.split('\n')

        pri_channels[0] = None
        pri_channels[1] = None

        openchannels = 0
        for chan in pri_channels:
            if chan != None:
                chan_data = chan.split()
                if len(chan_data) > 2 and chan_data[3] == "No":
                    openchannels += 1

        self.gauge('asterisk.pri.channelsinuse',openchannels)

##### IAX2 Peers

        iax_result = mgr.command('iax2 show peers')

        iax_results = iax_result.data.split('\n')

        iax_total_line = iax_results[len(iax_results)-3]

        iax_peers_total = re.findall(r'([0-9]+) iax2 peers',iax_total_line)[0]
        iax_peers_online = re.findall(r'\[([0-9]+) online',iax_total_line)[0]
        iax_peers_offline = re.findall(r'([0-9]+) offline',iax_total_line)[0]
        iax_peers_unmonitored = re.findall(r'([0-9]+) unmonitored',iax_total_line)[0]

        self.gauge('asterisk.iax2.peers',iax_peers_total)
        self.gauge('asterisk.iax2.online',iax_peers_online)
        self.gauge('asterisk.iax2.offline',iax_peers_offline)
        self.gauge('asterisk.iax2.unmonitored',iax_peers_unmonitored)
        
##### DAHDI Channels  
        
        dahdi_result = mgr.command('dahdi show status')

        dahdi_results = dahdi_result.data.split('\n')
        
        dahdi_total_trunks = len(dahdi_results)-3
        
        dahdi_results[0] = None
        
        dahdi_online_trunks = 0
        dahdi_offline_trunks = 0
        
        for chan in dahdi_results:
            if chan != None:
                chan_data = chan.split()

                if len(chan_data) > 1:
                    if "Wildcard" in chan_data[0]:
                        if len(chan_data) > 2 and chan_data[2] == "OK":
                            dahdi_online_trunks += 1
                        if len(chan_data) > 2 and chan_data[2] == "RED":
                            dahdi_offline_trunks += 1

                    if "wanpipe" in chan_data[0]:
                        if len(chan_data) > 2 and chan_data[3] == "OK":
                            dahdi_online_trunks += 1
                        if len(chan_data) > 2 and chan_data[3] == "RED":
                            dahdi_offline_trunks += 1
                    
        self.gauge('asterisk.dahdi.total',dahdi_total_trunks)
        self.gauge('asterisk.dahdi.online',dahdi_online_trunks)
        self.gauge('asterisk.dahdi.offline',dahdi_offline_trunks)

##### Close connection

        mgr.close()
