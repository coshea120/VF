#!/usr/bin/end python

import re

regex = r'(?P<vlan>\d{1,4})\s+(?P<mac_addr>\w{4}.\w{4}.\w{4})\s+(?P<type>(\w+))\s+(?P<port>(\S+))'

with open("./TableSample", "r") as handle:
    for line in handle.readlines():
        matches = re.search(regex,line)
        if matches is not None:
            print(matches.group('vlan'))
            print(matches.group('mac_addr'))
            print(matches.group('type'))
            print(matches.group('port'))

