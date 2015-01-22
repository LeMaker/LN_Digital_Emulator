from PySide import QtGui, QtCore
from PySide.QtCore import (Qt, QThread, QObject, Slot, Signal)
from PySide.QtGui import (
    QMainWindow, QPushButton, QApplication, QPainter, QFont
)
from multiprocessing import Queue
from threading import Barrier

import LNcommon
import LNdigitalIO
from .LN_Digital_Emulator_ui import Ui_LN_DigitalEmulatorWindow


# circle drawing
PIN_COLOUR = QtGui.QColor(0, 255, 255)
SWITCH_COLOUR = QtCore.Qt.yellow
CIRCLE_R = 9
# Following are for LN Digital 1 and 2
INPUT_PIN_CIRCLE_COORD = (
    # LN Digital
    ((5, 179), (17, 179), (29, 179), (41, 179), (53, 179), (65, 179),
     (77, 179),(89, 179)),
    # LN Digital 2
    ((171, 4), (159, 4), (147, 4), (135, 4), (123, 4), (111, 4),
     (99, 4), (87, 4)))
# output coords are backwards (output port indexed (7 -> 0)
OUTPUT_PIN_CIRCLE_COORD = (
    # LN Digital
    ((167, 12), (155, 12), (144, 12), (132, 12), (120, 12), (108, 12),
     (97, 12), (85, 12)),
    # LN Digital 2
    ((272, 4), (260, 4), (248, 4), (236, 4), (224, 4), (212, 4),
     (200, 4), (188, 4)))
SWITCH_CIRCLE_COORD = (
    # LN Digital
    ((13, 155), (43, 155), (69, 155), (94, 155)),
    # LN Digital 2
    ((160, 30), (134, 30), (108, 30), (82, 30)))
RELAY_CIRCLE_COORD = (
    # LN Digital
    ((275, 55), (275, 67), (275, 79), (275, 94), (275, 108),
     (275, 120)),
    # LN Digital 2
    ((286, 88), (286, 99), (286, 111), (286, 125), (286, 137), (286, 149)))
# led locations
LED_LABEL_X = ((175, 163, 152, 140, 128, 116, 105, 93),
               (280, 268, 257, 244, 232, 219, 207, 195))

# boundaries for input presses (index 0: LN Digital 1, 1: LN Digital 2)
SWITCH_BOUNDARY_Y_TOP = (148, 29)
SWITCH_BOUNDARY_Y_BOTTOM = (161, 44)
SWITCH_BOUNDARY_X_LEFT = ((10, 41, 66, 91), (157, 132, 105, 79))
SWITCH_BOUNDARY_X_RIGHT = ((30, 61, 86, 111), (177, 151, 124, 97))
PIN_BOUNDARY_Y_TOP = (180, 4)
PIN_BOUNDARY_Y_BOTTOM = (190, 14)
PIN_BOUNDARY_X_LEFT = ((5,  19, 31, 44, 53, 68, 79, 91, 104),
                       (171, 159, 147, 135, 123, 111, 99, 87))
PIN_BOUNDARY_X_RIGHT = ((15, 27, 38, 51, 66, 74, 87, 99, 112),
                        (180, 168, 156, 144, 132, 120, 108, 96))

NUM_LN_DIGITALS = 4


class CircleDrawingWidget(QtGui.QWidget):
    def __init__(self, parent=None, emu_window=None):
        super(CircleDrawingWidget, self).__init__(parent)
        # mirror actual state
        self.emu_window = emu_window

        # 'hold' for every input
        self.input_hold = [False for i in self.emu_window.input_state]

    @property
    def switch_circles_state(self):
        return self.emu_window.input_state[:4]

    @property
    def relay_circles_state(self):
        """returns six booleans for the relay pins"""
        # relays are attached to pins 0 and 1
        if self.emu_window.output_state[0]:
            state0 = [False, True, True]
        else:
            state0 = [True, True, False]

        if self.emu_window.output_state[1]:
            state1 = [False, True, True]
        else:
            state1 = [True, True, False]

        return state1 + state0

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setBrush(QtGui.QBrush(PIN_COLOUR))
        painter.setPen(QtGui.QPen(PIN_COLOUR))
        # draw input circles
        for i, state in enumerate(self.emu_window.input_state):
            if state:
                painter.drawEllipse(
                    INPUT_PIN_CIRCLE_COORD[self.emu_window.LNdig_ver-1][i][0],
                    INPUT_PIN_CIRCLE_COORD[self.emu_window.LNdig_ver-1][i][1],
                    CIRCLE_R, CIRCLE_R)

        # draw output circles
        for i, state in enumerate(self.emu_window.output_state):
            if state:
                painter.drawEllipse(
                    OUTPUT_PIN_CIRCLE_COORD[self.emu_window.LNdig_ver-1][i][0],
                    OUTPUT_PIN_CIRCLE_COORD[self.emu_window.LNdig_ver-1][i][1],
                    CIRCLE_R, CIRCLE_R)

        # draw relay circles
        for i, state in enumerate(self.relay_circles_state):
            if state:
                painter.drawEllipse(
                    RELAY_CIRCLE_COORD[self.emu_window.LNdig_ver-1][i][0],
                    RELAY_CIRCLE_COORD[self.emu_window.LNdig_ver-1][i][1],
                    CIRCLE_R,
                    CIRCLE_R)

        # draw switch circles
        painter.setBrush(QtGui.QBrush(SWITCH_COLOUR))
        painter.setPen(QtGui.QPen(SWITCH_COLOUR))
        for i, state in enumerate(self.switch_circles_state):
            if state:
                painter.drawEllipse(
                    SWITCH_CIRCLE_COORD[self.emu_window.LNdig_ver-1][i][0],
                    SWITCH_CIRCLE_COORD[self.emu_window.LNdig_ver-1][i][1],
                    CIRCLE_R, CIRCLE_R)
        painter.end()

    def mousePressEvent(self, event):
        self._pressed_pin, self._pressed_switch = switch = \
            get_input_index_from_mouse(event.pos(), self.emu_window.LNdig_ver)
        if self._pressed_pin is None:
            event.ignore()
            return

        # if we are over a switch, turn it on, else toggle
        if self._pressed_switch:
            self.emu_window.input_state[self._pressed_pin] = True
        else:
            self.emu_window.input_state[self._pressed_pin] = \
                not self.emu_window.input_state[self._pressed_pin]
            # hold it if we're setting it the pin high
            self.input_hold[self._pressed_pin] = \
                self.emu_window.input_state[self._pressed_pin]

        self.emu_window.update_emulator()

    def mouseReleaseEvent(self, event):
        if self._pressed_pin is None:
            event.ignore()
            return

        # if we're releasing a switch, turn off the pin (if it's not held)
        if self._pressed_switch:
            if not self.input_hold[self._pressed_pin]:
                self.emu_window.input_state[self._pressed_pin] = False
                self._pressed_pin = None
                self._pressed_switch = False
                self.emu_window.update_emulator()


class LNdigitalEmulatorWindow(QMainWindow, Ui_LN_DigitalEmulatorWindow):
    def __init__(self, parent=None):
        super(LNdigitalEmulatorWindow, self).__init__(parent)
        self.setupUi(self)

        self.LNdigital = None
        self.current_LN = 0
        self.LNdig_ver = 1

        # self._input_states = [[False for state in range(8)]
        #                       for p in range(NUM_LN_DIGITALS)]
        # self._previous_input_states = [list(p) for p in self._input_states]
        # self._output_states = [[False for state in range(8)]
        #                        for p in range(NUM_LN_DIGITALS)]
        self.input_state = [False for state in range(8)]
        self.previous_input_state = list(self.input_state)
        self.output_state = [False for state in range(8)]

        # add the circle drawing widget
        self.circleDrawingWidget = \
            CircleDrawingWidget(self.centralwidget, self)
        self.circleDrawingWidget.setGeometry(QtCore.QRect(10, 10, 301, 191))
        self.circleDrawingWidget.setObjectName("circleDrawingWidget")

        self.output_buttons = [
            self.output0Button,
            self.output1Button,
            self.output2Button,
            self.output3Button,
            self.output4Button,
            self.output5Button,
            self.output6Button,
            self.output7Button]
        self.led_labels = [
            self.led0Label,
            self.led1Label,
            self.led2Label,
            self.led3Label,
            self.led4Label,
            self.led5Label,
            self.led6Label,
            self.led7Label]

        # hide the leds
        for led in self.led_labels:
            led.setVisible(False)

	# show LN Digital Image and Leds
        self.LN_DigitalImageLabel.setVisible(True)
        self.set_led_label_locations()

        self.address0ActionToggled()

        # set up signal/slots
        self.outputControlAction.toggled.connect(self.enable_output_control)
        self.inputPullupsAction.toggled.connect(self.set_input_pullups)
        self.board_actions = (
            self.board0Action,
            self.board1Action,
            self.board2Action,
            self.board3Action,
        )

        for button in self.output_buttons:
            button.toggled.connect(self.output_overide)

        self.allOnButton.clicked.connect(self.all_outputs_on)
        self.allOffButton.clicked.connect(self.all_outputs_off)
        self.flipButton.clicked.connect(self.all_outputs_toggle)

        self.address0Action.toggled.connect(self.address0ActionToggled)
        self.address1Action.toggled.connect(self.address1ActionToggled)
        self.address2Action.toggled.connect(self.address2ActionToggled)
        self.address3Action.toggled.connect(self.address3ActionToggled)

        self.output_override_enabled = False


    def address0ActionToggled(self):
        self._addressActionToggled(0)

    def address1ActionToggled(self):
        self._addressActionToggled(1)

    def address2ActionToggled(self):
        self._addressActionToggled(2)

    def address3ActionToggled(self):
        self._addressActionToggled(3)

    def _addressActionToggled(self, index):
        self.current_LN = index
        if self.LNdigital:
            self.LNdigital.hardware_addr = index
        # block the signals
        self.address0Action.blockSignals(True)
        self.address1Action.blockSignals(True)
        self.address2Action.blockSignals(True)
        self.address3Action.blockSignals(True)
        # set correct check pattern
        self.address0Action.setChecked(index == 0)
        self.address1Action.setChecked(index == 1)
        self.address2Action.setChecked(index == 2)
        self.address3Action.setChecked(index == 3)
        # unblock the signals
        self.address0Action.blockSignals(False)
        self.address1Action.blockSignals(False)
        self.address2Action.blockSignals(False)
        self.address3Action.blockSignals(False)
        self.update_emulator()

    def set_led_label_locations(self):
        """Sets the location of the LED on image labels."""
        led_labels = (self.led0Label, self.led1Label, self.led2Label,
                      self.led3Label, self.led4Label, self.led5Label,
                      self.led6Label, self.led7Label)
        for i, led_label in enumerate(led_labels):
            # print("Moving led_label[{}] to {}".format(i, LED_LABEL_X[self.LNdig_ver-1][i]))
            led_label.move(LED_LABEL_X[self.LNdig_ver-1][i], 40)
            led_label.raise_()

    def enable_output_control(self, enable):
        if enable:
            self._saved_output_state = list(self.output_state)
            self.update_all_output_buttons()
        else:
            self.output_state = self._saved_output_state
            self.uncheck_all_output_buttons()
            self.update_emulator()

        self.output_override_enabled = enable
        self.outputControlBox.setEnabled(enable)

    def set_input_pullups(self, enable):
        if self.LNdigital is not None:
            self.LNdigital.gppub.value = 0xff if enable else 0x00
            if not enable:
                for i, s in enumerate(self.input_state):
                    self.set_input(i, False)
                self.update_emulator()

    def output_overide(self, enable):
        """sets the output to mirror the override buttons"""
        # find out output override buttons state
        # then write them to the output
        # don't use set_output since that is locked when override mode is on
        for i, button in enumerate(self.output_buttons):
            self.output_state[i] = button.isChecked()
        self.update_emulator()

    def set_output(self, index, enable, hardware_addr=None):
        """Sets the specified output on or off"""
        if not self.output_override_enabled:
            self.output_state[index] = enable

    def set_input(self, index, enable, hardware_addr=None):
        # don't set the input if it is being held
        if not self.circleDrawingWidget.input_hold[index]:
            self.input_state[index] = enable

    def get_output_as_value(self):
        output_value = 0
        for bit_index, state in enumerate(self.output_state):
            this_bit = 1 if state else 0
            output_value |= (this_bit << bit_index)
        return output_value

    def update_LN(self):
        self.LNdigital.output_port.value = self.get_output_as_value()

    interrupt_flagger = Signal(int)

    def update_emulator(self):
        self.update_circles()
        if self.input_has_changed():
            pin, direction = self.get_changed_pin_and_direction()
            self.interrupt_flagger.emit(
                small_nums_to_single_val(pin, direction))
        self.previous_input_state = list(self.input_state)
        self.update_led_images()

        if self.LNdigital is not None:
            self.update_LN()

    def input_has_changed(self):
        return self.input_state != self.previous_input_state

    def get_changed_pin_and_direction(self):
        for i, x in enumerate(
                zip(self.input_state, self.previous_input_state)):
            if x[0] != x[1]:
                pin = i
                direction = LNdigitalIO.IODIR_ON \
                    if x[0] else LNdigitalIO.IODIR_OFF
                return pin, direction

    def update_circles(self):
        self.circleDrawingWidget.input_pin_circles_state = self.input_state
        self.circleDrawingWidget.output_pin_circles_state = self.output_state
        self.circleDrawingWidget.repaint()

    def update_led_images(self):
        for index, state in enumerate(self.output_state):
            self.led_labels[index].setVisible(state)

    def all_outputs_on(self):
        self.output_state = [True for s in range(8)]
        self.update_all_output_buttons()
        self.update_emulator()

    def all_outputs_off(self):
        self.output_state = [False for s in range(8)]
        self.update_all_output_buttons()
        self.update_emulator()

    def all_outputs_toggle(self):
        self.output_state = [not s for s in self.output_state]
        self.update_all_output_buttons()
        self.update_emulator()

    def uncheck_all_output_buttons(self):
        for button in self.output_buttons:
            button.toggled.disconnect(self.output_overide)
            button.setChecked(False)
            button.toggled.connect(self.output_overide)

    def update_all_output_buttons(self):
        for i, button in enumerate(self.output_buttons):
            button.toggled.disconnect(self.output_overide)
            button.setChecked(self.output_state[i])
            button.toggled.connect(self.output_overide)

    @Slot(int)
    def set_input_enable(self, value):
        pin_num, hardware_addr = single_val_to_small_nums(value)
        self.set_input(pin_num, True, hardware_addr)
        self.update_emulator()

    @Slot(int)
    def set_input_disable(self, value):
        pin_num, hardware_addr = single_val_to_small_nums(value)
        self.set_input(pin_num, False, hardware_addr)
        self.update_emulator()

    @Slot(int)
    def set_output_enable(self, value):
        pin_num, hardware_addr = single_val_to_small_nums(value)
        self.set_output(pin_num, True, hardware_addr)
        self.update_emulator()

    @Slot(int)
    def set_output_disable(self, value):
        pin_num, hardware_addr = single_val_to_small_nums(value)
        self.set_output(pin_num, False, hardware_addr)
        self.update_emulator()

    send_input = Signal(int)

    @Slot(int)
    def get_input(self, value):
        pin_num, hardware_addr = single_val_to_small_nums(value)
        input_on = 1 if self.input_state[pin_num] else 0
        send_val = small_nums_to_single_val(input_on, hardware_addr)
        self.send_input.emit(send_val)

    send_output = Signal(int)

    @Slot(int)
    def get_output(self, value):
        pin_num, hardware_addr = single_val_to_small_nums(value)
        pin_on = 1 if self.output_state[pin_num] else 0
        send_val = small_nums_to_single_val(pin_on, hardware_addr)
        self.send_output.emit(send_val)


class QueueWatcher(QObject):
    """Handles the queue which talks to the main process"""

    set_out_enable = Signal(int)
    set_out_disable = Signal(int)
    get_in = Signal(int)
    get_out = Signal(int)

    def __init__(self, app, emu_window, q_to_em, q_from_em):
        super().__init__()
        self.main_app = app
        self.emu_window = emu_window
        self.q_to_em = q_to_em
        self.q_from_em = q_from_em
        self.perform = {
            'set_out': self.set_out_pin,
            'get_in': self.get_in_pin,
            'get_out': self.get_out_pin,
            'register_interrupt': self.register_interrupt,
            'activate_interrupt': self.activate_interrupt,
            'deactivate_interrupt': self.deactivate_interrupt,
            'quit': self.quit_main_app,
        }
        self.pin_function_maps = list()
        self.interrupts_activated = False

    def check_queue(self):
        while True:
            action = self.q_to_em.get(block=True)
            task = action[0]
            self.perform[task](action[1:])

    def set_out_pin(self, data):
        pin, enable, hardware_addr = data
        if enable:
            self.set_out_enable.emit(
                small_nums_to_single_val(pin, hardware_addr))
        else:
            self.set_out_disable.emit(
                small_nums_to_single_val(pin, hardware_addr))

    def get_in_pin(self, data):
        pin, hardware_addr = data[0], data[1]
        self.get_in.emit(small_nums_to_single_val(pin, hardware_addr))
        # now we have to rely on the emulator getting back to us

    @Slot(int)
    def send_get_in_pin_result(self, value):
        value, hardware_addr = single_val_to_small_nums(value)
        self.q_from_em.put(value)

    def get_out_pin(self, data):
        pin, hardware_addr = data[0], data[1]
        self.get_out.emit(small_nums_to_single_val(pin, hardware_addr))

    @Slot(int)
    def send_get_out_pin_result(self, value):
        value, hardware_addr = single_val_to_small_nums(value)
        self.q_from_em.put(value)

    def register_interrupt(self, data):
        pin_num, direction, callback = data
        self.pin_function_maps.append(LNcommon.interrupts.PinFunctionMap(
            pin_num, direction, callback))

    def activate_interrupt(self, data):
        self.interrupts_activated = True

    def deactivate_interrupt(self, data):
        self.interrupts_activated = False

    @Slot(int)
    def handle_interrupt(self, data):
        pin, direction = single_val_to_small_nums(data)
        func = self.get_registered_interrupt_func(pin, direction)
        if func is not None:
            flag = 0xff ^ LNcommon.get_bit_mask(pin)
            capture = self.emu_window.get_output_as_value()
            func(LNcommon.InterruptEvent(flag, capture))

    def get_registered_interrupt_func(self, pin, direction):
        for funcmap in self.pin_function_maps:
            if funcmap.pin_num == pin and funcmap.direction == direction:
                return funcmap.callback
        else:
            return None

    def quit_main_app(self, data):
        self.main_app.quit()


class InputWatcher(QObject):
    """Handles inputs and changes the emulator accordingly"""

    set_in_enable = Signal(int)
    set_in_disable = Signal(int)

    def __init__(self, emu_window):
        super().__init__()
        self.emu_window = emu_window
        cap = emu_window.LNdigital.intcapb.value  # clear interrupt
        self.event_listeners = list()
        for i in range(NUM_LN_DIGITALS):
            listener = LNdigitalIO.InputEventListener(
                emu_window.LNdigital)
            for i in range(8):
                listener.register(
                    i, LNdigitalIO.IODIR_BOTH, self.set_input)
            self.event_listeners.append(listener)

    def check_inputs(self):
        for listener in self.event_listeners:
            listener.activate()

    def stop_checking_inputs(self):
        for listener in self.event_listeners:
            listener.deactivate()

    def set_input(self, event):
        if event.direction == LNdigitalIO.IODIR_OFF:
            self.set_in_disable.emit(
                small_nums_to_single_val(event.pin_num,
                                         event.chip.hardware_addr))
        else:
            self.set_in_enable.emit(
                small_nums_to_single_val(event.pin_num,
                                         event.chip.hardware_addr))


def get_input_index_from_mouse(point, LNdig_ver):
    """returns the pin number based on the point clicked, also returns a
    boolean specifying if the press occured on a switch
    Returns:
        (pin, switch?)
    """
    x = point.x()
    y = point.y()

    # check for a switch press
    if (SWITCH_BOUNDARY_Y_TOP[LNdig_ver-1] < y and
            y < SWITCH_BOUNDARY_Y_BOTTOM[LNdig_ver-1]):
        for i in range(4):
            if (SWITCH_BOUNDARY_X_LEFT[LNdig_ver-1][i] < x and
                    x < SWITCH_BOUNDARY_X_RIGHT[LNdig_ver-1][i]):
                return (i, True)

    elif (PIN_BOUNDARY_Y_TOP[LNdig_ver-1] < y and
             y < PIN_BOUNDARY_Y_BOTTOM[LNdig_ver-1]):
        # check for a pin press
        for i in range(8):
            if (PIN_BOUNDARY_X_LEFT[LNdig_ver-1][i] < x and
                    x < PIN_BOUNDARY_X_RIGHT[LNdig_ver-1][i]):
                return (i, False)

    return (None, False)  # no pin found, press did not occur on switch


def start_q_watcher(app, emu_window, proc_comms_q_to_em, proc_comms_q_from_em):
    # need to spawn a worker thread that watches the proc_comms_q
    # need to seperate queue function from queue thread
    # http://stackoverflow.com/questions/4323678/threading-and-signals-problem
    # -in-pyqt
    q_watcher = QueueWatcher(
        app, emu_window, proc_comms_q_to_em, proc_comms_q_from_em)
    q_watcher_thread = QThread()
    q_watcher.moveToThread(q_watcher_thread)
    q_watcher_thread.started.connect(q_watcher.check_queue)

    # now that we've set up the thread, let's set up rest of signals/slots
    q_watcher.set_out_enable.connect(emu_window.set_output_enable)
    q_watcher.set_out_disable.connect(emu_window.set_output_disable)
    q_watcher.get_in.connect(emu_window.get_input)
    q_watcher.get_out.connect(emu_window.get_output)

    emu_window.send_output.connect(q_watcher.send_get_out_pin_result)
    emu_window.send_input.connect(q_watcher.send_get_in_pin_result)
    emu_window.interrupt_flagger.connect(q_watcher.handle_interrupt)

    # not sure why this doesn't work by connecting to q_watcher_thread.quit
    def about_to_quit():
        q_watcher_thread.quit()
    app.aboutToQuit.connect(about_to_quit)

    q_watcher_thread.start()


def start_input_watcher(app, emu_window):
    input_watcher = InputWatcher(emu_window)
    input_watcher_thread = QThread()
    input_watcher.moveToThread(input_watcher_thread)
    input_watcher_thread.started.connect(input_watcher.check_inputs)

    # signal / slots
    input_watcher.set_in_enable.connect(emu_window.set_input_enable)
    input_watcher.set_in_disable.connect(emu_window.set_input_disable)

    # quit setup
    def about_to_quit():
        input_watcher.stop_checking_inputs()
        input_watcher_thread.quit()
    app.aboutToQuit.connect(about_to_quit)

    input_watcher_thread.start()


def run_emulator(
        sysargv,
        use_LNdigital,
        init_board,
        emulated_LN):
    app = QApplication(sysargv)

    emu_window = LNdigitalEmulatorWindow()

    if use_LNdigital:
        emu_window.LNdigital = LNdigitalIO.LNdigitals(
            hardware_addr=emulated_LN.hardware_addr,
            bus=emulated_LN.bus,
            chip_select=emulated_LN.chip_select,
            init_board=init_board)

    emu_window.current_LN = emulated_LN.hardware_addr

    start_q_watcher(app,
                    emu_window,
                    emulated_LN.proc_comms_q_to_em,
                    emulated_LN.proc_comms_q_from_em)

    # only watch inputs if there is actually a LN digital
    if emu_window.LNdigital is not None:
        start_input_watcher(app, emu_window)

    emu_window.show()
    app.exec_()


def small_nums_to_single_val(val1, val2):
    return (val1 << 4) ^ val2


def single_val_to_small_nums(singleval):
    val2 = singleval & 0xf
    val1 = singleval >> 4
    return val1, val2
