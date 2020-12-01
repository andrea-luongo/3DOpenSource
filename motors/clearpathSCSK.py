from PySide2.QtCore import QObject, Signal, Slot


class ClearpathSCSK(QObject):

    print_text_signal = Signal(str)
    connected_signal = Signal(bool)
    homed_signal = Signal(bool)
    move_to_origin_signal = Signal(bool)

    def __init__(self, spindle_pitch_microns=4000, steps_per_revolution=6400, axis_orientation=1):
        QObject.__init__(self)
        try:
            self.pywrapper = __import__('external_libraries.clearpath.clearpathPyWrapper', fromlist='ClearpathTeknicDriver')
        except ImportError:
            print("ImportError")
            return None
        self.scskTeknic = self.pywrapper.ClearpathTeknicDriver()
        self.is_connected = False
        self.ports_count = 0
        self.nodes = []
        self.nodes_id = []
        self.motor_parameters = []
        self.default_parameters = {"spindle_pitch_microns": spindle_pitch_microns,
                                   "steps_per_revolution": steps_per_revolution,
                                   "step_length_microns": spindle_pitch_microns / steps_per_revolution,
                                   "axis_orientation": axis_orientation}

    def get_step_length_microns(self):
        return self.default_parameters.get("step_length_microns")

    def set_node_parameters(self, node=0, port=0, spindle_pitch_microns=4000, steps_per_revolution=6400,
                            axis_orientation=1):
        try:
            if port < self.ports_count and node < self.nodes[port]:
                self.motor_parameters[port][node] = {"spindle_pitch_microns": spindle_pitch_microns,
                                                     "steps_per_revolution": steps_per_revolution,
                                                     "step_length_microns": spindle_pitch_microns / steps_per_revolution,
                                                     "axis_orientation": axis_orientation}
        except Exception as e:
            print(e)
            self.print_text_signal.emit("Selected Node is either busy or disconnected!")
        return

    def connect_motor(self, serial_port=None):
        try:
            is_successful, ports_count, nodes_count, nodes_id, text = self.scskTeknic.connect()
            self.ports_count = ports_count
            self.nodes = nodes_count
            self.nodes_id = nodes_id
            print(is_successful, ports_count, nodes_count, nodes_id, text)
            if is_successful == 1:
                self.is_connected = True
                self.print_text_signal.emit("Connecting to printer...")
                self.connected_signal.emit(True)
                for port in range(ports_count):
                    self.motor_parameters.append([])
                    for node in range(nodes_count[port]):
                        # is_homing = self.home_building_plate(node, port)
                        self.motor_parameters[port].append(self.default_parameters)
                self.print_text_signal.emit("Connection to printer ESTABLISHED!")
                return True, self.ports_count, self.nodes, self.nodes_id
            else:
                self.print_text_signal.emit("Connection to printer NOT established!")
                return False, 0, 0, 0
        except Exception as e:
            print(e)
            self.print_text_signal.emit("exception Connection to printer NOT established!")
            return False, 0, 0, 0

    def disconnect_motor(self):
        try:
            if self.is_connected and self.scskTeknic.close():
                self.print_text_signal.emit("...connection CLOSED!")
                self.connected_signal.emit(False)
                self.is_connected = False
                return True
            else:
                self.print_text_signal.emit("...connection NOT closed!")
                return False
        except Exception as e:
            print(e)
            self.print_text_signal.emit("...connection NOT closed!")
            return False

    def reset_motor(self):
        if self.is_connected:
            try:
                if self.scskTeknic.close():
                    self.disconnect_motor()
                    self.connect_motor()
                    self.print_text_signal.emit("printer status: RESET")
                    return True
                else:
                    return False
            except Exception as e:
                print(e)
                return False

    def home_motor(self, *args):
        node = args[0]
        port = args[1]
        wait_for_motor = args[2]
        if self.is_connected:
            try:
                self.scskTeknic.enableNodeMotion(node, port)
                is_valid, message = self.scskTeknic.home(node, port)
                print(node, port, message)
                if is_valid:
                    self.print_text_signal.emit("...homing building plate...")
                    if wait_for_motor:
                        homing_done = False
                        while not homing_done:
                            homing_done = not self.scskTeknic.isHoming(node, port)
                    self.print_text_signal.emit("building plate homed!")
                    self.homed_signal.emit(True)
                    return True
                else:
                    self.print_text_signal.emit("Problems homing building plate!")
                    return False
            except Exception as e:
                raise e

    def move_motor(self, distance_mm, feed_rate_mm_min, is_relative=True, *args):
        node = args[0]
        port = args[1]
        wait_for_motor = args[2]
        if self.is_connected:
            try:
                self.scskTeknic.enableNodeMotion(node, port)
                node_parameters = self.motor_parameters[port][node]
                counts = int(node_parameters.get("axis_orientation") * distance_mm * 1000 / node_parameters.get(
                    "step_length_microns"))
                spindle_pitch_mm = node_parameters.get("spindle_pitch_microns") / 1000.0
                feedrate_rpm = feed_rate_mm_min / spindle_pitch_mm
                expected_time = self.scskTeknic.move(counts, feedrate_rpm, is_relative, node, port)
                if wait_for_motor:
                    movement_done = False
                    while not movement_done:
                        movement_done = not self.scskTeknic.isMoving(node, port)
                self.print_text_signal.emit("building plate moved!")
                print(expected_time)
                return True
            except Exception as e:
                raise e

    def print_motor_position(self, *args):
        node = args[0]
        port = args[1]
        if self.is_connected:
            count_position = self.scskTeknic.getPosition(node, port)
            node_parameters = self.motor_parameters[port][node]
            position_mm = node_parameters.get("axis_orientation") * count_position * node_parameters.get(
                "step_length_microns") / 1000.0
            self.print_text_signal.emit("Motor at node " + str(node) + " and port " + str(port) + " is at:" + str(position_mm) + " mm")
        else:
            self.print_text_signal.emit("The printer is NOT connected!")
        return position_mm

    def stop_motor_movements(self):
        try:
            self.scskTeknic.stopAllMotion()
        except Exception as e:
            raise e

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