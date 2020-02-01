#!/usr/bin/env python

import netdev
import asyncio
from yaml import safe_load


async def connect_ssh(address: str, username: str, password: str, platform: str):
    async with netdev.create(username=username, password=password, device_type=platform, host=address) as connection:
        output = await connection.send_command('show version')


async def main():
    with open("switches.yml", "r") as switches_handle:
        switches_root = safe_load(switches_handle)

    connection_list = [asyncio.create_task(connect_ssh(address=switch['address'],
                                                       platform=switch['platform'],
                                                       username=switch['username'],
                                                       password=switch['password']))
                       for switch in switches_root['switch_list']]

    await asyncio.gather(*connection_list)


if __name__ == '__main__':
    asyncio.run(main())
