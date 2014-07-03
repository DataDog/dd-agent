###############################################################################
# ntplib - Python NTP library.
# Copyright (C) 2009 Charles-Francois Natali <neologix@free.fr>
#
# ntplib is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 59
# Temple Place, Suite 330, Boston, MA 0.1.2-1307 USA
###############################################################################

"""Pyton NTP library.

Implementation of client-side NTP (RFC-1305), and useful NTP-related
functions.
"""


import socket
import struct
import time
import datetime

   
# compute delta between system epoch and NTP epoch
SYSTEM_EPOCH = datetime.date(*time.gmtime(0)[0:3])
NTP_EPOCH = datetime.date(1900, 1, 1)
NTP_DELTA = (SYSTEM_EPOCH - NTP_EPOCH).days * 24 * 3600


class NTPException(Exception):
    """Exception raised by this module."""


class NTPPacket(object):
    """NTP packet class.

    This class abstracts the stucture of a NTP packet."""
    
    # packet format to pack/unpack
    ntp_packet_format = '!B B B b 11I'
    
    def __init__(self, version=2, mode=3, tx_timestamp=0):
        self.leap = 0
        self.version = version
        self.mode = mode
        self.stratum = 0
        self.poll = 0
        self.precision = 0
        self.root_delay = 0
        self.root_dispersion = 0
        self.ref_id = 0
        self.ref_timestamp = 0
        self.orig_timestamp = 0
        self.recv_timestamp = 0
        self.tx_timestamp = tx_timestamp
        
    def to_data(self):
        """convert a NTPPacket to a NTP packet that can be sent over network
        raise a NTPException in case of invalid field"""
        try:
            packed = struct.pack(NTPPacket.ntp_packet_format,
                (self.leap << 6 | self.version << 3 | self.mode),
                self.stratum,
                self.poll,
                self.precision,
                to_int(self.root_delay) << 16 | to_frac(self.root_delay, 16),
                to_int(self.root_dispersion) << 16 |
                    to_frac(self.root_dispersion, 16),
                self.ref_id,
                to_int(self.ref_timestamp),
                to_frac(self.ref_timestamp),
                to_int(self.orig_timestamp),
                to_frac(self.orig_timestamp),
                to_int(self.recv_timestamp),
                to_frac(self.recv_timestamp),
                to_int(self.tx_timestamp),
                to_frac(self.tx_timestamp))
        except struct.error:
            raise NTPException('Invalid NTP packet fields')

        return packed

    def from_data(self, data):
        """build a NTPPacket from a NTP packet received from network
        raise an NTPException in case of invalid packet format"""
        try:
            unpacked = struct.unpack(NTPPacket.ntp_packet_format,
                    data[0:struct.calcsize(NTPPacket.ntp_packet_format)])
        except struct.error:
            raise NTPException('Invalid NTP packet')

        self.leap = unpacked[0] >> 6 & 0x3
        self.version = unpacked[0] >> 3 & 0x7
        self.mode = unpacked[0] & 0x7
        self.stratum = unpacked[1]
        self.poll = unpacked[2]
        self.precision = unpacked[3]
        self.root_delay = float(unpacked[4])/2**16
        self.root_dispersion = float(unpacked[5])/2**16
        self.ref_id = unpacked[6]
        self.ref_timestamp = to_time(unpacked[7], unpacked[8])
        self.orig_timestamp = to_time(unpacked[9], unpacked[10])
        self.recv_timestamp = to_time(unpacked[11], unpacked[12])
        self.tx_timestamp = to_time(unpacked[13], unpacked[14])
        

class NTPStats(NTPPacket):
    """wrapper for NTPPacket, offering additional statistics like offset and
    delay, and timestamps converted to local time"""
    
    def __init__(self, dest_timestamp):
        NTPPacket.__init__(self)
        self.dest_timestamp = dest_timestamp
        
    @property
    def offset(self):
        """NTP offset"""
        return ((self.recv_timestamp - self.orig_timestamp) +
                    (self.tx_timestamp - self.dest_timestamp))/2
    
    @property
    def delay(self):
        """NTP delay"""
        return ((self.dest_timestamp - self.orig_timestamp) -
                    (self.tx_timestamp - self.recv_timestamp))
    
    @property
    def tx_time(self):
        """tx_timestamp - local time"""
        return ntp_to_system_time(self.tx_timestamp)

    @property
    def recv_time(self):
        """recv_timestamp - local time"""
        return ntp_to_system_time(self.recv_timestamp)
    
    @property
    def orig_time(self):
        """orig_timestamp - local time"""
        return ntp_to_system_time(self.orig_timestamp)
    
    @property
    def ref_time(self):
        """ref_timestamp - local time"""
        return ntp_to_system_time(self.ref_timestamp)
    
    @property
    def dest_time(self):
        """dest_timestamp - local time"""
        return ntp_to_system_time(self.dest_timestamp)


class NTPClient(object):
    """Client session - for now, a mere wrapper for NTP requests"""
    
    def request(self, host, version=2, port='ntp'):
        """make a NTP request to a server - return a NTPStats object"""
        # lookup server address
        addrinfo = socket.getaddrinfo(host, port)[0]
        family, sockaddr = addrinfo[0], addrinfo[4]

        # create the socket
        s = socket.socket(family, socket.SOCK_DGRAM)
        s.settimeout(5)

        # create the request packet - mode 3 is client
        query = NTPPacket(mode=3, version=version,
                            tx_timestamp=system_to_ntp_time(time.time()))
        query_packet = query.to_data()
    
        try:
            # send the request
            s.sendto(query_packet, sockaddr)
            
            # wait for the response - check the source address
            src_addr = (None, None)
            while src_addr[0] != sockaddr[0]:
                (response_packet, src_addr) = s.recvfrom(256)

            # build the destination timestamp
            dest_timestamp = system_to_ntp_time(time.time())
        finally:
            # no matter what happens, we must close the socket
            # if an exception was raised, let the application hanle it
            s.close()
                    
        # construct corresponding statistics
        response = NTPStats(dest_timestamp)
        response.from_data(response_packet)
        
        return response
    

def to_int(date):
    """return the integral part of a timestamp"""
    return int(date)

def to_frac(date, n=32):
    """return the fractional part of a timestamp - n is the number of bits of
    the fractional part"""
    return int(abs(date - to_int(date)) * 2**n)

def to_time(integ, frac, n=32):
    """build a timestamp from an integral and fractional part - n is the
    number of bits of the fractional part"""
    return integ + float(frac)/2**n

def ntp_to_system_time(date):
    """convert a NTP time to system time"""
    return date - NTP_DELTA

def system_to_ntp_time(date):
    """convert a system time to a NTP time"""
    return date + NTP_DELTA

def leap_to_text(leap):
    """convert a leap value to text"""
    leap_table = {
        0: 'no warning',
        1: 'last minute has 61 seconds',
        2: 'last minute has 59 seconds',
        3: 'alarm condition (clock not synchronized)',
    }

    if leap in leap_table:
        return leap_table[leap]
    else:
        raise NTPException('Invalid leap indicator')

def mode_to_text(mode):
    """convert a mode value to text"""
    mode_table = {
        0: 'unspecified',
        1: 'symmetric active',
        2: 'symmetric passive',
        3: 'client',
        4: 'server',
        5: 'broadcast',
        6: 'reserved for NTP control messages',
        7: 'reserved for private use',
    }

    if mode in mode_table:
        return mode_table[mode]
    else:
        raise NTPException('Invalid mode')

def stratum_to_text(stratum):
    """convert a stratum value to text"""
    stratum_table = {
        0: 'unspecified',
        1: 'primary reference',
    }

    if stratum in stratum_table:
        return stratum_table[stratum]
    elif 1 < stratum < 255:
        return 'secondary reference (NTP)'
    else:
        raise NTPException('Invalid stratum')

def ref_id_to_text(ref_id, stratum=2):
    """convert a reference identifier to text according to stratum"""
    ref_id_table = {
            'DNC': 'DNC routing protocol',
            'NIST': 'NIST public modem',
            'TSP': 'TSP time protocol',
            'DTS': 'Digital Time Service',
            'ATOM': 'Atomic clock (calibrated)',
            'VLF': 'VLF radio (OMEGA, etc)',
            'callsign': 'Generic radio',
            'LORC': 'LORAN-C radionavidation',
            'GOES': 'GOES UHF environment satellite',
            'GPS': 'GPS UHF satellite positioning',
    }

    fields = (ref_id >> 24 & 0xff, ref_id >> 16 & 0xff,
                ref_id >> 8 & 0xff, ref_id & 0xff)

    # return the result as a string or dot-formatted IP address
    if 0 <= stratum <= 1 :
        text = '%c%c%c%c' % fields
        if text in ref_id_table:
            return ref_id_table[text]
        else:
            return text
    elif 2 <= stratum < 255:
        return '%d.%d.%d.%d' % fields
    else:
        raise NTPException('Invalid reference clock identifier')
