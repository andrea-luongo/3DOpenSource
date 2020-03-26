import sys
from PySide2.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QPushButton, QWidget, QStackedLayout, QSizePolicy, \
    QLayout
from PySide2.QtCore import QLocale
from PySide2.QtGui import QCloseEvent
from PySide2.QtCore import Signal, Slot, QFile, QIODevice, QJsonDocument
from DLPPrinter.dlpGUI import DLPGUI
from pathlib import Path


class MainGui(QWidget):

    def __init__(self, parent=None):
        QLocale.setDefault(QLocale.English)
        QWidget.__init__(self, parent)
        self.setWindowTitle("AMLab Software v1.0")
        self.supported_printers = ['DLP', 'Metal']
        self.setup_widget = None
        self.dlp_gui = None
        self.metal_gui = None
        self.stacked_layout = QStackedLayout()
        self.main_layout = QVBoxLayout()
        self.main_layout.addLayout(self.stacked_layout)
        self.setLayout(self.main_layout)
        # self.main_layout.setSizeConstraint(QLayout.SetFixedSize)
        if not self.__load_settings__():
            self.__init_setup__()

    def minimumSizeHint(self):
        return self.stacked_layout.currentWidget().minimumSizeHint()

    def sizeHint(self):
        return self.stacked_layout.currentWidget().sizeHint()

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
        self.stacked_layout.addWidget(self.setup_widget)
        self.stacked_layout.setCurrentIndex(0)

    def __select_dlp__(self):
        self.dlp_gui = DLPGUI(self)
        self.stacked_layout.addWidget(self.dlp_gui)
        self.selected_printer = self.supported_printers[0]
        self.stacked_layout.setCurrentIndex(1)
        self.adjustSize()

    def __select_metal__(self):
        self.dlp_gui = DLPGUI(self)
        self.stacked_layout.addWidget(self.dlp_gui)
        self.selected_printer = self.supported_printers[1]
        self.stacked_layout.setCurrentIndex(2)
        self.adjustSize()
# WIDTH = 800
# HEIGHT = 600

    @Slot()
    def closeEvent(self, event: QCloseEvent):
        if self.setup_widget:
            self.setup_widget.close()
        if self.dlp_gui:
            self.dlp_gui.close()
        if self.metal_gui:
            self.metal_gui.close()
        event.accept()



def main():
    app = QApplication(sys.argv)
    main_gui = MainGui()
    main_gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

