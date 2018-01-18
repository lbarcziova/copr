#!/usr/bin/env python2

from __future__ import print_function

import re
import sys
import requests
import json
import os
import logging
import argparse
import netaddr

sys.path.append("/usr/share/copr/")

from dateutil.parser import parse as dt_parse
from netaddr import IPNetwork, IPAddress

from collections import defaultdict
from backend.helpers import BackendConfigReader

opts = BackendConfigReader().read()

logging.basicConfig(
    filename="/var/log/copr-backend/hitcounter.log",
    format='[%(asctime)s][%(thread)s][%(levelname)6s]: %(message)s',
    level=logging.INFO)

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))

spider_regex = re.compile('.*(ahrefs|bot/[0-9]|bingbot|borg|google|googlebot|yahoo|slurp|msnbot|msrbot'
                          '|openbot|archiver|netresearch|lycos|scooter|altavista|teoma|gigabot|baiduspider'
                          '|blitzbot|oegp|charlotte|furlbot|http://client|polybot|htdig|ichiro|mogimogi'
                          '|larbin|pompos|scrubby|searchsight|seekbot|semanticdiscovery|silk|snappy|speedy'
                          '|spider|voila|vortex|voyager|zao|zeal|fast-webcrawler|converacrawler|dataparksearch'
                          '|findlinks|crawler|yandex|blexbot|semrushbot).*', re.IGNORECASE)

logline_regex = re.compile(
    r'(?P<ip_address>.*)\s+(?P<hostname>.*)\s+-\s+\[(?P<timestamp>.*)\]\s+'
    r'"GET (?P<url>.*)\s+(?P<protocol>.*)"\s+(?P<code>.*)\s+(?P<bytes_sent>.*)\s+'
    r'"(?P<referer>.*)"\s+"(?P<agent>.*)"', re.IGNORECASE)

repomd_url_regex = re.compile("/results/(?P<owner>[^/]*)/(?P<project>[^/]*)/(?P<chroot>[^/]*)/repodata/repomd.xml", re.IGNORECASE)
rpm_url_regex = re.compile("/results/(?P<owner>[^/]*)/(?P<project>[^/]*)/(?P<chroot>[^/]*)/(?P<build_dir>[^/]*)/(?P<rpm>[^/]*\.rpm)", re.IGNORECASE)

datetime_regex = re.compile(".*\[(?P<date>[^:]*):(?P<time>\S*)\s(?P<zone>[^\]]*)\].*")
datetime_parse_template = '{date} {time} {zone}'

parser = argparse.ArgumentParser(description='Read lighttpd access.log and count repo accesses.')
parser.add_argument('--ignore-subnet',action='store', help='What IPs to ignore')
parser.add_argument('logfile', action='store', help='Path to the logfile')


def get_hit_data():
    hits = defaultdict(int)

    first_line = None
    last_line = None
    with open(sys.argv[1], 'r') as logfile:
        logline = None
        for logline in logfile:
            if not first_line:
                first_line = logline

            m = logline_regex.match(logline)
            if not m:
                continue

            if m.group('code') != str(200):
                continue

            if args.ignore_subnet:
                try:
                    if IPAddress(m.group('ip_address')) in IPNetwork(args.ignore_subnet):
                        continue
                except netaddr.core.AddrFormatError:
                    continue

            if spider_regex.match(m.group('agent')):
                continue

            url_match = repomd_url_regex.match(m.group('url'))
            if url_match:
                chroot_key = (
                    'chroot_repo_metadata_dl_stat',
                    url_match.group('owner'),
                    url_match.group('project'),
                    url_match.group('chroot')
                )
                chroot_key_str = '|'.join(chroot_key)
                hits[chroot_key_str] += 1
                continue

            url_match = rpm_url_regex.match(m.group('url'))
            if url_match:
                chroot_key = (
                    'chroot_rpms_dl_stat',
                    url_match.group('owner'),
                    url_match.group('project'),
                    url_match.group('chroot')
                )
                chroot_key_str = '|'.join(chroot_key)
                hits[chroot_key_str] += 1
                project_key = (
                    'project_rpms_dl_stat',
                    url_match.group('owner'),
                    url_match.group('project')
                )
                project_key_str = '|'.join(project_key)
                hits[project_key_str] += 1
                continue
        last_line = logline

    return {
        'ts_from': get_timestamp(first_line),
        'ts_to': get_timestamp(last_line),
        'hits': hits,
    }


def get_timestamp(logline):
    if not logline:
        return None

    m = datetime_regex.match(logline)
    if not m:
        return None

    datetime_str = datetime_parse_template.format(
        date=m.group('date'),
        time=m.group('time'),
        zone=m.group('zone')
    )

    return int(dt_parse(datetime_str).strftime('%s'))


if __name__ == "__main__":
    args = parser.parse_args()
    result = get_hit_data()
    result_json = json.dumps(result)
    target_uri = os.path.join(opts.frontend_base_url, 'stats_rcv' , 'from_backend')
    log.info('Sending: {} results from {} to {}'.format(
        len(result['hits']),
        result['ts_from'],
        result['ts_to']))
    r = requests.post(target_uri, json=result_json)
    log.info('Received: {} {}'.format(r.status_code, r.text))