#!/usr/bin/env python

import netdev
import asyncio
from yaml import safe_load


async def find_mac_address_on_switch(address: str, username: str, password: str, platform: str, maclist):
    async with netdev.create(username=username, password=password, device_type=platform, host=address) as connection:
        print(f'Connected to {connection.base_prompt} successfully.')

        for mac in maclist:
            output = await connection.send_command('show mac address-table | incl ' + mac['MAC'])
            print(output)
        #output = [await connection.send_command(f'show mac address-table') for mac in maclist]


async def main():
    with open("switches.yml", "r") as switches_handle:
        switches_root = safe_load(switches_handle)

    with open("end_devices.yml", "r") as device_handle:
        devices = safe_load(device_handle)

    connection_list = [asyncio.create_task(find_mac_address_on_switch(address=switch['address'],
                                                                      platform=switch['platform'],
                                                                      username=switch['username'],
                                                                      password=switch['password'],
                                                                      maclist=devices['end_devices']))
                       for switch in switches_root['switch_list']]

    output = await asyncio.gather(*connection_list)
    # print([line for line in (''.join([str(elem) for elem in output])).split('\\n')])
    # print(output)
if __name__ == '__main__':
    asyncio.run(main())
