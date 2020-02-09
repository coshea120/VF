#!/usr/bin/env python

import netdev
import asyncio
from yaml import safe_load


#####################################################################################################################
#
#   Name - create_mac_address_dictionary
#
#   Description - This function runs 'show mac address-table' on the ssh session represented by 'connection',
#   and creates a dictionary of that data with the mac address as the key of type string, and the remaining values
#   stored as a tuple
#
#
#   Parameters
#       - connection - The active netmiko client session with the target switch
#
#   Return - Dictionary representing the output of 'show mac address-table' on the target switch
#
#####################################################################################################################
async def create_mac_address_dictionary(connection, mac):
    result = await connection.send_command('show mac address-table | incl ' + mac)
    if result != '':
        vlan, mac, porttype, port = result.split()
        return {mac: {'vlan': vlan, 'type': porttype, 'port': port}}
    else:
        return None


#####################################################################################################################
#
#   Name - get_switchport_operational_mode
#
#   Description - This function runs 'show interface [interface] switchport' on the active ssh session represented by
#   'connection'.  The function then searches for the line that begins with 'Operational Mode.'  The value of that
#   field is returned as a string.
#
#
#   Parameters
#       - connection - The active netmiko client session with the target switch
#       - portID - String representing the switchport interface ID e.g. Gi1/0
#
#   Return - String representing operational mode of the switchport
#
#####################################################################################################################
async def get_switchport_operational_mode(connection, portID: str):
    result = await connection.send_command('show interface ' + portID + ' switchport | incl Operational Mode')

    if result != '':
        return result.split(":")[1].lstrip()
    else:
        return None


async def find_mac_address_on_switch(address: str, username: str, password: str, platform: str, maclist):
    async with netdev.create(username=username, password=password, device_type=platform, host=address) as connection:
        print(f'Connected to {connection.base_prompt} successfully.')

        for mac in maclist:

            mac_str = mac['MAC']
            mac_dict = await create_mac_address_dictionary(connection, mac_str)

            if mac_dict is None:
                print(f"{mac_str} not found on {address}.")
                continue

            if mac_str in mac_dict.keys():
                print(f"{mac_str} found on {mac_dict[mac_str]['port']}.  Checking operational mode...")
                result = await get_switchport_operational_mode(connection, mac_dict[mac_str]['port'])

                if result.lower() == 'static access':
                    print(f"MAC address {mac_str} is located on {address} on interface {mac_dict[mac_str]['port']}")
                else:
                    print(f"{mac_dict[mac_str]['port']} on {address} is not operating as an access port.  Ignoring...")


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
