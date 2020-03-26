from DLPPrinter.dlpMotorController import DLPMotorController
from DLPPrinter.dlpProjectorController import DLPProjectorController
from PySide2.QtGui import QPixmap
from PySide2.QtCore import QObject, Signal, Slot, QTimer, QFile, QIODevice, QJsonDocument, QTime, QDate, QDateTime
from pathlib import Path

DEBUG_MODE_ON = False

class DLPMainController(QObject):

    print_text_signal = Signal(str)
    display_image_signal = Signal(QPixmap)
    block_parameters_signal = Signal()
    reactivate_parameters_signal = Signal()
    etc_updated_signal = Signal(float)

    def __init__(self, printer_setup='BOTTOM-UP', projector_setup='VisitechDLP9000', motor_setup='ClearpathSDSK'):
        QObject.__init__(self)
        self.printer_setup = printer_setup
        self.projector_setup = projector_setup
        self.motor_setup = motor_setup
        self.__default_parameters = {}
        self.__load_default_parameters__()
        self.TEST_MODE = False
        base_path = Path(__file__).parent
        self.output_file = str((base_path / '../resources/SAVED_POSITION.txt').resolve())
        # self.output_file = '../resources/SAVED_POSITION.txt'
        # self.__motor_controller = DLPMotorController(self.printer_setup, self.motor_setup)
        # self.__projector_controller = DLPProjectorController(self.projector_setup)
        self.print_status = "SUCCESS"
        self.error_message = ""
        self.printing_date = ""
        self.printing_time = ""
        self.username = "username"
        self.print_job_name = "print job name"
        self.current_layer = 0
        self.current_burning_layer = 0
        self.number_of_layers = 0
        self.is_printing = False
        self.next_layer_timer = QTimer()
        self.next_layer_timer.setSingleShot(True)

        # Printing parameters
        self.current_thickness = 0
        self.current_amplitude = 0
        self.current_exposure = 0
        self.current_file_name = ''
        # Support Parameters
        self.support_thickness = self.__default_parameters['support_thickness (mm)']  # mm
        self.support_exposure = self.__default_parameters['support_exposure (ms)']  # ms
        self.support_amplitude = int(self.__default_parameters['support_amplitude'])
        self.support_burn_layers = int(self.__default_parameters['support_burn_layers'])
        self.support_burn_exposure = self.__default_parameters['support_burn_exposure (ms)']  # ms
        self.support_burn_amplitude = int(self.__default_parameters['support_burn_amplitude'])
        self.support_file_names = {}
        # Features Parameters
        self.features_thickness = self.__default_parameters['features_thickness (mm)']  # mm
        self.features_exposure = self.__default_parameters['features_exposure (ms)']  # ms
        self.features_amplitude = int(self.__default_parameters['features_amplitude'])
        self.features_burn_layers = int(self.__default_parameters['features_burn_layers'])
        self.features_burn_exposure = self.__default_parameters['features_burn_exposure (ms)']  # ms
        self.features_burn_amplitude = int(self.__default_parameters['features_burn_amplitude'])
        self.features_file_names = {}
        # Advanced Parameters
        self.incremental_thickness = self.__default_parameters['incremental_thickness']
        self.incremental_exposure = self.__default_parameters['incremental_exposure']
        self.incremental_amplitude = self.__default_parameters['incremental_amplitude']
        self.starting_incremental_thickness = self.__default_parameters['starting_incremental_thickness (mm)']  # mm
        self.incremental_step_thickness = self.__default_parameters['incremental_step_thickness (mm)']  # mm
        self.starting_incremental_exposure = self.__default_parameters['starting_incremental_exposure (ms)']  # ms
        self.incremental_step_exposure = self.__default_parameters['incremental_step_exposure (ms)']  # ms
        self.starting_incremental_amplitude = int(self.__default_parameters['starting_incremental_amplitude'])
        self.incremental_step_amplitude = int(self.__default_parameters['incremental_step_amplitude'])
        self.fixed_layer = self.__default_parameters['fixed_layer']
        self.grayscale_correction = self.__default_parameters['grayscale_correction']
        self.grayscale_alpha = self.__default_parameters['grayscale_alpha']
        self.grayscale_beta = self.__default_parameters['grayscale_beta']
        self.grayscale_gamma = self.__default_parameters['grayscale_gamma']
        # Others
        self.projector_amplitude = int(self.__default_parameters['projector_amplitude'])
        self.spindle_pitch_microns = self.__default_parameters['spindle_pitch_microns']
        self.motor_steps_per_revolution = self.__default_parameters['motor_steps_per_revolution']
        self.__motor_controller = DLPMotorController(self.printer_setup, self.motor_setup, self.spindle_pitch_microns, self.motor_steps_per_revolution)
        self.__projector_controller = DLPProjectorController(self.projector_setup)
        self.__motor_controller.feed_rate = self.__default_parameters['feed_rate (mm/min)']
        self.__motor_controller.projector_feed_rate = self.__default_parameters['projector_feed_rate (mm/min)']
        self.__motor_controller.repositioning_delay = self.__default_parameters['repositioning_delay (ms)']
        self.__motor_controller.repositioning_offset = self.__default_parameters['repositioning_offset (mm)']
        self.projector_pixel_size = self.__default_parameters['projector_pixel_size (mm)']
        self.projector_width = self.__default_parameters['projector_width']
        self.projector_height = self.__default_parameters['projector_height']
        self.set_horizontal_mirroring(self.__default_parameters['horizontal_mirror'])
        self.set_vertical_mirroring(self.__default_parameters['vertical_mirror'])
        self.samples_per_pixel = int(self.__default_parameters['samples_per_pixel'])
        self.save_default_parameters()
        self.connect_signals_to_slots()

    @Slot()
    def connect_signals_to_slots(self):
        self.__motor_controller.print_text_signal.connect(self.print_to_console)
        self.__projector_controller.print_text_signal.connect(self.print_to_console)
        self.__projector_controller.display_image_signal.connect(self.display_image_preview)
        self.__motor_controller.repositioning_completed_signal.connect(self.project_next_layer)
        self.__motor_controller.ready_for_printing_signal.connect(self.prepare_next_layer)
        self.next_layer_timer.timeout.connect(self.prepare_next_layer)

    @Slot()
    def stop_printing_process(self, save_parameters=True):
        # if not self.is_printing:
        #     return
        self.print_text_signal.emit("Stopping printing process...")
        if save_parameters:
            self.print_status = "STOPPED"
            self.save_current_parameters()
        self.__projector_controller.clear_image()
        self.__projector_controller.set_amplitude(0)
        self.is_printing = False
        self.blockSignals(True)
        self.next_layer_timer.stop()
        self.__motor_controller.delay_timer.stop()
        self.__motor_controller.motor_movement_timer.stop()
        self.__motor_controller.blockSignals(True)
        self.__projector_controller.blockSignals(True)
        try:
            self.__motor_controller.stop_motor_movements()
        except Exception as e:
            print(e)
            raise e
        self.blockSignals(False)
        self.__projector_controller.blockSignals(False)
        self.__motor_controller.blockSignals(False)
        self.reactivate_parameters_signal.emit()
        self.print_text_signal.emit("... printing process stopped!")

    @Slot()
    def starting_printing_process(self):
        if self.is_printing:
            self.print_text_signal.emit("Already printing!")
            return
        if self.__motor_controller.is_connected or DEBUG_MODE_ON:
            self.printing_date = QDate.currentDate().toString("yyyy.MM.dd")
            self.printing_time = QTime.currentTime().toString("hh.mm.ss")
            self.is_printing = True
            self.block_parameters_signal.emit()
            self.current_layer = 0
            self.current_burning_layer = 0
            self.number_of_layers = len(self.features_file_names) + len(self.support_file_names)
            self.print_text_signal.emit("Starting printing process ...")
            self.__print_support_parameters__()
            self.__print_features_parameters__()
            if DEBUG_MODE_ON:
                self.prepare_next_layer()
            else:
                self.__motor_controller.begin_printing_process()
        else:
            self.print_text_signal.emit("The printer is NOT connected!")

    @Slot()
    def prepare_next_layer(self):
        try:
            estimated_time_ms = self.evaluate_time_estimate(self.current_layer)
            self.print_text_signal.emit("ETC: " + QDateTime.fromTime_t(estimated_time_ms/1000.0).toUTC().toString('hh:mm:ss'))
            self.__projector_controller.clear_image()
            if not DEBUG_MODE_ON:
                if not self.__projector_controller.set_amplitude(0):
                    self.stop_printing_process()
                    return
            # self.__projector_controller.set_projector_amplitude(0)
            move_building_plate = True
            if self.current_layer < len(self.support_file_names):
                self.current_file_name = self.support_file_names[self.current_layer]
                self.current_thickness = self.support_thickness
                is_burning_layer = self.current_layer < self.support_burn_layers
                if is_burning_layer:
                    self.current_amplitude = self.support_burn_amplitude
                    self.current_exposure = self.support_burn_exposure
                else:
                    self.current_amplitude = self.support_amplitude
                    self.current_exposure = self.support_exposure

            elif self.current_layer < self.number_of_layers:
                self.current_file_name = self.features_file_names[self.current_layer - len(self.support_file_names)]
                self.current_thickness = self.features_thickness
                burning_layers_threshold = len(self.support_file_names) + self.features_burn_layers
                is_burning_layer = self.current_layer < burning_layers_threshold

                if is_burning_layer:
                    self.current_amplitude = self.features_burn_amplitude
                    self.current_exposure = self.features_burn_exposure
                elif self.incremental_exposure:
                    if self.fixed_layer and self.current_layer > burning_layers_threshold:
                        move_building_plate = False
                    self.current_amplitude = self.features_amplitude
                    self.current_exposure = self.starting_incremental_exposure + \
                                        (self.current_layer - burning_layers_threshold) * self.incremental_step_exposure
                elif self.incremental_thickness:
                    self.current_thickness = self.starting_incremental_thickness + \
                                         (self.current_layer - burning_layers_threshold) * self.incremental_step_thickness
                    self.current_amplitude = self.features_amplitude
                    self.current_exposure = self.features_exposure
                elif self.incremental_amplitude:
                    if self.fixed_layer and self.current_layer > burning_layers_threshold:
                        move_building_plate = False
                    self.current_amplitude = self.starting_incremental_amplitude + \
                                         (self.current_layer - burning_layers_threshold) * self.incremental_step_amplitude
                    print(self.current_amplitude)
                    self.current_exposure = self.features_exposure
                else:
                    self.current_amplitude = self.features_amplitude
                    self.current_exposure = self.features_exposure
            else:
                self.print_text_signal.emit("...printing process ended!")
                self.print_status = "SUCCESS"
                self.save_current_parameters()
                if not DEBUG_MODE_ON:
                    self.__motor_controller.home_building_plate()
                self.is_printing = False
                self.reactivate_parameters_signal.emit()
                return
            # self.print_text_signal.emit("Preparing next layer")

            if move_building_plate:
                if DEBUG_MODE_ON:
                    self.__motor_controller.reposition_next_layer(0)
                else:
                    self.__motor_controller.reposition_next_layer(self.current_thickness)
            else:
                self.project_next_layer()
        except Exception as e:
            self.print_status = "FAILED"
            self.error_message = str(e)
            self.save_current_parameters()
            self.print_text_signal.emit("PRINTING PROCESS FAILED!")
            self.stop_printing_process(save_parameters=False)
            print(e)


    @Slot()
    def project_next_layer(self):
        self.print_text_signal.emit("Printing layer "
                                    + str(self.current_layer + 1) + " of " + str(self.number_of_layers))
        if not DEBUG_MODE_ON:
            if not self.__projector_controller.set_amplitude(self.current_amplitude):
                self.stop_printing_process()
                return
        self.__projector_controller.show_image(self.current_file_name, self.grayscale_correction, self.grayscale_alpha, self.grayscale_beta, self.grayscale_gamma)
        self.current_layer = self.current_layer + 1
        self.next_layer_timer.setInterval(self.current_exposure)
        self.next_layer_timer.start()

    def __print_current_parameters__(self):
        self.print_text_signal.emit("Current Thickness " + str(self.current_thickness*1000) + str(' \u03BCm'))
        self.print_text_signal.emit("Current Exposure Time " + str(self.current_exposure) + " ms")
        self.print_text_signal.emit("Current Amplitude " + str(self.current_amplitude))

    def __print_support_parameters__(self):
        self.print_text_signal.emit("Support Thickness " + str(self.support_thickness))
        self.print_text_signal.emit("Support Exposure Time " + str(self.support_exposure))
        self.print_text_signal.emit("Support Amplitude " + str(self.support_amplitude))
        self.print_text_signal.emit("Support Burning Layers " + str(self.support_burn_layers))
        self.print_text_signal.emit("Support Burning Exposure Time " + str(self.support_burn_exposure))
        self.print_text_signal.emit("Support Burning Amplitude " + str(self.support_burn_amplitude))

    def __print_features_parameters__(self):
        self.print_text_signal.emit("Features Thickness " + str(self.features_thickness))
        self.print_text_signal.emit("Features Exposure Time " + str(self.features_exposure))
        self.print_text_signal.emit("Features Amplitude " + str(self.features_amplitude))
        self.print_text_signal.emit("Features Burning Layers " + str(self.features_burn_layers))
        self.print_text_signal.emit("Features Burning Exposure Time " + str(self.features_burn_exposure))
        self.print_text_signal.emit("Features Burning Amplitude " + str(self.features_burn_amplitude))

    @Slot(float)
    def set_support_thickness(self, thickness):
        self.support_thickness = thickness / 1000.0
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(float)
    def set_support_exposure_time(self, exposure):
        self.support_exposure = exposure
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(int)
    def set_support_amplitude(self, amplitude):
        self.support_amplitude = amplitude
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(int)
    def set_support_burning_layers(self, layers):
        self.support_burn_layers = layers
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(float)
    def set_support_burning_exposure_time(self, exposure):
        self.support_burn_exposure = exposure
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(int)
    def set_support_burning_amplitude(self, amplitude):
        self.support_burn_amplitude = amplitude
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(str)
    def set_support_images(self, images):
        self.support_file_names = images
        for im in images:
            self.print_text_signal.emit(im)
        self.print_text_signal.emit("Loaded " + str(len(images)) + " support images!")
        self.number_of_layers = len(self.features_file_names) + len(self.support_file_names)
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(float)
    def set_features_thickness(self, thickness):
        self.features_thickness = thickness / 1000.0
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(float)
    def set_features_exposure_time(self, exposure):
        self.features_exposure = exposure
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(int)
    def set_features_amplitude(self, amplitude):
        self.features_amplitude = amplitude
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(int)
    def set_features_burning_layers(self, layers):
        self.features_burn_layers = layers
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(float)
    def set_features_burning_exposure_time(self, exposure):
        self.features_burn_exposure = exposure
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(int)
    def set_features_burning_amplitude(self, amplitude):
        self.features_burn_amplitude = amplitude
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(str)
    def set_features_images(self, images):
        self.features_file_names = images
        for im in images:
            self.print_text_signal.emit(im)
        self.print_text_signal.emit("Loaded " + str(len(images)) + " features images!")
        self.number_of_layers = len(self.features_file_names) + len(self.support_file_names)
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(bool)
    def set_incremental_amplitude(self, value):
        self.incremental_amplitude = value
        self.print_text_signal.emit("Incremental Amplitude set to: " + str(value))
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(bool)
    def set_incremental_thickness(self, value):
        self.incremental_thickness = value
        self.print_text_signal.emit("Incremental Thickness set to: " + str(value))
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(bool)
    def set_incremental_exposure(self, value):
        self.incremental_exposure = value
        self.print_text_signal.emit("Incremental Exposure set to: " + str(value))
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(bool)
    def set_fixed_layer(self, value):
        self.fixed_layer = value
        self.print_text_signal.emit("Fixed Layer set to: " + str(value))
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(bool)
    def set_grayscale_correction(self, value):
        self.grayscale_correction = value
        self.print_text_signal.emit("Grayscale Correction set to: " + str(value))
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(float)
    def set_starting_incremental_thickness(self, thickness):
        self.starting_incremental_thickness = thickness / 1000.0
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(float)
    def set_incremental_step_thickness(self, step):
        self.incremental_step_thickness = step / 1000.0
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(float)
    def set_starting_incremental_exposure(self, exposure):
        self.starting_incremental_exposure = exposure
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(float)
    def set_incremental_step_exposure(self, step):
        self.incremental_step_exposure = step
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(int)
    def set_starting_incremental_amplitude(self, amplitude):
        self.starting_incremental_amplitude = amplitude
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(int)
    def set_incremental_step_amplitude(self, step):
        self.incremental_step_amplitude = step
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(int)
    def set_grayscale_alpha(self, a):
        self.grayscale_alpha = a
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(int)
    def set_grayscale_beta(self, b):
        self.grayscale_beta = b
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(int)
    def set_grayscale_gamma(self, c):
        self.grayscale_gamma = c
        self.etc_updated_signal.emit(self.evaluate_time_estimate())

    @Slot(str)
    def print_to_console(self, text):
        self.print_text_signal.emit(text)

    @Slot()
    def available_ports(self):
        return self.__motor_controller.get_port_list()

    @Slot(int)
    def select_port(self, idx):
        self.__motor_controller.select_port(idx)

    @Slot()
    def update_port_list(self):
        self.__motor_controller.update_port_list()

    @Slot()
    def reset_printer(self):
        self.__motor_controller.reset_printer()

    @Slot()
    def connect_printer(self):
        self.__motor_controller.connect_printer()

    @Slot()
    def disconnect_printer(self):
        self.__motor_controller.disconnect_printer()

    @Slot(float)
    def update_building_plate_distance(self, dist):
        self.__motor_controller.update_manual_plate_distance(dist)

    @Slot()
    def move_building_plate(self):
        self.__motor_controller.move_building_plate()

    @Slot()
    def set_building_plate_origin(self):
        self.__motor_controller.set_origin()

    @Slot()
    def home_building_plate(self):
        self.__motor_controller.home_building_plate()

    @Slot()
    def move_building_plate_to_origin(self):
        self.__motor_controller.move_plate_to_origin()

    @Slot()
    def home_projector(self):
        self.__motor_controller.home_projector()

    @Slot(float)
    def update_projector_distance(self, dist):
        self.__motor_controller.update_manual_projector_distance(dist)

    @Slot()
    def move_projector(self):
        self.__motor_controller.move_projector()

    @Slot()
    def lock_unlock_projector(self):
        self.__motor_controller.lock_projector()

    @Slot()
    def start_projector(self):
        self.__projector_controller.init_projector()

    @Slot(QPixmap)
    def display_image_preview(self, image):
        self.display_image_signal.emit(image)

    @Slot()
    def project_calibration_pattern(self):
        self.__projector_controller.project_pattern()

    @Slot()
    def set_projector_amplitude(self):
        result = self.__projector_controller.set_amplitude(self.projector_amplitude)
        if result:
            self.print_text_signal.emit("Projector amplitude set to: " + str(self.projector_amplitude))

    @Slot(int)
    def update_projector_amplitude(self, amplitude):
        self.projector_amplitude = amplitude

    @Slot(bool)
    def set_horizontal_mirroring(self, state):
        self.__projector_controller.horizontal_mirror = state
        self.print_text_signal.emit("Horizontal Mirroring set to: " + str(state))

    @Slot(bool)
    def set_vertical_mirroring(self, state):
        self.__projector_controller.vertical_mirror = state
        self.print_text_signal.emit("Vertical Mirroring set to: " + str(state))

    @Slot()
    def is_horizontal_mirrored(self):
        return self.__projector_controller.horizontal_mirror

    @Slot()
    def is_vertical_mirrored(self):
        return self.__projector_controller.vertical_mirror

    @Slot()
    def close_projector(self):
        self.disconnect_printer()
        self.projector_amplitude = 0
        self.set_projector_amplitude()
        self.__projector_controller.stop_projector()
        self.__projector_controller.close()

    def get_step_length_microns(self):
        return self.__motor_controller.get_motor_step_length_microns()

    @Slot()
    def print_motor_position(self):
        self.__motor_controller.print_motor_position()

    @Slot()
    def evaluate_time_estimate(self, current_layer=0):
        support_burn_layers_left = max(0, min(len(self.support_file_names), self.support_burn_layers) - current_layer)
        support_layer_left = max(0, len(self.support_file_names) - max(current_layer, self.support_burn_layers))
        features_burn_layers_left = max(0, min(len(self.features_file_names), len(self.support_file_names) + self.features_burn_layers - max(current_layer, len(self.support_file_names))))
        features_layer_left = max(0, self.number_of_layers - max(current_layer, len(self.support_file_names) + self.features_burn_layers))
        # support_layers = len(self.support_file_names) - self.support_burn_layers
        # support_layers = support_layers - (current_layer)
        rep_offset = self.__motor_controller.repositioning_offset
        feed_rate = self.__motor_controller.feed_rate
        rep_delay = self.__motor_controller.repositioning_delay
        up_delay_ms = abs(rep_offset)/feed_rate * 60 * 1000
        support_down_delay_ms = abs(rep_offset - self.support_thickness)/feed_rate * 60 * 1000
        features_down_delay_ms = abs(rep_offset - self.features_thickness)/feed_rate * 60 * 1000
        support_burn_time_ms = support_burn_layers_left * (self.support_burn_exposure + rep_delay
                                                           + up_delay_ms + support_down_delay_ms)
        support_time_ms = support_layer_left * (self.support_exposure + rep_delay + up_delay_ms + support_down_delay_ms)
        features_burn_time_ms = features_burn_layers_left * (self.features_burn_exposure + rep_delay + up_delay_ms +
                                                             features_down_delay_ms)

        features_layers = len(self.features_file_names) - self.features_burn_layers
        if not (self.incremental_amplitude or self.incremental_exposure or self.incremental_thickness):
            features_time_ms = features_layer_left * (self.features_exposure + rep_delay + up_delay_ms + features_down_delay_ms)
        elif self.fixed_layer:
            tot_repositioning_time = (rep_delay + up_delay_ms + features_down_delay_ms) * (features_layers - features_layer_left == 0)
            tot_exposure_time = 0
            if self.incremental_exposure:
                for idx in range(features_layers - features_layer_left, features_layers):
                    tot_exposure_time += self.starting_incremental_exposure + self.incremental_step_exposure * idx
            else:
                tot_exposure_time += features_layer_left * self.features_exposure
            features_time_ms = tot_exposure_time + tot_repositioning_time
        else:
            tot_repositioning_time = features_layer_left * (rep_delay + up_delay_ms + features_down_delay_ms)
            tot_exposure_time = features_layer_left * self.features_exposure
            if self.incremental_exposure:
                tot_exposure_time = 0
                for idx in range(features_layers - features_layer_left, features_layers):
                    tot_exposure_time += self.starting_incremental_exposure + self.incremental_step_exposure * idx
            if self.incremental_thickness:
                tot_repositioning_time = features_layer_left * (rep_delay + up_delay_ms)
                for idx in range(features_layers - features_layer_left, features_layers):
                    layer_thickness = self.starting_incremental_thickness + idx * self.incremental_step_thickness
                    tot_repositioning_time += abs(rep_offset - layer_thickness)/feed_rate * 60 * 1000

            features_time_ms = tot_exposure_time + tot_repositioning_time

        time_estimate = support_burn_time_ms + support_time_ms + features_burn_time_ms + features_time_ms
        return time_estimate

    @Slot(str)
    def set_username(self, username):
        self.username = username

    @Slot(str)
    def set_printjob_name(self, print_job_name):
        self.print_job_name = print_job_name

    def __load_default_parameters__(self):
        self.__default_parameters = {
            'printer_setup': self.printer_setup,
            'projector_setup': self.projector_setup,
            'motor_setup': self.motor_setup,
            'support_thickness (mm)': 0.018,  # mm
            'support_exposure (ms)': 3000,  # ms
            'support_amplitude': 230,
            'support_burn_layers': 5,
            'support_burn_exposure (ms)': 15000,  # ms
            'support_burn_amplitude': 500,
            # Features Parameters
            'features_thickness (mm)': 0.018,  # mm
            'features_exposure (ms)': 3000,  # ms
            'features_amplitude': 230,
            'features_burn_layers': 0,
            'features_burn_exposure (ms)': 15000,  # ms
            'features_burn_amplitude': 500,
            # Advanced Parameters
            'incremental_thickness': False,
            'incremental_exposure': False,
            'incremental_amplitude': False,
            'starting_incremental_thickness (mm)': 0.001,  # mm
            'incremental_step_thickness (mm)': 0.001,  # mm
            'starting_incremental_exposure (ms)': 1000,  # ms
            'incremental_step_exposure (ms)': 100,  # ms
            'starting_incremental_amplitude': 10,
            'incremental_step_amplitude': 10,
            'fixed_layer': False,
            'grayscale_correction': False,
            'grayscale_alpha': 0,
            'grayscale_beta': 0,
            'grayscale_gamma': 0,
            # Others
            'projector_amplitude': 0,
            'horizontal_mirror': True,
            'vertical_mirror': False,
            'repositioning_delay (ms)': 500,  # ms
            'feed_rate (mm/min)': 300,  # mm/min
            'spindle_pitch_microns': 4000,
            'motor_steps_per_revolution': 6400,
            'projector_feed_rate (mm/min)': 300,
            'repositioning_offset (mm)': 5,  # mm
            'projector_pixel_size (mm)': 0.00754,  # mm
            'projector_width': 2560,
            'projector_height': 1600,
            'samples_per_pixel': 1
        }
        base_path = Path(__file__).parent
        settings_path = str((base_path / '../resources/PRINTER_SETTINGS.json').resolve())
        settings_file = QFile(settings_path)
        if settings_file.open(QIODevice.ReadOnly | QIODevice.Text):
            file_data = QJsonDocument.fromJson(settings_file.readAll()).object()
            if "dlp_settings" in file_data:
                for key, value in self.__default_parameters.items():
                    if key in file_data["dlp_settings"]:
                        new_value = file_data["dlp_settings"][key]
                        self.__default_parameters[key] = new_value
            settings_file.close()

    @Slot()
    def save_default_parameters(self):
        base_path = Path(__file__).parent
        settings_path = str((base_path / '../resources/PRINTER_SETTINGS.json').resolve())
        settings_file = QFile(settings_path)
        file_data = {}
        if settings_file.open(QIODevice.ReadOnly | QIODevice.Text):
            file_data = QJsonDocument.fromJson(settings_file.readAll()).object()
            settings_file.close()
        if settings_file.open(QIODevice.ReadWrite | QIODevice.Text | QIODevice.Truncate):
            file_data["printer_type"] = "DLP"
            file_data["dlp_settings"] = self.__default_parameters
            settings_file.write(QJsonDocument(file_data).toJson())
            settings_file.close()

    def get_default_parameters(self):
        return self.__default_parameters

    @Slot()
    def set_default_parameter(self, key, value):
        self.__default_parameters[key] = value

    @Slot()
    def save_current_parameters(self):
        current_parameters = {
            'printer_setup': self.printer_setup,
            'projector_setup': self.projector_setup,
            'motor_setup': self.motor_setup,
            # Support Parameters
            'support_thickness (mm)': self.support_thickness,  # mm
            'support_exposure (ms)': self.support_exposure,  # ms
            'support_amplitude': self.support_amplitude,
            'support_burn_layers': self.support_burn_layers,
            'support_burn_exposure (ms)': self.support_burn_exposure,  # ms
            'support_burn_amplitude': self.support_burn_amplitude,
            # Features Parameters
            'features_thickness (mm)': self.features_thickness,  # mm
            'features_exposure (ms)': self.features_exposure,  # ms
            'features_amplitude': self.features_amplitude,
            'features_burn_layers': self.features_burn_layers,
            'features_burn_exposure (ms)': self.features_burn_exposure,  # ms
            'features_burn_amplitude': self.features_burn_amplitude,
            # Advanced Parameters
            'incremental_thickness': self.incremental_thickness,
            'incremental_exposure': self.incremental_exposure,
            'incremental_amplitude': self.incremental_amplitude,
            'starting_incremental_thickness (mm)': self.starting_incremental_thickness,  # mm
            'incremental_step_thickness (mm)': self.incremental_step_thickness,  # mm
            'starting_incremental_exposure (ms)': self.starting_incremental_exposure,  # ms
            'incremental_step_exposure (ms)': self.incremental_step_exposure,  # ms
            'starting_incremental_amplitude': self.starting_incremental_amplitude,
            'incremental_step_amplitude': self.incremental_step_amplitude,
            'fixed_layer': self.fixed_layer,
            'grayscale_correction': self.grayscale_correction,
            'grayscale_alpha': self.grayscale_alpha,
            'grayscale_beta': self.grayscale_beta,
            'grayscale_gamma': self.grayscale_gamma,
            # Others
            'projector_amplitude': self.projector_amplitude,
            'feed_rate (mm/min)': self.__motor_controller.feed_rate,  # mm/min
            'spindle_pitch_microns': self.spindle_pitch_microns,
            'motor_steps_per_revolution': self.motor_steps_per_revolution,
            'projector_feed_rate (mm/min)': self.__motor_controller.projector_feed_rate,
            'repositioning_delay (ms)': self.__motor_controller.repositioning_delay,  # ms
            'repositioning_offset (mm)': self.__motor_controller.repositioning_offset,  # mm
            'projector_pixel_size (mm)': self.projector_pixel_size,  # mm
            'projector_width': self.projector_width,
            'projector_height': self.projector_height,
            'horizontal_mirror': self.__projector_controller.horizontal_mirror,
            'vertical_mirror': self.__projector_controller.vertical_mirror,
            'samples_per_pixel': self.samples_per_pixel
        }
        base_path = Path(__file__).parent
        log_path = str((base_path / '../resources/PRINT_LOG.json').resolve())
        log_file = QFile(log_path)
        file_data = {}
        # if log_file.open(QIODevice.ReadOnly | QIODevice.Text):
        #     file_data = QJsonDocument.fromJson(log_file.readAll()).object()
        #     log_file.close()
        if log_file.open(QIODevice.ReadWrite | QIODevice.Append):
            # Print Job Parameters
            file_data['date (yyyy.MM.dd)'] = self.printing_date
            file_data['time (hh.mm.ss)'] = self.printing_time
            file_data['username'] = self.username
            file_data['print_job_name'] = self.print_job_name
            file_data['print_job_status'] = self.print_status
            file_data['total_layers'] = self.number_of_layers
            file_data['support_layers'] = len(self.support_file_names)
            file_data['features_layers'] = len(self.features_file_names)
            file_data['printed_layers'] = self.current_layer
            file_data["printer_type"] = "DLP"
            if self.print_status == "FAILED":
                file_data["error_message"] = self.error_message
            file_data["dlp_settings"] = current_parameters
            log_file.write(QJsonDocument(file_data).toJson())
            log_file.close()
