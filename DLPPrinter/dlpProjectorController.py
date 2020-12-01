from PySide2.QtCore import Signal, Slot, Qt, QRunnable, QThreadPool
from PySide2.QtWidgets import QLabel, QDesktopWidget
from PySide2.QtGui import QPixmap, QTransform, QImage
import sys
from pathlib import Path
import numpy as np
from DLPPrinter.dlpColorCalibrator import DLPColorCalibrator
from DLPPrinter.projectors import visitechDLP9000

DEBUG_MODE_ON = False


class DLPProjectorController(QLabel):

    print_text_signal = Signal(str)
    display_image_signal = Signal(QPixmap)

    def __init__(self, projector_setup="VisitechDLP9000"):
        QLabel.__init__(self)
        base_path = Path(__file__).parent
        if projector_setup == 'VisitechDLP9000':
            self.projector_instance = visitechDLP9000.VisitechDLP9000()
        else:
            print("Error: an invalid projector was selected!")
            sys.exit(1)

        self.connected = False
        self.projector_instance.print_text_signal.connect(self.print_to_console)
        self.projector_instance.connection_status_signal.connect(self.set_connection_status)
        self.calibration_pattern = str((base_path / "../resources/projection_pattern.png").resolve())
        self.img = None
        self.horizontal_mirror = True
        self.vertical_mirror = False
        self.project_pattern_on = False
        self.setStyleSheet("QLabel { background-color : black}")
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.show()
        self.desktops = QDesktopWidget()
        for d in range(self.desktops.screenCount()):
            print(self.desktops.screenGeometry(d))
        if self.desktops.screenCount() > 1:
            self.projector_width = self.desktops.screenGeometry(1).width()
            self.projector_height = self.desktops.screenGeometry(1).height()
            self.move(self.desktops.screenGeometry(1).center() - self.rect().center())
            self.showFullScreen()
        else:
            self.projector_width = 600
            self.projector_height = 600
            self.setFixedSize(self.projector_width, self.projector_height)
        self.threadpool = QThreadPool()

    @Slot()
    def init_projector(self):
        worker = Worker(self.projector_instance.init_projector)
        self.threadpool.start(worker)

    def stop_projector(self):
        if self.projector_instance.stop_projector():
            self.connected = False

    def show_image(self, pattern, use_grayscale=False, alpha=0, beta=0, gamma=0):
        # if not self.connected:
        #     self.print_text_signal.emit("Impossible to show image: projector is not connected!")
        #     return
        loaded_image = QImage(pattern).convertToFormat(QImage.Format.Format_RGB32)
        values = loaded_image.bits()
        pixel_values = np.array(values).reshape(loaded_image.height(), loaded_image.width(), 4)
        if use_grayscale:
            thickness = DLPColorCalibrator.my_log_function(1,alpha,beta,gamma)
            tmp, corrected_values = DLPColorCalibrator.my_color_correction(pixel_values, alpha, beta, gamma, thickness)
            corrected_values_tr = corrected_values.copy()
            corrected_image = QImage(corrected_values_tr, corrected_values_tr.shape[1], corrected_values_tr.shape[0], QImage.Format_RGB32)
            self.img = QPixmap(corrected_image)
        else:
            self.img = QPixmap(loaded_image)
        if self.horizontal_mirror:
            self.img = self.img.transformed(QTransform().scale(-1, 1))
        if self.vertical_mirror:
            self.img = self.img.transformed(QTransform().scale(1, -1))
        self.display_image_signal.emit(self.img)
        self.setPixmap(self.img)

    def clear_image(self):
        self.img = QPixmap('')
        self.display_image_signal.emit(self.img)
        self.setPixmap(self.img)

    def project_pattern(self):
        # if not self.connected:
        #     self.print_text_signal.emit("Impossible to show image: projector is not connected!")
        #     return
        if self.project_pattern_on:
            self.project_pattern_on = not self.project_pattern_on
            self.clear_image()
        else:
            self.project_pattern_on = not self.project_pattern_on
            self.show_image(self.calibration_pattern)

    def set_amplitude(self, amplitude):
        if DEBUG_MODE_ON:
            return True
        if not self.connected:
            self.print_text_signal.emit("Impossible to set amplitude: projector is not connected!")
            return
        status = self.projector_instance.set_projector_amplitude(amplitude)
        return status

    @Slot(str)
    def print_to_console(self, text):
        self.print_text_signal.emit(text)

    @Slot(bool)
    def set_connection_status(self, status):
        self.connected = status


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

