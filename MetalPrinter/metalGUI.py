from PySide2.QtWidgets import QSizePolicy, QHBoxLayout, QPushButton, QWidget, QStackedLayout, QTabWidget, \
    QDesktopWidget, QGroupBox, QVBoxLayout
from PySide2.QtGui import QCloseEvent
from PySide2.QtCore import Signal, Slot, QFile, QIODevice, QJsonDocument
from pathlib import Path
from MetalPrinter.metalSlicerGUI import MetalSlicerGUI
from MetalPrinter.gCodeSenderGUI import GCodeSenderGUI


class MetalGUI(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.parent = parent
        self.supported_setups = ['TOP-DOWN']
        self.stacked_layout = QStackedLayout()
        self.__setup_widget = None
        self.__metal_main_widget = None
        self.__init_main_widget__()
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
            if "metal_printer_settings" in file_data:
                printer_setup = str(file_data["metal_printer_settings"]["printer_setup"])
                if printer_setup == self.supported_setups[0]:
                    self.__select_setup__(0)
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

    def __select_setup__(self, idx):
        self.selected_setup = self.supported_setups[idx]
        self.__init_main_widget__()
        self.stacked_layout.setCurrentIndex(1)
        self.parent.move(self.desktops.screen(0).rect().center() - self.__metal_main_widget.rect().center())

    def __init_main_widget__(self):
        self.__metal_main_widget = QTabWidget(self)
        self.__metal_main_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.__gcode_sender_widget = GCodeSenderGUI(parent=self.__metal_main_widget)
        self.__slicer_widget = MetalSlicerGUI(parent=self.__metal_main_widget)
        self.__slicer_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.__metal_main_widget.addTab(self.__gcode_sender_widget, 'GCode Sender')
        self.__metal_main_widget.addTab(self.__slicer_widget, 'Slicer')
        self.stacked_layout.addWidget(self.__metal_main_widget)
        self.desktops = QDesktopWidget()

    @Slot()
    def closeEvent(self, event: QCloseEvent):
        if self.__setup_widget:
            self.__setup_widget.close()
        if self.__metal_main_widget:
            self.__slicer_widget.close()
            self.__metal_main_widget.close()
        event.accept()

    def get_settings_window(self, parent=None):
        printer_settings = QGroupBox("Metal Printer Settings:", parent)
        gcodesender_settings = self.__gcode_sender_widget.get_settings_window(printer_settings)
        settings_layout = QVBoxLayout(printer_settings)
        settings_layout.addWidget(gcodesender_settings)
        return printer_settings
