from PySide2.QtCore import QObject, Signal, Slot
from pipython import GCSDevice, pitools, gcserror


class NanoStage(QObject):

    print_text_signal = Signal(str)
    connected_signal = Signal(bool)
    homed_signal = Signal(bool)
    move_to_origin_signal = Signal(bool)

    def __init__(self, controller_name='C-863.11', stage_name='L-511', ref_mode='FNL', spindle_pitch_microns=2000, steps_per_revolution=20000):
        QObject.__init__(self)
        self.axis_orientation = 1
        self.controller_name = controller_name
        self.stage_name = stage_name
        self.ref_mode = ref_mode
        self.gcs = GCSDevice(self.controller_name)
        self.projector_locked = True
        self.spindle_pitch_microns = spindle_pitch_microns  # mm
        self.steps_per_revolution = steps_per_revolution
        self.step_length_microns = self.spindle_pitch_microns / self.steps_per_revolution  # microns
        self.is_connected = False

    def get_step_length_microns(self):
        return self.step_length_microns

    @Slot()
    def connect_motor(self, serial_port, *args):
        if serial_port == '':
            self.print_text_signal.emit("A valid port was NOT selected! Select a valid port.")
            return False
        try:
            serialnum = args[0]
            self.gcs.ConnectUSB(serialnum=serialnum)
            pitools.startup(self.gcs, refmode=self.ref_mode)
            self.print_text_signal.emit("Connecting to " + serial_port + "...")
            #
            if self.gcs.IsConnected():
                self.is_connected = True
                range_min = list(self.gcs.qTMN().values())
                range_max = list(self.gcs.qTMX().values())
                ranges = list(zip(range_min, range_max))
                print(ranges)
                self.print_text_signal.emit("Connection to Nanostage ESTABLISHED!")
                self.connected_signal.emit(True)
                return True
            else:
                self.print_text_signal.emit("Connection to printer NOT established!")
                return False
        except Exception as e:
            print(e)
            self.gcs.close()
            self.print_text_signal.emit("Connection to Nanostage NOT established!")
            return False

    @Slot()
    def disconnect_motor(self):
        if self.is_connected:
            try:
                self.gcs.close()
                self.print_text_signal.emit("...connection CLOSED!")
                self.connected_signal.emit(False)
                self.is_connected = False
                return True
            except:
                self.print_text_signal.emit("...connection NOT closed!")
                return False

    @Slot()
    def reset_printer(self):
        if self.is_connected:
            try:
                self.disconnect_printer()
                self.connect_printer()
                self.print_text_signal.emit("printer status: RESET")
                return True
            except:
                return False

    @Slot()
    def home_motor(self):
        if self.is_connected:
            try:
                self.print_text_signal.emit("...homing building plate...")
                self.gcs.GOH()
                pitools.waitontarget(self.gcs)
                self.print_text_signal.emit("building plate homed!")
                self.homed_signal.emit(True)
                return True
            except Exception as e:
                self.print_text_signal.emit("Problems homing building plate!")
                self.homed_signal.emit(False)
                raise e

    @Slot()
    def move_motor(self, distance_mm, feed_rate_mm_min, is_relative=True):
        if self.is_connected:
            try:
                if is_relative:
                    self.gcs.MVR(self.gcs.axes, self.axis_orientation * distance_mm)
                else:
                    self.gcs.MOV(self.gcs.axes, self.axis_orientation * distance_mm)
                return True
            except Exception as e:
                self.print_text_signal.emit("Position out of limits!")
                return False

    @Slot()
    def move_projector(self, distance, feed_rate, relative_move=True):
        self.print_text_signal.emit("Projector movement not supported!")
        return False

    @Slot()
    def home_projector(self):
        self.print_text_signal.emit("Projector movement not supported!")
        return False

    @Slot()
    def lock_projector(self):
        self.print_text_signal.emit("Projector movement not supported!")
        return False

    @Slot()
    def print_motor_position(self):
        if self.is_connected:
            positions = self.gcs.qPOS(self.gcs.axes)
            self.print_text_signal.emit("Building plate position:" + str(list(positions.values())) + " mm")
        else:
            self.print_text_signal.emit("The printer is NOT connected!")

    def stop_motor_movements(self):
        try:
            self.gcs.STP()
        except gcserror.E10_PI_CNTR_STOP as e:
            self.print_text_signal.emit("Motor abruptly stopped!")


