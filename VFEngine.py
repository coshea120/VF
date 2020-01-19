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

# !/usr/bin/end python

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException
from paramiko.ssh_exception import SSHException
from netmiko.ssh_exception import AuthenticationException
from yaml import safe_load
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError
import re


#####################################################################################################################
#
#   Name - render_j2_template
#
#   Description - This function opens a jinja2 template from a file and returns the rendered command from the template
#   and additional parameters
#
#   Parameters
#       - filename - The path to the jinja2 template file.
#       - *args - argument list (built in syntax for command-line argument lists)
#       - **kwargs - argument dictionary (built in syntax for command-line argument dictionaries)
#
#   Return - Returns the rendered template as a string
#####################################################################################################################


def render_j2_template(filename, *args, **kwargs):
    try:
        j2_environment = Environment(
            loader=FileSystemLoader("."),
            trim_blocks=True,
            autoescape=True
        )

        template = j2_environment.get_template(filename)
        return template.render(*args, **kwargs)
    except TemplateNotFound as file_not_found:
        print(f"Unable to find template {filename}.\n-----\n{file_not_found.message}")
        return None
    except TemplateSyntaxError as syntax_error:
        print(f"Unable to compile template due to syntax error.\n------\n{syntax_error.message()}")
        return None


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
#       - j2_config - The rendered jinja2 template that will run in CLI
#
#   Return - Dictionary representing the output of 'show mac address-table' on the target switch
#
#####################################################################################################################

def create_mac_address_dictionary(connection, j2_config):
    regex = r'(?P<vlan>\d{1,4})\s+(?P<macaddr>\w{4}.\w{4}.\w{4})\s+(?P<type>(\w+))\s+(?P<port>(\S+))'

    mac_dictionary = {}

    result = connection.send_config_set(j2_config.split("\n"))

    for line in result.split('\n'):

        matches = re.search(regex, line)
        if matches is not None:
            mac_dictionary[matches.group('macaddr')] = \
                {
                    'vlan': matches.group('vlan'),
                    'type': matches.group('type'),
                    'port': matches.group('port')
                }

    return mac_dictionary


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
#       - j2_config - The rendered jinja2 template that will run in CLI
#
#   Return - String representing operational mode of the switchport
#
#####################################################################################################################
def get_switchport_operational_mode(connection, j2_config):
    result = connection.send_config_set(j2_config.split("\n"))

    for result_line in result.split("\n"):
        if 'Operational Mode:' in result_line:
            return result_line.split(":")[1].lstrip()


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
    with open("hosts.yml", "r") as hosts_handle:
        hosts_root = safe_load(hosts_handle)

    with open("end_devices.yml", "r") as device_handle:
        devices = safe_load(device_handle)

    # platform_map = {"ios": "cisco_ios", "iosxr": "cisco_xr"}

    shmactbl_config = render_j2_template("showmacaddrtable.j2")

    for device in devices['end_devices']:

        print(f"Searching for {device['MAC']}...")
        for host in hosts_root["host_list"]:
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
                print(f"Logged into {connection.find_prompt()} successfully.")

                mac_dict = create_mac_address_dictionary(connection, shmactbl_config)

                mac = device['MAC']

                if mac in mac_dict.keys():
                    print(f"{mac} found on {mac_dict[mac]['port']}.  Checking operational mode...")
                    shswport_config = render_j2_template("showintswitchport.j2", int=mac_dict[mac]['port'])
                    result = get_switchport_operational_mode(connection, shswport_config).lower()

                    if result == 'static access':
                        print(f"MAC address {mac} is located on {address} on interface {mac_dict[mac]['port']}")
                        break
                    else:
                        print(f"Port is not operating as an access port.  Ignoring...")


##############################################  ENTRY POINT  #########################################################

if __name__ == "__main__":
    main()
