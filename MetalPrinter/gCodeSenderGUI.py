from PySide2.QtWidgets import QProgressBar, QSizePolicy, QPushButton, QWidget, QLabel, QComboBox, QLineEdit, \
    QGridLayout, QVBoxLayout, QPlainTextEdit, QFileDialog, QGroupBox, QDoubleSpinBox
from PySide2.QtGui import QPalette, QColor
from PySide2.QtCore import Signal, Slot, QLocale
from MetalPrinter.gCodeSender import GCodeSender


class MyQComboBox(QComboBox):
    combo_box_clicked = Signal()
    @Slot()
    def showPopup(self):
        self.combo_box_clicked.emit()
        super(MyQComboBox, self).showPopup()


class GCodeSenderGUI(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        QLocale.setDefault(QLocale.English)
        self.__central_widget = None
        self.__menu_bar = None
        self.__status_bar = None
        self.__g_code_sender = GCodeSender()
        self.__init_central_widget()
        # self.__init_menu_bar_widget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.__central_widget)
        # self.setCentralWidget(self.__central_widget)
        # self.setMenuBar(self.__menu_bar)
        # self.setWindowTitle("MyGCodeSender")

    def __init_central_widget(self):
        self.__central_widget = QWidget(self)
        central_layout = QGridLayout(self.__central_widget)

        self.__init_right_column_widget(self.__central_widget)
        central_layout.addWidget(self.__right_column_widget, 0, 2, 1, 1)
        self.__init_console_widget(self.__central_widget)
        central_layout.addWidget(self.__console_widget, 0, 0, 1, 2)
        self.__init_bottom_widget(self.__central_widget)
        central_layout.addWidget(self.__bottom_widget, 1, 0, 1, 3)
        self.__right_column_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        # self.__console_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        # self.__bottom_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

    def __init_console_widget(self, parent=None):
        self.__console_widget = QPlainTextEdit(parent)
        self.__console_widget.setReadOnly(True)
        self.__console_widget.setStyleSheet("QPlainTextEdit { background-color : dimgrey}")
        palette = self.__console_widget.palette()
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        self.__console_widget.setPalette(palette)
        self.__g_code_sender.print_text_signal.connect(self.__console_widget.appendPlainText)

    def __init_bottom_widget(self, parent=None):
        self.__bottom_widget = QWidget(parent)
        send_button = QPushButton("Send", self.__bottom_widget)
        send_button.setObjectName("send_button")
        send_button.clicked.connect(self.__send_single_command)
        start_button = QPushButton("Start", self.__bottom_widget)
        start_button.setObjectName("start_button")
        start_button.clicked.connect(self.__g_code_sender.start)
        load_gcode_button = QPushButton("Load Gcode", self.__bottom_widget)
        load_gcode_button.setObjectName("load_gcode_button")
        load_gcode_button.clicked.connect(self.__load_gcode_file)
        self.__line_sender_edit = QLineEdit(self.__bottom_widget)
        self.__line_sender_edit.setObjectName("line_sender_edit")
        self.__line_sender_edit.setPlaceholderText("Send Manual Gcode")
        self.__line_sender_edit.returnPressed.connect(self.__send_single_command)
        self.__progress_bar = QProgressBar(self.__bottom_widget)
        self.__progress_bar.setProperty("value", 0)
        self.__progress_bar.setObjectName("progress_bar")
        self.__progress_bar.setRange(0, 100)
        self.__g_code_sender.percentage_progress_signal.connect(self.__progress_bar.setValue)
        # defining bottom layout
        bottom_layout = QGridLayout(self.__bottom_widget)
        bottom_layout.addWidget(self.__line_sender_edit, 0, 0, 1, 1)
        bottom_layout.addWidget(send_button, 0, 1, 1, 1)
        bottom_layout.addWidget(load_gcode_button, 0, 2, 1, 1)
        bottom_layout.addWidget(start_button, 0, 3, 1, 1)
        bottom_layout.addWidget(self.__progress_bar, 1, 0, 1, 4)

    def __init_right_column_widget(self, parent=None):
        self.__right_column_widget = QWidget(parent)
        port_label = QLabel("Port Number", self.__right_column_widget)
        port_label.setObjectName("port_label")
        self.__port_combo_box = MyQComboBox(self.__right_column_widget)
        self.__port_combo_box.setObjectName("port_combo_box")
        self.__port_combo_box.addItems(self.__g_code_sender.get_ports_list())
        self.__port_combo_box.currentIndexChanged.connect(self.__g_code_sender.set_comport)
        self.__port_combo_box.combo_box_clicked.connect(self.__update_ports_list)

        baudrate_label = QLabel("Baudrate", self.__right_column_widget)
        baudrate_combo_box = QComboBox(self.__right_column_widget)
        baudrate_combo_box.setObjectName("baudrate_combo_box")
        baudrate_combo_box.addItems([str(i) for i in self.__g_code_sender.get_baudrates_list()])
        baudrate_combo_box.currentIndexChanged.connect(self.__g_code_sender.set_baudrate)

        connect_button = QPushButton("Connect GLAMS", self.__right_column_widget)
        connect_button.setObjectName("connect_button")
        connect_button.clicked.connect(self.__g_code_sender.connect_serial)
        disconnect_button = QPushButton("Disconnect GLAMS", self.__right_column_widget)
        disconnect_button.setObjectName("disconnect_button")
        disconnect_button.clicked.connect(self.__g_code_sender.disconnect)
        motor_connect_button = QPushButton("Connect Motor", self.__right_column_widget)
        motor_connect_button.setObjectName("motor_connect_button")
        motor_connect_button.clicked.connect(self.__g_code_sender.motor_connect)
        home_motors_button = QPushButton("Home Motors", self.__right_column_widget)
        home_motors_button.setObjectName("home_motors_button")
        home_motors_button.clicked.connect(self.__g_code_sender.home_motors)
        stop_button = QPushButton("STOP", self.__right_column_widget)
        stop_button.setObjectName("stop_button")
        stop_button.clicked.connect(self.__g_code_sender.emergency_stop)
        stop_button.setStyleSheet("QPushButton {background-color: red; border-style: outset; border-width: 6px; "
                                  "border-radius: 10px; border-color: beige; font: bold 20px; padding: 10px;}")
        pause_button = QPushButton("Pause", self.__right_column_widget)
        pause_button.setObjectName("pause_button")
        pause_button.clicked.connect(self.__g_code_sender.pause)

        right_column_layout = QVBoxLayout(self.__right_column_widget)
        right_column_layout.addWidget(stop_button)
        right_column_layout.addWidget(port_label)
        right_column_layout.addWidget(self.__port_combo_box)
        right_column_layout.addWidget(baudrate_label)
        right_column_layout.addWidget(baudrate_combo_box)
        right_column_layout.addWidget(connect_button)
        right_column_layout.addWidget(disconnect_button)
        right_column_layout.addWidget(motor_connect_button)
        right_column_layout.addWidget(home_motors_button)
        right_column_layout.addWidget(pause_button)

    @Slot()
    def __send_single_command(self):
        command = self.__line_sender_edit.text()
        self.__g_code_sender.execute_gcode_command(command)

    @Slot()
    def __load_gcode_file(self):
        file_path = QFileDialog.getOpenFileName(caption='Select GCode File', dir='../',
                                                  filter="GCode Files (*.g)")
        file_path = file_path[0]
        self.__g_code_sender.open_file(file_path)

    @Slot()
    def __update_ports_list(self):
        self.__g_code_sender.update_port_list()
        current_idx = self.__port_combo_box.currentIndex()
        self.__port_combo_box.blockSignals(True)
        self.__port_combo_box.clear()
        self.__port_combo_box.addItems(self.__g_code_sender.get_ports_list())
        self.__port_combo_box.blockSignals(False)
        self.__port_combo_box.setCurrentIndex(current_idx)

    def get_settings_window(self, parent=None):
        gcodesender_settings = QGroupBox("GCodeSender Settings:", parent)
        buildplate_label = QLabel("Buildplate Motor:", gcodesender_settings)
        nodes = [str(item) for item in self.__g_code_sender.get_motor_nodes_id_list()]
        self.buildplate_combo_box = MyQComboBox(gcodesender_settings)
        self.buildplate_combo_box.addItems(nodes)
        self.buildplate_combo_box.setCurrentIndex(self.__g_code_sender.get_buildplate_node())
        self.buildplate_combo_box.combo_box_clicked.connect(self.__update_nodes_list)
        self.buildplate_combo_box.currentIndexChanged.connect(self.__set_buildplate_node)
        wiper_label = QLabel("Wiper Motor:", gcodesender_settings)
        self.wiper_combo_box = MyQComboBox(gcodesender_settings)
        self.wiper_combo_box.addItems(nodes)
        self.wiper_combo_box.setCurrentIndex(self.__g_code_sender.get_wiper_node())
        self.wiper_combo_box.combo_box_clicked.connect(self.__update_nodes_list)
        self.wiper_combo_box.currentIndexChanged.connect(self.__set_wiper_node)
        buildplate_recoat_offset_label = QLabel("Buildplate recoating offset (mm):", gcodesender_settings)
        buildplate_recoat_offset_spin = QDoubleSpinBox(gcodesender_settings)
        buildplate_recoat_offset_spin.setRange(0, 99999)
        buildplate_recoat_offset_spin.setDecimals(3)
        buildplate_recoat_offset_spin.setSingleStep(0.001)
        buildplate_recoat_offset_spin.setValue(self.__g_code_sender.get_building_plate_recoating_offset())
        buildplate_recoat_offset_spin.valueChanged.connect(self.__g_code_sender.set_building_plate_recoat_offset)
        buildplate_recoat_feedrate_label = QLabel("Buildplate recoating feedrate (mm/min):", gcodesender_settings)
        buildplate_recoat_feedrate_spin = QDoubleSpinBox(gcodesender_settings)
        buildplate_recoat_feedrate_spin.setRange(0, 99999)
        buildplate_recoat_feedrate_spin.setDecimals(3)
        buildplate_recoat_feedrate_spin.setSingleStep(0.001)
        buildplate_recoat_feedrate_spin.setValue(self.__g_code_sender.get_building_plate_recoating_feedrate())
        buildplate_recoat_feedrate_spin.valueChanged.connect(self.__g_code_sender.set_building_plate_recoat_feedrate)
        wiper_recoat_offset_label = QLabel("Wiper recoating offset: (mm)", gcodesender_settings)
        wiper_recoat_offset_spin = QDoubleSpinBox(gcodesender_settings)
        wiper_recoat_offset_spin.setRange(0, 99999)
        wiper_recoat_offset_spin.setDecimals(3)
        wiper_recoat_offset_spin.setSingleStep(0.001)
        wiper_recoat_offset_spin.setValue(self.__g_code_sender.get_wiper_recoating_offset())
        wiper_recoat_offset_spin.valueChanged.connect(self.__g_code_sender.set_wiper_recoat_offset)
        wiper_recoat_feedrate_label = QLabel("Wiper recoating feedrate (mm/min):", gcodesender_settings)
        wiper_recoat_feedrate_spin = QDoubleSpinBox(gcodesender_settings)
        wiper_recoat_feedrate_spin.setRange(0, 99999)
        wiper_recoat_feedrate_spin.setDecimals(3)
        wiper_recoat_feedrate_spin.setSingleStep(0.001)
        wiper_recoat_feedrate_spin.setValue(self.__g_code_sender.get_wiper_recoating_feedrate())
        wiper_recoat_feedrate_spin.valueChanged.connect(self.__g_code_sender.set_wiper_recoat_feedrate)
        motor_layout = QGridLayout(gcodesender_settings)
        motor_layout.addWidget(buildplate_label, 0, 0)
        motor_layout.addWidget(self.buildplate_combo_box, 0, 1)
        motor_layout.addWidget(buildplate_recoat_offset_label, 1, 0)
        motor_layout.addWidget(buildplate_recoat_offset_spin, 1, 1)
        motor_layout.addWidget(buildplate_recoat_feedrate_label, 2, 0)
        motor_layout.addWidget(buildplate_recoat_feedrate_spin, 2, 1)
        motor_layout.addWidget(wiper_label, 3, 0)
        motor_layout.addWidget(self.wiper_combo_box, 3, 1)
        motor_layout.addWidget(wiper_recoat_offset_label, 4, 0)
        motor_layout.addWidget(wiper_recoat_offset_spin, 4, 1)
        motor_layout.addWidget(wiper_recoat_feedrate_label, 5, 0)
        motor_layout.addWidget(wiper_recoat_feedrate_spin, 5, 1)
        return gcodesender_settings

    @Slot(int)
    def __set_buildplate_node(self, value):
        nodes = self.__g_code_sender.get_motor_nodes_count_list()
        ports = self.__g_code_sender.get_motor_ports_connected()
        node_idx = value
        for port_idx in range(ports):
            if node_idx < nodes[port_idx]:
                self.__g_code_sender.set_buildplate_port(port_idx)
                self.__g_code_sender.set_buildplate_node(node_idx)
                return
            else:
                node_idx = node_idx - nodes[port_idx]

    @Slot(int)
    def __set_wiper_node(self, value):
        nodes = self.__g_code_sender.get_motor_nodes_count_list()
        ports = self.__g_code_sender.get_motor_ports_connected()
        node_idx = value
        for port_idx in range(ports):
            if node_idx < nodes[port_idx]:
                self.__g_code_sender.set_wiper_port(port_idx)
                self.__g_code_sender.set_wiper_node(node_idx)
                return
            else:
                node_idx = node_idx - nodes[port_idx]
        return

    @Slot()
    def __update_nodes_list(self):
        nodes = [str(item) for item in self.__g_code_sender.get_motor_nodes_id_list()]
        buildplate_current_idx = self.buildplate_combo_box.currentIndex()
        self.buildplate_combo_box.blockSignals(True)
        self.buildplate_combo_box.clear()
        self.buildplate_combo_box.addItems(nodes)
        self.buildplate_combo_box.blockSignals(False)
        self.buildplate_combo_box.setCurrentIndex(buildplate_current_idx)
        wiper_current_idx = self.wiper_combo_box.currentIndex()
        self.wiper_combo_box.blockSignals(True)
        self.wiper_combo_box.clear()
        self.wiper_combo_box.addItems(nodes)
        self.wiper_combo_box.blockSignals(False)
        self.wiper_combo_box.setCurrentIndex(wiper_current_idx)

