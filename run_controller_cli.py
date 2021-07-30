#!/usr/bin/env python3

import argparse
import asyncio
import logging
import os

from aioconsole import ainput

import joycontrol.debug as debug
from joycontrol import logging_default as log, utils
from joycontrol.command_line_interface import ControllerCLI
from joycontrol.controller import Controller
from joycontrol.controller_state import ControllerState, button_push, button_press, button_release
from joycontrol.memory import FlashMemory
from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server
from joycontrol.nfc_tag import NFCTag

import pygame

logger = logging.getLogger(__name__)

"""Emulates Switch controller. Opens joycontrol.command_line_interface to send button commands and more.

While running the cli, call "help" for an explanation of available commands.

Usage:
    run_controller_cli.py <controller> [--device_id | -d  <bluetooth_adapter_id>]
                                       [--spi_flash <spi_flash_memory_file>]
                                       [--reconnect_bt_addr | -r <console_bluetooth_address>]
                                       [--log | -l <communication_log_file>]
                                       [--nfc <nfc_data_file>]
    run_controller_cli.py -h | --help

Arguments:
    controller      Choose which controller to emulate. Either "JOYCON_R", "JOYCON_L" or "PRO_CONTROLLER"

Options:
    -d --device_id <bluetooth_adapter_id>   ID of the bluetooth adapter. Integer matching the digit in the hci* notation
                                            (e.g. hci0, hci1, ...) or Bluetooth mac address of the adapter in string
                                            notation (e.g. "FF:FF:FF:FF:FF:FF").
                                            Note: Selection of adapters may not work if the bluez "input" plugin is
                                            enabled.

    --spi_flash <spi_flash_memory_file>     Memory dump of a real Switch controller. Required for joystick emulation.
                                            Allows displaying of JoyCon colors.
                                            Memory dumps can be created using the dump_spi_flash.py script.

    -r --reconnect_bt_addr <console_bluetooth_address>  Previously connected Switch console Bluetooth address in string
                                                        notation (e.g. "FF:FF:FF:FF:FF:FF") for reconnection.
                                                        Does not require the "Change Grip/Order" menu to be opened,

    -l --log <communication_log_file>       Write hid communication (input reports and output reports) to a file.

    --nfc <nfc_data_file>                   Sets the nfc data of the controller to a given nfc dump upon initial
                                            connection.
"""


async def gamepad_proxy(controller_state: ControllerState):
    pygame.init()
    clock = pygame.time.Clock()

    joysticks = []
    for i in range(0, pygame.joystick.get_count()):
        joysticks.append(pygame.joystick.Joystick(i))
        joysticks[-1].init()
        print ("Initialized joystick")

    gamepad_loop = True
    while gamepad_loop:
        # clock.tick(60)

        for event in pygame.event.get():

            # Sticks
            if event.type == pygame.JOYAXISMOTION:
                if event.axis == 0:
                    print("L Horizontal", event.value)
                    controller_state.l_stick_state.set_h(event.value)
                if event.axis == 1:
                    print("L Vertical", event.value)
                    controller_state.l_stick_state.set_v(event.value)
                if event.axis == 2:
                    print("R Horizontal", event.value)
                    controller_state.r_stick_state.set_h(event.value)
                if event.axis == 3:
                    print("R Vertical", event.value)
                    controller_state.r_stick_state.set_v(event.value)

            # Buttons
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    print("Y Down")
                    await button_press(controller_state, "y")
                if event.button == 1:
                    print("B Down")
                    await button_press(controller_state, "b")
                if event.button == 2:
                    print("A Down")
                    await button_press(controller_state, "a")
                if event.button == 3:
                    print("X Down")
                    await button_press(controller_state, "x")
                if event.button == 4:
                    print("LB Down")
                    await button_press(controller_state, "l")
                if event.button == 5:
                    print("RB Down")
                    await button_press(controller_state, "r")
                if event.button == 6:
                    print("LT Down")
                    await button_press(controller_state, "zl")
                if event.button == 7:
                    print("RT Down")
                    await button_press(controller_state, "zr")
                if event.button == 8:
                    print("- Down")
                    await button_press(controller_state, "minus")
                if event.button == 9:
                    print("+ Down")
                    await button_press(controller_state, "plus")
                if event.button == 10:
                    print("L Stick Down")
                    await button_press(controller_state, "l_stick")
                if event.button == 11:
                    print("R Stick Down")
                    await button_press(controller_state, "r_stick")
                if event.button == 12:
                    print("Home Down")
                    await button_press(controller_state, "home")
                if event.button == 13:
                    print("Capture Down")
                    await button_press(controller_state, "capture")
                
            if event.type == pygame.JOYBUTTONUP:
                if event.button == 0:
                    print("Y Down")
                    await button_release(controller_state, "y")
                if event.button == 1:
                    print("B Down")
                    await button_release(controller_state, "b")
                if event.button == 2:
                    print("A Down")
                    await button_release(controller_state, "a")
                if event.button == 3:
                    print("X Down")
                    await button_release(controller_state, "x")
                if event.button == 4:
                    print("LB Down")
                    await button_release(controller_state, "l")
                if event.button == 5:
                    print("RB Down")
                    await button_release(controller_state, "r")
                if event.button == 6:
                    print("LT Down")
                    await button_release(controller_state, "zl")
                if event.button == 7:
                    print("RT Down")
                    await button_release(controller_state, "zr")
                if event.button == 8:
                    print("- Down")
                    await button_release(controller_state, "minus")
                if event.button == 9:
                    print("+ Down")
                    await button_release(controller_state, "plus")
                if event.button == 10:
                    print("L Stick Down")
                    await button_release(controller_state, "l_stick")
                if event.button == 11:
                    print("R Stick Down")
                    await button_release(controller_state, "r_stick")
                if event.button == 12:
                    print("Home Down")
                    await button_release(controller_state, "home")
                if event.button == 13:
                    print("Capture Down")
                    await button_release(controller_state, "capture")

def _register_commands_with_controller_state(controller_state, cli):
    """
    Commands registered here can use the given controller state.
    The doc string of commands will be printed by the CLI when calling "help"
    :param cli:
    :param controller_state:
    """
    async def start_gamepad():
        """
        start_gamepad - Starts using gamepad as a proxy for switch controller
        """
        await gamepad_proxy(controller_state)

    cli.add_command(start_gamepad.__name__, start_gamepad)

async def _main(args):
    # Get controller name to emulate from arguments
    controller = Controller.from_arg(args.controller)

    # parse the spi flash
    if args.spi_flash:
        with open(args.spi_flash, 'rb') as spi_flash_file:
            spi_flash = FlashMemory(spi_flash_file.read())
    else:
        # Create memory containing default controller stick calibration
        spi_flash = FlashMemory()


    with utils.get_output(path=args.log, default=None) as capture_file:
        # prepare the the emulated controller
        factory = controller_protocol_factory(controller, spi_flash=spi_flash, reconnect = args.reconnect_bt_addr)
        ctl_psm, itr_psm = 17, 19
        transport, protocol = await create_hid_server(factory, reconnect_bt_addr=args.reconnect_bt_addr,
                                                      ctl_psm=ctl_psm,
                                                      itr_psm=itr_psm, capture_file=capture_file,
                                                      device_id=args.device_id,
                                                      interactive=True)

        controller_state = protocol.get_controller_state()

        # Create command line interface and add some extra commands
        cli = ControllerCLI(controller_state)
        _register_commands_with_controller_state(controller_state, cli)
        cli.add_command('amiibo', ControllerCLI.deprecated('Command was removed - use "nfc" instead!'))
        cli.add_command(debug.debug.__name__, debug.debug)

        # set default nfc content supplied by argument
        if args.nfc is not None:
            await cli.commands['nfc'](args.nfc)

        # run the cli
        try:
            await cli.run()
        finally:
            logger.info('Stopping communication...')
            await transport.close()


if __name__ == '__main__':
    # check if root
    if not os.geteuid() == 0:
        raise PermissionError('Script must be run as root!')

    # setup logging
    #log.configure(console_level=logging.ERROR)
    log.configure()

    parser = argparse.ArgumentParser()
    parser.add_argument('controller', help='JOYCON_R, JOYCON_L or PRO_CONTROLLER')
    parser.add_argument('-l', '--log', help="BT-communication logfile output")
    parser.add_argument('-d', '--device_id', help='not fully working yet, the BT-adapter to use')
    parser.add_argument('--spi_flash', help="controller SPI-memory dump to use")
    parser.add_argument('-r', '--reconnect_bt_addr', type=str, default=None,
                        help='The Switch console Bluetooth address (or "auto" for automatic detection), for reconnecting as an already paired controller.')
    parser.add_argument('--nfc', type=str, default=None, help="amiibo dump placed on the controller. Äquivalent to the nfc command.")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        _main(args)
    )
