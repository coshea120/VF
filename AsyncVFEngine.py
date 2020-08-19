#!/usr/bin/env python

import netdev
import asyncio
import getpass
from yaml import safe_load

#####################################################################################################################
#
#   Name - create_mac_address_dictionary
#
#   Description - This function runs 'show mac address-table' on the ssh session represented by 'connection',
#   and creates a dictionary of that data with the mac address as the key of type string, and the remaining values
#   stored as a tuple
#
#   Parameters
#       - connection - The active client session with the target switch
#
#   Return - Dictionary representing the output of 'show mac address-table | include <mac>' on the target switch, or 
#            None if MAC does  not appear in MAC address table
#
#####################################################################################################################
async def create_mac_address_dictionary(connection, mac):
    result = await connection.send_command('show mac address-table | incl ' + mac)
    
    if result != '':
        vlan, mac, porttype, port = result.split()
        return {mac: {'vlan': vlan, 'type': porttype, 'port': port}}
    
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
#       - connection - The active client session with the target switch
#       - portID - String representing the switchport interface ID e.g. Gi1/0
#
#   Return - String representing operational mode of the switchport, None if CLI command returns no output.
#
#####################################################################################################################
async def get_switchport_operational_mode(connection, portID: str):
    result = await connection.send_command('show interface ' + portID + ' switchport | incl Operational Mode')

    if result != '':
        return result.split(":")[1]
    
    return None

#####################################################################################################################
#
#   Name - find_mac_address_on_switch
#
#   Description - This function establishes an SSH connection with the switch running 'platform' at 'address' using  
#                 'username' and 'password' to authenticate.  The function then iterates over 'maclist', checking if
#                 an entry in 'maclist' shows in the switch's mac address table.  If so, check if it is a static 
#                 access port.  If so, we have found the port connected to the end device with the current mac address.  
#
#   Parameters
#       - address - Address of the switch to connect to
#       - username - username to use when authenticating with 'address'
#       - password - password to use with 'username'
#       - platform - the platform/OS the target switch is running (e.g. cisco IOS, IOSXR, JunOS, etc.)
#       - maclist - list of MAC addresses of end devices that we are looking for
#
#   Return - N/A
#
#####################################################################################################################


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

                if 'access' in result.lower():
                    print(f"MAC address {mac_str} is located on {address} on interface {mac_dict[mac_str]['port']}")
                else:
                    print(f"{mac_dict[mac_str]['port']} on {address} is not operating as an access port.  Ignoring...")


########################################################################################################################
#
#   Name - get_credentials
#
#   Description - Prompts the user for a username and password to be used when attempting to establish SSH connections
#   with the access switches.  Makes use of Python's built-in getpass module.                           
#
#   Parameters - None
#      
#   Return - Key-value pair where the username is the key, and the password is the value
#
#   Todo's - 
#
########################################################################################################################

def get_credentials():
    try:
        u = getpass.getuser()
        p = getpass.getpass(f"Enter password for {u}.")
        
    except:
        return None
    else:
        return {u:p}
  

########################################################################################################################
#
#   Name - main
#
#   Description - Script's entry point.  First, it opens a YAML file that represents the switches that will be searched.
#   Next, it opens another YAML file that represents the end devices that we are looking for.  After, it creates a 
#   collection of asynchronous tasks for each switch.  The purpose is to be able to search multiple switches in parallel 
#   instead sequentially to boost speed.  One task is created and executed for each switch that needs to be searched.
#
#   Parameters - None
#      
#   Return - N/A
#
#   Todo's - Tasks generate output, but nothing is done with it.  Can be used to return error messages, generate logs, 
#            etc.
#          - Right now, credentials to SSH into switches are stored in the YAML file.  First, this is insecure.  Second,
#            it is redundant since each entry in the YAML file has the creds repeated.  Prompt user to enter credentials
#            securely, and use those for all switches.
#
########################################################################################################################
                          
async def main():
    with open("switches.yml", "r") as switches_handle:
        switches_root = safe_load(switches_handle)

    with open("end_devices.yml", "r") as device_handle:
        devices = safe_load(device_handle)
                          
    (username, password), = get_credentials().items()
                          
    connection_list = [asyncio.create_task(find_mac_address_on_switch(address=switch['address'],
                                                                      platform=switch['platform'],
                                                                      username=username,
                                                                      password=password,
                                                                      maclist=devices['end_devices']))
                       for switch in switches_root['switch_list']]

    output = await asyncio.gather(*connection_list)
    # print([line for line in (''.join([str(elem) for elem in output])).split('\\n')])
    # print(output)
if __name__ == '__main__':
    asyncio.run(main())
