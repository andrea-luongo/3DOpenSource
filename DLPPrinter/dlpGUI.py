from PySide2.QtWidgets import QSizePolicy, QHBoxLayout, QPushButton, QWidget, QStackedLayout, QTabWidget, QDesktopWidget
from PySide2.QtGui import QCloseEvent
from PySide2.QtCore import Signal, Slot, QFile, QIODevice, QJsonDocument
from DLPPrinter.dlpPrinterGUI import DLPPrinterGUI
from DLPPrinter.dlpSettingsGUI import DLPSettingsGUI
from DLPPrinter.dlpSlicerGUI import DLPSlicerGUI
from pathlib import Path
from DLPPrinter.dlpMainController import DLPMainController


class DLPGUI(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.parent = parent
        self.supported_setups = ['BOTTOM-UP', 'TOP-DOWN']
        self.supported_projectors = ['VisitechDLP9000']
        self.supported_motors = ['ClearpathSDSK']
        self.stacked_layout = QStackedLayout()
        self.__setup_widget = None
        self.__dlp_main_widget = None
        if not self.__load_settings__():
            self.__init_configuration_selection_widget__()
            self.__init_projector_selection_widget__()
            self.__init_motor_selection_widget__()
            self.stacked_layout.setCurrentIndex(0)
        self.setLayout(self.stacked_layout)

    def minimumSizeHint(self):
        return self.stacked_layout.currentWidget().minimumSizeHint()

    def sizeHint(self):
        return self.stacked_layout.currentWidget().sizeHint()

    def __load_settings__(self):
        base_path = Path(__file__).parent
        settings_path = str((base_path / '../resources/PRINTER_SETTINGS.json').resolve())
        settings_file = QFile(settings_path)
        if settings_file.open(QIODevice.ReadOnly | QIODevice.Text):
            file_data = QJsonDocument.fromJson(settings_file.readAll()).object()
            if "dlp_settings" in file_data:
                printer_setup = str(file_data["dlp_settings"]["printer_setup"])
                if printer_setup == self.supported_setups[0]:
                    self.__select_setup__(0)
                elif printer_setup == self.supported_setups[1]:
                    self.__select_setup__(1)
                else:
                    return False
                projector_setup = str(file_data["dlp_settings"]["projector_setup"])
                if projector_setup == self.supported_projectors[0]:
                    self.__select_projector__(None, 0)
                elif projector_setup == self.supported_projectors[1]:
                    self.__select_projector__(None, 1)
                else:
                    return False
                motor_setup = str(file_data["dlp_settings"]["motor_setup"])
                if motor_setup == self.supported_motors[0]:
                    self.__select_motor__(None, 0)
                elif motor_setup == self.supported_motors[1]:
                    self.__select_motor__(None, 1)
                else:
                    return False
                return True
            settings_file.close()
        return False

    def __init_configuration_selection_widget__(self):
        self.__setup_widget = QWidget(self)
        setup_layout = QHBoxLayout()
        for idx in range(len(self.supported_setups)):
            button = QPushButton(self.supported_setups[idx], self.__setup_widget)
            button.setFixedSize(200, 200)
            button.clicked.connect(self.__select_setup__)
            setup_layout.addWidget(button)
        self.__setup_widget.setLayout(setup_layout)
        self.stacked_layout.addWidget(self.__setup_widget)
        # self.stacked_layout.setCurrentIndex(0)

    def __init_projector_selection_widget__(self):
        self.__projector_setup_widget = QWidget(self)
        projector_setup_layout = QHBoxLayout()
        for idx in range(len(self.supported_projectors)):
            button = QPushButton(self.supported_projectors[idx], self.__setup_widget)
            button.setFixedSize(200, 200)
            button.clicked.connect(lambda state=None, x=idx: self.__select_projector__(state, x))
            projector_setup_layout.addWidget(button)
        self.__projector_setup_widget.setLayout(projector_setup_layout)
        self.stacked_layout.addWidget(self.__projector_setup_widget)

    def __init_motor_selection_widget__(self):
        self.__motor_setup_widget = QWidget(self)
        motor_setup_layout = QHBoxLayout()
        for idx in range(len(self.supported_motors)):
            button = QPushButton(self.supported_motors[idx], self.__setup_widget)
            button.setFixedSize(200, 200)
            button.clicked.connect(lambda state=None, x=idx: self.__select_motor__(state, x))
            motor_setup_layout.addWidget(button)
        self.__motor_setup_widget.setLayout(motor_setup_layout)
        self.stacked_layout.addWidget(self.__motor_setup_widget)

    def __select_setup__(self, idx):
        self.selected_setup = self.supported_setups[idx]
        self.stacked_layout.setCurrentIndex(1)

    def __select_projector__(self, button_state, projector_id):
        self.selected_projector = self.supported_projectors[projector_id]
        self.stacked_layout.setCurrentIndex(2)

    def __select_motor__(self, button_state, motor_id):
        self.selected_motor = self.supported_motors[motor_id]
        self.__init_main_widget__()
        self.stacked_layout.setCurrentIndex(3)
        self.parent.move(self.desktops.screen(0).rect().center() - self.__dlp_main_widget.rect().center())

    def __init_main_widget__(self):
        self.__dlp_main_widget = QTabWidget(self)
        self.__dlp_main_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.dlp_controller = DLPMainController(self.selected_setup, self.selected_projector, self.selected_motor)
        self.__printer_widget = DLPPrinterGUI(dlp_controller=self.dlp_controller, parent=self.__dlp_main_widget)
        self.__slicer_widget = DLPSlicerGUI(dlp_controller=self.dlp_controller, parent=self.__dlp_main_widget)
        self.__settings_widget = DLPSettingsGUI(dlp_controller=self.dlp_controller, parent=self.__dlp_main_widget)
        self.__printer_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.__slicer_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.__settings_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.__dlp_main_widget.addTab(self.__printer_widget, 'DLP')
        self.__dlp_main_widget.addTab(self.__slicer_widget, 'Slicer')
        self.__dlp_main_widget.addTab(self.__settings_widget, 'Advanced Settings')
        self.stacked_layout.addWidget(self.__dlp_main_widget)
        # self.__dlp_main_widget.move()
        self.desktops = QDesktopWidget()
        # self.parent.move(self.desktops.screen(0).rect().center() - self.__dlp_main_widget.rect().center())
        # self.__dlp_main_widget.move(QGuiApplication.desktop().screen().rect().center() - self.rect().center())

    @Slot()
    def closeEvent(self, event: QCloseEvent):
        if self.__setup_widget:
            self.__setup_widget.close()
        if self.__dlp_main_widget:
            self.__printer_widget.close()
            self.__slicer_widget.close()
            self.__settings_widget.close()
            self.__dlp_main_widget.close()
        event.accept()
