import sys
from PySide2.QtWidgets import QMainWindow, QHBoxLayout, QPushButton, QWidget, QGridLayout, QVBoxLayout, QMenuBar, \
    QAction, QDialog, QGroupBox, QLabel, QComboBox
from PySide2.QtCore import QLocale
from PySide2.QtGui import QCloseEvent
from PySide2.QtCore import Signal, Slot, QFile, QIODevice, QJsonDocument
from DLPPrinter.dlpGUI import DLPGUI
from MetalPrinter.metalGUI import MetalGUI
from pathlib import Path


class MainGui(QMainWindow):

    def __init__(self, parent=None):
        QLocale.setDefault(QLocale.English)
        QMainWindow.__init__(self, parent)
        self.setWindowTitle("AMLab Software v1.0")
        self.supported_printers = ['DLP', 'Metal']
        self.selected_printer = self.supported_printers[0]
        self.__init_setup__()
        self.dlp_gui = None
        self.metal_gui = None
        # self.dlp_gui.hide()
        # self.metal_gui.hide()
        self.setup_widget.hide()
        self.__init_menu_bar__()
        if not self.__load_settings__():
            self.__select_setup_widget__()

    def __load_settings__(self):
        base_path = Path(__file__).parent
        settings_path = str((base_path / './resources/PRINTER_SETTINGS.json').resolve())
        settings_file = QFile(settings_path)
        if settings_file.open(QIODevice.ReadOnly | QIODevice.Text):
            file_data = QJsonDocument.fromJson(settings_file.readAll()).object()
            if "printer_type" in file_data:
                printer_type = str(file_data["printer_type"])
                if printer_type == self.supported_printers[0]:
                    self.__select_dlp__()
                elif printer_type == self.supported_printers[1]:
                    self.__select_metal__()
                else:
                    return False
                return True
            settings_file.close()
        return False

    def __init_setup__(self):
        self.setup_widget = QWidget(self)
        dlp_button = QPushButton("DLP \nPrinter", self.setup_widget)
        dlp_button.setFixedSize(200, 200)
        dlp_button.clicked.connect(self.__select_dlp__)
        metal_button = QPushButton("Metal \nPrinter", self.setup_widget)
        metal_button.setFixedSize(200, 200)
        metal_button.clicked.connect(self.__select_metal__)
        self.setup_layout = QHBoxLayout()
        self.setup_layout.addWidget(dlp_button)
        self.setup_layout.addWidget(metal_button)
        self.setup_widget.setLayout(self.setup_layout)

    def __select_setup_widget__(self):
        self.setup_widget.show()
        self.setCentralWidget(self.setup_widget)

    def __select_dlp__(self):
        self.dlp_gui = DLPGUI(self)
        self.selected_printer = self.supported_printers[0]
        self.setCentralWidget(self.dlp_gui)
        self.adjustSize()

    def __select_metal__(self):
        self.metal_gui = MetalGUI(self)
        self.selected_printer = self.supported_printers[1]
        self.setCentralWidget(self.metal_gui)
        self.adjustSize()

    @Slot()
    def closeEvent(self, event: QCloseEvent):
        try:
            self.dlp_gui.close()
        except:
            print("already deleted")
        try:
            self.metal_gui.close()
        except:
            print("already deleted")
        event.accept()

    def __init_menu_bar__(self):
        self.__menu_bar = QMenuBar(self)
        self.__init_file_menu()
        self.setMenuBar(self.__menu_bar)

    def __init_file_menu(self):
        self.file_menu = self.__menu_bar.addMenu("File")
        settings_action = QAction("Settings", self)
        settings_action.setStatusTip("Open Settings")
        settings_action.triggered.connect(self.__open_settings_window)
        self.file_menu.addAction(settings_action)

    @Slot()
    def __open_settings_window(self):
        settings_window = QDialog(self)
        settings_window.setWindowTitle("Settings")
        printer_settings = QGroupBox("Printer Settings:", settings_window)
        printer_type_label = QLabel("Printer Type:", printer_settings)
        self.printer_type_combo = QComboBox(printer_settings)
        self.printer_type_combo.addItems(self.supported_printers)
        self.printer_type_combo.setCurrentIndex(self.supported_printers.index(self.selected_printer))
        apply_button = QPushButton("Apply Changes", printer_settings)
        apply_button.clicked.connect(self.__apply_settings)
        apply_button.clicked.connect(settings_window.close)
        apply_button.setAutoDefault(False)
        printer_settings_layout = QGridLayout(printer_settings)
        printer_settings_layout.addWidget(printer_type_label, 0, 0)
        printer_settings_layout.addWidget(self.printer_type_combo, 0, 1)
        printer_settings_layout.addWidget(apply_button, 4, 1)
        if self.selected_printer is self.supported_printers[0]:
            extra_settings = self.dlp_gui.get_settings_window(settings_window)
        elif self.selected_printer is self.supported_printers[1]:
            extra_settings = self.metal_gui.get_settings_window(settings_window)
        settings_layout = QVBoxLayout(settings_window)
        settings_layout.addWidget(printer_settings)
        settings_layout.addWidget(extra_settings)
        settings_window.open()

    @Slot()
    def __apply_settings(self):
        self.selected_printer = self.supported_printers[self.printer_type_combo.currentIndex()]
        try:
            self.dlp_gui.close()
        except:
            print("already deleted")
        try:
            self.metal_gui.close()
        except:
            print("already deleted")
        if self.selected_printer is self.supported_printers[0]:
            self.__select_dlp__()
        elif self.selected_printer is self.supported_printers[1]:
            self.__select_metal__()
