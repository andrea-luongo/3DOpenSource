"""
Created on Sun Mar 19 19:40:51 2017

@author: Sebastian Aagaard
"""
from motors.clearpathSCSK import ClearpathSCSK
import serial
import serial.tools.list_ports
import time
from PySide2.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool
import array
import random


class GCodeSender(QObject):

    print_text_signal = Signal(str)
    percentage_progress_signal = Signal(int)

    def __init__(self):
        QObject.__init__(self)
        self.__motor = ClearpathSCSK()
        self.__motor_nodes_count_list = [2]
        self.__motor_nodes_id_list = ["Disconnected 0", "Disconnected 1"]
        self.__motor_ports_connected = len(self.__motor_nodes_count_list)
        self.__building_plate_port = 0
        self.__wiper_port = 0
        self.__building_plate_node = 0
        self.__wiper_node = 1
        self.__wiper_recoat_offset_mm = 245
        self.__wiper_recoat_feedrate_mm_min = 1800
        self.__building_plate_recoat_offset_mm = 1
        self.__building_plate_recoat_feedrate_mm_min = 300
        self.__pause_toggle = False
        self.__ser = serial.Serial(timeout=5, write_timeout=0)
        self.__loaded_gcode = []
        self.__number_of_lines = 0
        self.__baudrates_list = (115200, 57600, 38400, 28800, 19200, 14400, 9600, 4800, 2400, 1200, 600, 300)
        self.__baudrate = self.__baudrates_list[0]
        self.__com_port = ''
        self.__available_ports = serial.tools.list_ports.comports()
        ports = ()
        for p in self.__available_ports:
            ports = ports + (str(p.device),)
        self.__available_ports = ports
        if len(self.__available_ports) > 0:
            self.__com_port = self.__available_ports[0]

        self.__threadpool = QThreadPool()

    def __del__(self):
        self.close_connection()

    @Slot()
    def get_building_plate_recoating_offset(self):
        return self.__building_plate_recoat_offset_mm

    @Slot()
    def get_building_plate_recoating_feedrate(self):
        return self.__building_plate_recoat_feedrate_mm_min

    @Slot(float)
    def set_building_plate_recoat_offset(self, value):
        self.__building_plate_recoat_offset_mm = value

    @Slot(float)
    def set_building_plate_recoat_feedrate(self, value):
        self.__building_plate_recoat_feedrate_mm_min = value

    @Slot()
    def get_wiper_recoating_offset(self):
        return self.__wiper_recoat_offset_mm

    @Slot()
    def get_wiper_recoating_feedrate(self):
        return self.__wiper_recoat_feedrate_mm_min

    @Slot(float)
    def set_wiper_recoat_offset(self, value):
        self.__wiper_recoat_offset_mm = value

    @Slot(float)
    def set_wiper_recoat_feedrate(self, value):
        self.__wiper_recoat_feedrate_mm_min = value

    @Slot()
    def get_motor_ports_connected(self):
        return self.__motor_ports_connected

    @Slot()
    def get_motor_nodes_count_list(self):
        return self.__motor_nodes_count_list

    @Slot()
    def get_motor_nodes_id_list(self):
        return self.__motor_nodes_id_list

    @Slot()
    def get_buildplate_port(self):
        return self.__building_plate_port

    @Slot(int)
    def set_buildplate_port(self, value):
        # print(self.__building_plate_port, value)
        self.__building_plate_port = value

    @Slot()
    def get_buildplate_node(self):
        return self.__building_plate_node

    @Slot(int)
    def set_buildplate_node(self, value):
        # print(self.__building_plate_node, value)
        self.__building_plate_node = value

    @Slot()
    def get_wiper_port(self):
        return self.__wiper_port

    @Slot(int)
    def set_wiper_port(self, value):
        # print(self.__wiper_plate_port, value)
        self.__wiper_port = value

    @Slot()
    def get_wiper_node(self):
        return self.__wiper_node

    @Slot(int)
    def set_wiper_node(self, value):
        # print(self.__wiper_node, value)
        self.__wiper_node = value

    def home_motors(self):
        self.print_text_signal.emit("..Homing Build plate..")
        self.__motor.home_motor(self.__building_plate_node, self.__building_plate_port, wait_for_motor=True)
        self.print_text_signal.emit("..Homing Wiper..")
        self.__motor.home_motor(self.__wiper_node, self.__wiper_port, wait_for_motor=True)
        self.print_text_signal.emit("..Done Homing..")

    def motor_connect(self):
        is_connected, self.__motor_ports_connected, self.__motor_nodes_count_list, self.__motor_nodes_id_list = self.__motor.connect_motor()
        if not is_connected:
            self.__motor_nodes_count_list = [2]
            self.__motor_nodes_id_list = ["Disconnected 0", "Disconnected 1"]
            self.__motor_ports_connected = len(self.__motor_nodes_count_list)
        self.__motor.set_node_parameters(node=self.__building_plate_node, spindle_pitch_microns=4000, steps_per_revolution=6400, axis_orientation=-1)
        self.__motor.set_node_parameters(node=self.__wiper_node, spindle_pitch_microns=4000, steps_per_revolution=6400, axis_orientation=1)
        if self.__motor.is_connected:
            self.print_text_signal.emit("Connection to ClearPath Motors established!")
        else:
            self.print_text_signal.emit("... problems connecting to ClearPath Motors!")

    def pause(self):
        self.__pause_toggle = not self.__pause_toggle
        print("pausing")
        # self.execute_gcode_command("S1")
        if self.__pause_toggle:
            self.print_text_signal.emit("Program Paused")
        else:
            self.print_text_signal.emit("Program Unpaused")

    def disconnect(self):
        self.__ser.close()
        self.print_text_signal.emit("Serial Connection is Closed")

    def start(self):
        worker = Worker(self.__start)
        self.__threadpool.start(worker)
        # self.__start()

    def __start(self):
        self.print_text_signal.emit("Starting Printing Process!")
        self.__pause_toggle = False
        pause_command_to_send = False
        for line_idx, line in enumerate(self.__loaded_gcode):
            if self.__pause_toggle:
                self.execute_gcode_command("S1")
                pause_command_to_send = True
            while self.__pause_toggle:
                useless_command = 1
                # print("I am paused!")
                # time.sleep(1)
            if pause_command_to_send:
                self.execute_gcode_command("S1")
                pause_command_to_send = False

            line = self.remove_comment(line).strip()
            # line = line.strip()  # Strip all EOL characters for streaming
            progress_percentage = (line_idx + 1) / self.__number_of_lines * 100
            self.percentage_progress_signal.emit(int(progress_percentage))
            if not line.isspace() and len(line) > 0:
                self.print_text_signal.emit('Executing Line: ' + line)
                self.execute_gcode_command(line)

    def __execute_motor_command(self, command):
        if not self.__motor.is_connected:
            self.print_text_signal.emit("...Motors are NOT connected!")
            return
        command = command.replace(" ", "")  # remove all whitespace for better reading
        # Homing
        if command[1] == "0":
            self.print_text_signal.emit("...Homing motor...")
            self.home_motors()
        # Move building plate
        elif command[1] == "1":
            self.print_text_signal.emit("...Moving Z stage...")
            is_relative = True
            movement_type = command[2]
            if movement_type == "A":
                is_relative = False
            elif movement_type is not "R":
                self.print_text_signal.emit("...Invalid Motor Command!")
                return
            new_pos = float(command[3:])
            self.__motor.move_motor(distance_mm=new_pos, feed_rate_mm_min=300, is_relative=is_relative,
                                    node=self.__building_plate_node, wait_for_motor=True)
            self.print_text_signal.emit("Build Height is " + str(self.__motor.print_motor_position(self.__building_plate_node, 0)) + " mm")
        # Move wiper
        elif command[1] == "2":
            self.print_text_signal.emit("...Moving Wiper...")
            is_relative = True
            movement_type = command[2]
            if movement_type == "A":
                is_relative = False
            elif movement_type is not "R":
                self.print_text_signal.emit("...Invalid Motor Command!")
                return
            new_pos = float(command[3:])
            self.__motor.move_motor(distance_mm=new_pos, feed_rate_mm_min=300, is_relative=is_relative, node=self.__wiper_node, wait_for_motor=True)
            self.print_text_signal.emit("Wiper position: " + str(self.__motor.print_motor_position(self.__wiper_node, 0)) + " mm")
            #     return
        # Recoating
        elif command[1] == "3":
            self.print_text_signal.emit("...Recoating...")
            self.__motor.move_motor(distance_mm=self.__wiper_recoat_offset_mm, feed_rate_mm_min=self.__wiper_recoat_feedrate_mm_min, is_relative=False, node=self.__wiper_node, wait_for_motor=True)
            self.__motor.move_motor(distance_mm=self.__building_plate_recoat_offset_mm, feed_rate_mm_min=self.__building_plate_recoat_feedrate_mm_min, is_relative=True, node=self.__building_plate_node, wait_for_motor=True)
            self.__motor.move_motor(distance_mm=0, feed_rate_mm_min=self.__wiper_recoat_feedrate_mm_min, is_relative=False, node=self.__wiper_node, wait_for_motor=True)
            self.__motor.move_motor(distance_mm=-self.__building_plate_recoat_offset_mm, feed_rate_mm_min=self.__building_plate_recoat_feedrate_mm_min, is_relative=True, node=self.__building_plate_node, wait_for_motor=True)
        else:
            self.print_text_signal.emit("..Not understood, sorry..")

    @staticmethod
    def __append_checksum(msg):
        checksum = 0
        a1 = array.array('B', msg.encode('ascii'))
        for idx in range(len(a1)):
            checksum ^= a1[idx]
        return (msg + '*' + str(checksum) + '\n').encode('ascii'), checksum

    def execute_gcode_command(self, command, wait_for_serial=True):
        self.print_text_signal.emit("Send: %s" % command)
        if command[0:1] == "C":
            self.__execute_motor_command(command)
        elif self.__ser.is_open:
            msg, checksum = self.__append_checksum(command)
            self.__ser.write(msg)  # Send g-code block
            if wait_for_serial:
                self.__wait_for_serial_reply(command)
        else:
            self.print_text_signal.emit("Serial connection NOT established!")
            self.print_text_signal.emit("-- Input will be ignored --")

    def emergency_stop(self):
        self.execute_gcode_command("S0", wait_for_serial=False)
        self.print_text_signal.emit("Program was stopped - please restart unit!")

    # Pure functionality
    def connect_serial(self):
        self.__ser.close()
        self.__ser.port = self.__com_port
        self.__ser.baudrate = self.__baudrate
        if self.__ser.port == '':
            self.print_text_signal.emit("A valid port was NOT selected! Select a valid port.")
            return False
        try:
            self.__ser.open()
            self.print_text_signal.emit("Connecting to Arduino")
            time.sleep(2)  # Wait for  initialization # this line shouldn't be needed
            # self.execute_gcode_command("M999")
            # Wake up
            self.__ser.reset_input_buffer()  # Flush startup text in serial input
            self.print_text_signal.emit("\nTeensy reporting ready for Phew Phew!\n")
        except Exception as e:
            print(e)
            self.__ser.close()
            self.print_text_signal.emit("Connection to " + self.__ser.port + " NOT established!")
            return False

    def __wait_for_serial_reply(self, command):
        self.__ser.reset_input_buffer()  # Flush startup text in serial input
        # Serial read section
        received_msg = ""
        to_resend = False
        while received_msg != 'ok':
            received_msg = self.__ser.readline().decode("utf-8").strip()
            if len(received_msg) > 0:
                self.print_text_signal.emit("Received: " + received_msg)
            if received_msg == 'resend':
                to_resend = True
                break
        if to_resend:
            msg, checksum = self.__append_checksum(command)
            self.__ser.write(msg)  # Send g-code block
            self.__wait_for_serial_reply(command)
        # if self.__pause_toggle is True:
        #     self.execute_gcode_command("S1")

    @Slot()
    def close_connection(self):
        if self.__motor.is_connected:
            self.__motor.disconnect_motor()
        if self.__ser.isOpen():
            if self.__pause_toggle:
                self.pause()
            self.__ser.close()
        print("Connection Closed!")

    def open_file(self, file_path):
        try:
            f = open(file_path, 'r')
            self.__loaded_gcode = f.readlines()
            self.__loaded_gcode = list(filter(bool, self.__loaded_gcode))
            self.__number_of_lines = len(self.__loaded_gcode)
            self.print_text_signal.emit("File name: %s" % file_path)
            self.print_text_signal.emit("Number of Lines: %s" % self.__number_of_lines)
            self.percentage_progress_signal.emit(0)
            f.close()
        except Exception as e:
            print(e)
            self.print_text_signal.emit("Problems loading the GCode file!")
            return False

    @staticmethod
    def remove_comment(string):
        if string.find(';') == -1:
            return string
        else:
            return string[:string.index(';')]

    @Slot()
    def update_port_list(self):
        self.__available_ports = serial.tools.list_ports.comports()
        ports = ()
        for p in self.__available_ports:
            ports = ports + (str(p.device),)
        self.__available_ports = ports

    def get_ports_list(self):
        return self.__available_ports

    @Slot(int)
    def set_comport(self, idx):
        if idx > 0:
            self.__com_port = self.__available_ports[idx]
        else:
            self.__com_port = ''

    def get_comport(self):
        return self.__com_port

    @Slot(int)
    def set_baudrate(self, baudrate_idx):
        self.__baudrate = self.__baudrates_list[baudrate_idx]
        self.print_text_signal.emit("Baudrate changed to %i" % self.__baudrate)
        self.print_text_signal.emit("Reset the serial connection for this to have any effect!")

    def get_baudrate(self):
        return self.__baudrate

    def get_baudrates_list(self):
        return self.__baudrates_list


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        result = self.fn(*self.args, **self.kwargs)
        return result
