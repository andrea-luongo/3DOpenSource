from PySide2.QtCore import QObject, Signal, Slot, QTimer, QRunnable, QThreadPool
import sys
from serial.tools import list_ports
from enum import Enum
from motors import clearpathSDSK, nanostage, clearpathSCSK


class DLPMotorController(QObject):

    class MOVEMENT_MESSAGE(Enum):
        MANUAL_MOVEMENT = 0
        INFILTRATION_STEP = 1
        REPOSITIONING_MOVEMENT = 2
        ORIGIN_MANUAL_MOVEMENT = 3
        ORIGIN_SETUP_MOVEMENT = 4
        PROJECTOR_MOVEMENT = 5
        NONE = 6

    print_text_signal = Signal(str)
    repositioning_completed_signal = Signal()
    ready_for_printing_signal = Signal()

    def __init__(self, printer_setup='BOTTOM-UP', motor_setup='ClearpathSDSK', spindle_pitch_micron=None, steps_per_revolution=None):
        QObject.__init__(self)
        if printer_setup == 'BOTTOM-UP':
            self.platform_direction = -1
        else:
            self.platform_direction = 1

        if motor_setup == 'ClearpathSDSK':
            self.motor_instance = clearpathSDSK.ClearpathSDSK()
        elif motor_setup == 'ClearpathSCSK':
            self.motor_instance = clearpathSCSK.ClearpathSCSK(axis_orientation=-1)
            if self.motor_instance is None:
                self.print_text_signal.emit("Clearpath SCSK not supported: selected Clearpath SDSK")
                self.motor_instance = clearpathSDSK.ClearpathSDSK()
        elif motor_setup == 'Nanostage':
            self.motor_instance = nanostage.NanoStage()
        else:
            print("Error: an invalid motor was selected!")
            sys.exit(1)
        self.motor_instance.print_text_signal.connect(self.print_to_console)
        self.motor_instance.connected_signal.connect(self.set_connection_status)
        self.motor_instance.homed_signal.connect(self.homing_completed)
        self.current_movement_message = self.MOVEMENT_MESSAGE.NONE
        self.motor_movement_timer = QTimer()
        self.motor_movement_timer.setSingleShot(True)
        self.motor_movement_timer.timeout.connect(self.__handle_movement_signals__)
        self.delay_timer = QTimer()
        self.delay_timer.setSingleShot(True)
        self.delay_timer.timeout.connect(self.__emit_repositioned_signal__)
        self.repositioning_delay = 500  # s
        self.feed_rate = 300  # mm/min
        self.projector_feed_rate = 300
        self.manual_plate_distance = 0  # mm
        self.manual_projector_distance = 0  # mm
        self.building_plate_origin = 0
        self.current_plate_position = 0
        self.projector_origin = 0
        self.projector_current_position = 0
        self.repositioning_offset = 5  # mm
        self.layer_thickness = 0
        self.available_ports = list_ports.comports()
        self.serial_port = ''
        ports = ()
        for p in self.available_ports:
            ports = ports + (str(p.device),)
        self.available_ports = ports
        if len(self.available_ports) > 0:
            self.serial_port = self.available_ports[0]
        self.building_plate_is_moving = False
        self.projector_is_moving = False
        self.is_connected = False
        self.threadpool = QThreadPool()

    def __wait_for_movement__(self, movement_length, feed_rate, message=0):
        delay = abs(movement_length)/feed_rate * 60 * 1000  # in ms
        self.current_movement_message = message
        print('delay', delay)
        self.motor_movement_timer = QTimer()
        self.motor_movement_timer.setSingleShot(True)
        self.motor_movement_timer.timeout.connect(self.__handle_movement_signals__)
        self.motor_movement_timer.setInterval(delay)
        self.motor_movement_timer.start()

    @Slot()
    def connect_printer(self):
        worker = Worker(self.motor_instance.connect_motor, self.serial_port)
        self.threadpool.start(worker)

    @Slot()
    def disconnect_printer(self):
        if self.motor_instance.disconnect_motor():
            self.building_plate_is_moving = False
            self.projector_is_moving = False
            self.is_connected = False

    @Slot()
    def reset_printer(self):
        if self.is_connected:
            self.motor_instance.reset_printer()
        else:
            self.print_text_signal.emit("The printer is NOT connected!")

    @Slot()
    def home_building_plate(self):
        if self.building_plate_is_moving:
            self.print_text_signal.emit("Building plate already moving!")
            return False
        if self.is_connected:
            self.building_plate_is_moving = True
            # self.motor_instance.home_building_plate()
            worker = Worker(self.motor_instance.home_motor)
            self.threadpool.start(worker)
            return True
        else:
            self.print_text_signal.emit("The printer is NOT connected!")
            return False

    @Slot()
    def reposition_next_layer(self, thickness):
        self.motor_instance.reposition_next_layer(thickness)

    @Slot()
    def begin_printing_process(self):
        self.motor_instance.begin_printing_process()

    @Slot()
    def set_origin(self):
        if self.is_connected:
            self.building_plate_origin = self.current_plate_position
            self.print_text_signal.emit("Setting NEW ORIGIN!")
            # self.motor_instance.set_origin()
        else:
            self.print_text_signal.emit("The printer is NOT connected!")
            return False

    @Slot()
    def move_building_plate(self, target_mm=None, print_on=True, message=None, relative_move=True):
        if message is None:
            message = self.MOVEMENT_MESSAGE.ORIGIN_MANUAL_MOVEMENT
        if target_mm is None:
            target_mm = self.manual_plate_distance
        if self.building_plate_is_moving:
            self.print_text_signal.emit("Building plate already moving!")
            return
        if self.is_connected:
            if self.motor_instance.move_motor(target_mm, self.feed_rate, relative_move):
                self.building_plate_is_moving = True
                if print_on:
                    self.print_text_signal.emit("...moving the building plate by " + str(target_mm) + "mm...")
                if relative_move:
                    self.current_plate_position += target_mm
                    distance_to_target = target_mm
                else:
                    distance_to_target = abs(self.current_plate_position - target_mm)
                    self.current_plate_position = target_mm
                self.__wait_for_movement__(distance_to_target, self.feed_rate, message)
                # if print_on:
                #     self.print_text_signal.emit("...building plate in position!")
        else:
            self.print_text_signal.emit("The printer is NOT connected!")

    @Slot()
    def move_plate_to_origin(self, message=None):
        if message is None:
            message = self.MOVEMENT_MESSAGE.ORIGIN_MANUAL_MOVEMENT
        if self.building_plate_is_moving:
            self.print_text_signal.emit("Building plate already moving!")
            return
        if self.is_connected:
            if self.motor_instance.move_motor(self.building_plate_origin, self.feed_rate, is_relative=False):
                self.building_plate_is_moving = True
                distance_to_target = abs(self.current_plate_position - self.building_plate_origin)
                self.__wait_for_movement__(distance_to_target, self.feed_rate, message)
                self.current_plate_position = self.building_plate_origin
        else:
            self.print_text_signal.emit("The printer is NOT connected!")

    @Slot()
    def move_projector(self, target=None, relative_move=True):
        if target is None:
            target = self.manual_projector_distance
        if self.projector_is_moving:
            self.print_text_signal.emit("Projector already moving!")
            return
        if self.is_connected:
            if self.motor_instance.move_projector(target, self.projector_feed_rate, relative_move):
                self.projector_is_moving = True
                if relative_move:
                    self.projector_current_position += target
                    distance_to_target = target
                else:
                    distance_to_target = abs(self.projector_current_position - target)
                    self.projector_current_position = target
                self.__wait_for_movement__(distance_to_target, self.projector_feed_rate, self.MOVEMENT_MESSAGE.PROJECTOR_MOVEMENT)
        else:
            self.print_text_signal.emit("The printer is NOT connected!")

    @Slot()
    def home_projector(self):
        if self.projector_is_moving:
            self.print_text_signal.emit("Projector already moving!")
            return
        if self.is_connected:
            self.motor_instance.home_projector()
            self.projector_current_position = 0
        else:
            self.print_text_signal.emit("The printer is NOT connected!")

    @Slot()
    def lock_projector(self):
        if self.is_connected:
            self.motor_instance.lock_projector()
        else:
            self.print_text_signal.emit("The printer is NOT connected!")

    @Slot(int)
    def select_port(self, idx):
        if idx >= 0:
            self.serial_port = self.available_ports[idx]
        else:
            self.serial_port = ''

    @Slot()
    def update_port_list(self):
        self.available_ports = list_ports.comports()
        ports = ()
        for p in self.available_ports:
            ports = ports + (str(p.device),)
        self.available_ports = ports

    @Slot()
    def get_port_list(self):
        return self.available_ports

    @Slot(float)
    def update_manual_plate_distance(self, distance):
        self.manual_plate_distance = distance

    @Slot(float)
    def update_manual_projector_distance(self, distance):
        self.manual_projector_distance = distance

    @Slot()
    def print_motor_position(self):
        self.motor_instance.print_motor_position()

    def stop_motor_movements(self):
        self.motor_instance.stop_motor_movements()
        self.building_plate_is_moving = False
        self.projector_is_moving = False

    @Slot(str)
    def print_to_console(self, text):
        self.print_text_signal.emit(text)

    def __infiltration_step__(self):
        movement_offset = self.platform_direction * self.repositioning_offset
        self.move_building_plate(target_mm=movement_offset, print_on=False,
                                 message=self.MOVEMENT_MESSAGE.INFILTRATION_STEP)

    def __lowering_step__(self):
        movement_offset = self.platform_direction * (-self.repositioning_offset + self.layer_thickness)
        self.move_building_plate(target_mm=movement_offset, print_on=False,
                                 message=self.MOVEMENT_MESSAGE.REPOSITIONING_MOVEMENT)

    def __finish_repositioning__(self):
        self.delay_timer = QTimer()
        self.delay_timer.setSingleShot(True)
        self.delay_timer.timeout.connect(self.__emit_repositioned_signal__)
        self.delay_timer.setInterval(self.repositioning_delay)
        self.delay_timer.start()

    def begin_printing_process(self):
        self.move_plate_to_origin(message=self.MOVEMENT_MESSAGE.ORIGIN_SETUP_MOVEMENT)

    def reposition_next_layer(self, thickness):
        self.layer_thickness = thickness
        if self.layer_thickness > 0.0:
            self.__infiltration_step__()
        else:
            self.delay_timer = QTimer()
            self.delay_timer.setSingleShot(True)
            self.delay_timer.timeout.connect(self.__emit_repositioned_signal__)
            self.delay_timer.setInterval(self.repositioning_delay)
            self.delay_timer.start()

    def __handle_movement_signals__(self):
        if self.current_movement_message == self.MOVEMENT_MESSAGE.MANUAL_MOVEMENT \
                or self.current_movement_message == self.MOVEMENT_MESSAGE.ORIGIN_MANUAL_MOVEMENT:
            self.building_plate_is_moving = False
            self.print_text_signal.emit("...building plate in position!")
        elif self.current_movement_message == self.MOVEMENT_MESSAGE.ORIGIN_SETUP_MOVEMENT:
            self.building_plate_is_moving = False
            self.ready_for_printing_signal.emit()
        elif self.current_movement_message == self.MOVEMENT_MESSAGE.INFILTRATION_STEP:
            self.building_plate_is_moving = False
            self.__lowering_step__()
        elif self.current_movement_message == self.MOVEMENT_MESSAGE.REPOSITIONING_MOVEMENT:
            self.building_plate_is_moving = False
            self.__finish_repositioning__()
        elif self.current_movement_message == self.MOVEMENT_MESSAGE.PROJECTOR_MOVEMENT:
            self.projector_is_moving = False

    def __emit_repositioned_signal__(self):
        self.repositioning_completed_signal.emit()

    @Slot(bool)
    def set_connection_status(self, status):
        self.is_connected = status

    @Slot(bool)
    def homing_completed(self, is_completed):
        self.building_plate_is_moving = False
        if is_completed:
            self.current_plate_position = 0

    def get_motor_step_length_microns(self):
        return self.motor_instance.get_step_length_microns()


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        result = self.fn(*self.args, **self.kwargs)

