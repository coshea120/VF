#####################################################################################################################
#
#   Project VF
#
#   The purpose of this script is to determine if MAC addresses are somewhere on the network, and, if so, identifying
#   the switch and switchport associated with that MAC address.
#
#   Written By - Christian O'Shea
#   Version 0.1
#
#####################################################################################################################

# !/usr/bin/env python

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException, AuthenticationException
from paramiko.ssh_exception import SSHException
from yaml import safe_load


#####################################################################################################################
#
#   Name - create_mac_address_dictionary
#
# Description - This function runs 'show mac address-table' on the ssh session represented by 'connection',
# and creates a dictionary of that data with the mac address as the key of type string, and the remaining values
# stored as a tuple
#
#
#   Parameters
#       - connection - The active netmiko client session with the target switch
#
#   Return - Dictionary representing the output of 'show mac address-table' on the target switch
#
#####################################################################################################################

def create_mac_address_dictionary(connection, mac):

    result = connection.send_command('show mac address-table | incl ' + mac)
    if result != '':
        vlan, mac, porttype, port = result.split()
        return {mac: {'vlan': vlan, 'type': porttype, 'port': port}}


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
#
#   Return - String representing operational mode of the switchport
#
#####################################################################################################################
def get_switchport_operational_mode(connection, portID):
    result = connection.send_command('show interface ' + portID + ' switchport | incl Operational Mode')
    val = result.split(":")[1].lstrip()
    return result.split(":")[1].lstrip()


#####################################################################################################################
#
#   Name - main
#
#   Description - Script's entry point.  Steps are as follows:
#       - Open list of addresses of switches to check
#       - Begin to loop over the list
#       - Open the list of end devices (hostnames and mac addresses)
#       - SSH into the current switch
#       - Run show mac address-table on the current switch
#       - Parse table and attempt to match mac addresses in table with mac addresses from end devices list
#       - If there is a match, run 'show int switchport' on the port that matches the mac address
#       - Parse that output to check if the Operational Mode is 'static access' (ignore trunk ports)
#       - If so, return the address of the switch and the port ID as strings
#
#   Parameters
#       - None
#
#   Return:
#       - None
#
#
#####################################################################################################################


def main():
    with open("switches.yml", "r") as hosts_handle:
        hosts_root = safe_load(hosts_handle)

    with open("end_devices.yml", "r") as device_handle:
        devices = safe_load(device_handle)

    # platform_map = {"ios": "cisco_ios", "iosxr": "cisco_xr"}

    for device in devices['end_devices']:

        print(f"Searching for {device['MAC']}...")
        for host in hosts_root["switch_list"]:
            # platform = platform_map[host["platform"]]
            platform = host["platform"]
            address = host["address"]

            try:
                connection = ConnectHandler(
                    ip=address,
                    device_type=platform,
                    username="coshea",
                    password="cisco"
                )
            except AuthenticationException:
                print(f"SSH Authentication Failed on {address}.")
            except NetMikoTimeoutException:
                print(f"Attempt to connect to {address} has timed-out.")
            except SSHException:
                print(f"Check if SSH is enabled on {address}.")
            else:
                # Do a little sanity check to verify successful login.  If we can pull the prompt from the
                # device on the other side, the connection is good.
                print(f"Logged into {connection.find_prompt()} successfully.")

                mac = device['MAC']
                mac_dict = create_mac_address_dictionary(connection, mac)

                if mac in mac_dict.keys():
                    print(f"{mac} found on {mac_dict[mac]['port']}.  Checking operational mode...")

                    result = get_switchport_operational_mode(connection, mac_dict[mac]['port']).lower()

                    if result == 'static access':
                        print(f"MAC address {mac} is located on {address} on interface {mac_dict[mac]['port']}")
                        break
                    else:
                        print(f"Port is not operating as an access port.  Ignoring...")


##############################################  ENTRY POINT  #########################################################

if __name__ == "__main__":
    main()
