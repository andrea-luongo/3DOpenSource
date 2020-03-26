from PySide2.QtCore import Signal, Slot
from PySide2.QtWidgets import QWidget
from PySide2.QtGui import QPixmap
import sys
import os
import subprocess
import shlex
from pathlib import Path

DEBUG_MODE_ON = False


class VisitechDLP9000(QWidget):

    print_text_signal = Signal(str)
    connection_status_signal = Signal(bool)
    display_image_signal = Signal(QPixmap)

    def __init__(self):
        QWidget.__init__(self)
        base_path = Path(__file__).parent
        if sys.platform == 'linux':
            self.i2c_cmd_filename = str((base_path / "../../resources/i2c_cmd").resolve())
        elif sys.platform == 'win32':
            self.i2c_cmd_filename = str((base_path / "../../resources/i2c_cmd.exe").resolve())
        else:
            if DEBUG_MODE_ON:
                print("Fix operating system, line 70.")
            sys.exit(1)
        if not os.path.isfile(self.i2c_cmd_filename):
            if DEBUG_MODE_ON:
                print("\"" + self.i2c_cmd_filename + "\" does not exist.")
            sys.exit(1)

        self.init_file = str((base_path / "../../resources/hdmi30fps.txt").resolve())


    @Slot()
    def init_projector(self):
        self.print_text_signal.emit('...Starting Projector: step 1 of 4...')
        command = self.i2c_cmd_filename + ' init hdmi'
        status = self.__send_command_to_projector__(command)
        if not status:
            self.print_text_signal.emit('...Projector initialization failed!')
            self.connection_status_signal.emit(False)
            return False
        self.print_text_signal.emit('...Starting Projector: step 2 of 4...')
        command = self.i2c_cmd_filename + ' upload ' + self.init_file + ' 0'
        status = self.__send_command_to_projector__(command)
        if not status:
            self.print_text_signal.emit('...Projector initialization failed!')
            self.connection_status_signal.emit(False)
            return False
        self.print_text_signal.emit('...Starting Projector: step 3 of 4...')
        command = self.i2c_cmd_filename + ' start'
        status = self.__send_command_to_projector__(command)
        if not status:
            self.print_text_signal.emit('...Projector initialization failed!')
            self.connection_status_signal.emit(False)
            return False
        self.print_text_signal.emit('...Starting Projector: step 4 of 4...')
        command = self.i2c_cmd_filename + ' setamplitude ' + str(0)
        status = self.__send_command_to_projector__(command)
        if not status:
            self.print_text_signal.emit('...Projector initialization failed!')
            self.connection_status_signal.emit(False)
            return False
        self.print_text_signal.emit("...Projector READY!")
        self.connection_status_signal.emit(True)
        return True

    def stop_projector(self):
        command = self.i2c_cmd_filename + ' stop'
        self.print_text_signal.emit(command)
        output = self.__send_command_to_projector__(command)
        self.connection_status_signal.emit(not output)

    def set_projector_amplitude(self, amplitude):
        command = self.i2c_cmd_filename + ' setamplitude ' + str(amplitude)
        if DEBUG_MODE_ON:
            print('setamplitude ' + str(amplitude))
        status = self.__send_command_to_projector__(command)
        return status

    def __send_command_to_projector__(self, command):
        if sys.platform == 'linux':
            p = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        elif sys.platform == 'win32':
            p = subprocess.run(command, capture_output=True)
        output = p.stdout
        err = p.stderr
        if DEBUG_MODE_ON:
            print('output:', output, 'error:', err)
        output = output.decode('UTF-8')
        err = err.decode('UTF-8')
        output_split = output.split('\r')
        err_split = err.split('\r')
        output_message = ''
        first_message = ''
        if len(output_split[0]) > 0:
            output_message = output_split[0].split(' ')[-2]
            first_message = output_split[0].split(' ')[0]
        if (output == '\r\n' or output_message == 'failed' or first_message == 'Problems'):
            self.print_text_signal.emit("Projector error: " + output)
            return False
        return True

