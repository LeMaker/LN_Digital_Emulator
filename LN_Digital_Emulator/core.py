#!/usr/bin/env python3
import sys
from time import sleep
from multiprocessing import Process, Queue
import LNcommon.interrupts
import LNcommon.core
import LNcommon.mcp23s17
import LNdigitalIO
from .gui import run_emulator

# from LNdigitalIO import OUTPUT_PORT, INPUT_PORT
OUTPUT_PORT = LNcommon.mcp23s17.GPIOA
INPUT_PORT = LNcommon.mcp23s17.GPIOB


_LNdigitalsDict = dict()


class EmulatorAddressError(Exception):
    pass


class LNdigitalEmulator(object):
    def read_bit(self, bit_num, address, hardware_addr=0):
        # This is  a function that belongs to LNcommon
        if address is INPUT_PORT:
            self.proc_comms_q_to_em.put(('get_in', bit_num, hardware_addr))
            return self.proc_comms_q_from_em.get(block=True)
        elif address is OUTPUT_PORT:
            self.proc_comms_q_to_em.put(('get_out', bit_num, hardware_addr))
            return self.proc_comms_q_from_em.get(block=True)
        else:
            raise EmulatorAddressError(
                "Reading to 0x%X is not supported in the "
                "LN Digital emulator" % address)

    def write_bit(self, value, bit_num, address, hardware_addr=0):
        """This is a function that belongs to LNcommon"""
        if address is OUTPUT_PORT:
            self.proc_comms_q_to_em.put(
                ('set_out', bit_num, True if value else False, hardware_addr))
        else:
            raise EmulatorAddressError(
                "Writing to 0x%X is not supported in the LN Digital "
                "emulator" % address)

    def read(self, address, hardware_addr=0):
        if address is INPUT_PORT or address is OUTPUT_PORT:
            value = 0x00
            for i in range(8):
                value |= self.read_bit(i, address, hardware_addr) << i

            return value

        else:
            raise EmulatorAddressError(
                "Reading from 0x%X is not supported in the LN Digital "
                "emulator" % address)

    def write(self, data, address, hardware_addr=0):
        if address is OUTPUT_PORT:
            for i in range(8):
                value = (data >> i) & 1
                self.write_bit(value, i, address, hardware_addr)

        else:
            raise EmulatorAddressError(
                "Writing to 0x%X is not supported in the LN Digital "
                "emulator" % address)

    def spisend(self, bytes_to_send):
        raise FunctionNotImplemented("spisend")

"""
# TODO have not yet implemented interupt functions in emulator
def wait_for_input(input_func_map=None, loop=False, timeout=None):
    raise FunctionNotImplemented("wait_for_input")
"""


class LNdigitals(LNdigitalEmulator, LNdigitalIO.LNdigitals):
    def __init__(self,
                 hardware_addr=0,
                 bus=LNdigitalIO.DEFAULT_SPI_BUS,
                 chip_select=LNdigitalIO.DEFAULT_SPI_CHIP_SELECT,
                 init_board=True):
        self.hardware_addr = hardware_addr
        try:
            # check if we can access a real LN digital
            LNdigitalIO.LNdigitals(
                hardware_addr, bus, chip_select, init_board)
            use_LNd = True
            # create this false LN Digital
            super(LNdigitals, self).__init__(hardware_addr,
                                                bus,
                                                chip_select,
                                                init_board=False)
        except LNcommon.spi.SPIInitError as e:
            print("Error initialising LN Digital: ", e)
            print("Running without hardware LN Digital.")
            use_LNd = False
        except LNdigitalIO.NoLNdigitalDetectedError:
            print("No LN Digital detected, running without "
                  "LN Digital.")
            use_LNd = False


        self.proc_comms_q_to_em = Queue()
        self.proc_comms_q_from_em = Queue()

        # start the gui in another process
        self.emulator = Process(target=run_emulator,
                                args=(sys.argv, use_LNd, init_board, self))

        global _LNdigitalsDict
        _LNdigitalsDict[self.hardware_addr] = self

        self.emulator.start()


class InputEventListener(object):
    """PicklingError: Can't pickle <class 'method'>: attribute lookup
    builtins.method failed
    """
    def __init__(self):
        raise NotImplementedError(
            "Interrupts are not implemented in the emulator.")
    # def register(self, pin_num, direction, callback):
    #     global proc_comms_q_to_em
    #     proc_comms_q_to_em.put(
    #         ('register_interrupt', pin_num, direction, callback))

    # def activate(self):
    #     global proc_comms_q_to_em
    #     proc_comms_q_to_em.put(('activate_interrupt',))

    # def deactivate(self):
    #     global proc_comms_q_to_em
    #     proc_comms_q_to_em.put(('deactivate_interrupt',))


def init():
    pass


def deinit():
    pass


def digital_read(pin_num, hardware_addr=0):
    return _LNdigitalsDict[hardware_addr].read_bit(pin_num,
                                                   INPUT_PORT,
                                                   hardware_addr) ^ 1


def digital_write(pin_num, value, hardware_addr=0):
    _LNdigitalsDict[hardware_addr].write_bit(value,
                                             pin_num,
                                             OUTPUT_PORT,
                                             hardware_addr)


def digital_read_pullup(pin_num, hardware_addr=0):
    return _LNdigitalsDict[hardware_addr].read_bit(pin_num,
                                                   INPUT_PULLUP,
                                                   hardware_addr)


def digital_write_pullup(pin_num, value, hardware_addr=0):
    _LNdigitalsDict[hardware_addr].write_bit(value,
                                             pin_num,
                                             INPUT_PULLUP,
                                             hardware_addr)
