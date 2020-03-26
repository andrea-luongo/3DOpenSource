from PySide2.QtWidgets import QWidget, QSizePolicy, QFileDialog, QLabel, QTableView, QGroupBox, QHBoxLayout, QVBoxLayout, QPushButton, QGridLayout
from PySide2.QtGui import QGuiApplication, QPainter
from PySide2.QtCore import Signal, Slot, QAbstractTableModel, Qt
from PySide2.QtCharts import QtCharts
from DLPPrinter.dlpColorCalibrator import DLPColorCalibrator


class DLPSettingsGUI(QWidget):

    def __init__(self, dlp_controller=None, dlp_slicer=None, parent=None):
        QWidget.__init__(self, parent)
        self.parent = parent
        self.dlp_controller = dlp_controller
        self.dlp_slicer = dlp_slicer
        self.dlp_color_calibrator = DLPColorCalibrator()
        self.dlp_color_calibrator.analysis_completed_signal.connect(self.update_charts)
        self.__printer_parameters_list = {}
        self.__slicer_parameters_list = {}
        self.data_fit_chart_view = None
        self.data_fit_chart = None
        self.main_layout = QHBoxLayout()
        self.__init_table_widget__()
        self.__init_color_calibration_widget()
        self.main_layout.addWidget(self.__default_parameters_widget, stretch=1)
        self.main_layout.addWidget(self.__color_calibration_widget, stretch=2)
        self.setLayout(self.main_layout)
        self.__adjust_table_size__()
        self.updateGeometry()
        self.table_view.updateGeometry()
        self.__color_calibration_widget.updateGeometry()
        self.__default_parameters_widget.updateGeometry()
        self.table_model.dataChanged.emit(0, 0)
        self.main_layout.update()

    def __init_color_calibration_widget(self, parent=None):
        self.__color_calibration_widget = QGroupBox("Color Correction Options", parent)
        self.__color_calibration_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        color_calibration_layout = QVBoxLayout(self.__color_calibration_widget)

        chart_widget = QWidget(self.__color_calibration_widget)
        chart_layout = QGridLayout(chart_widget)
        self.data_fit_chart = QtCharts.QChart()
        self.data_fit_chart_view = QtCharts.QChartView(self.data_fit_chart)
        self.axis_x = QtCharts.QValueAxis()
        self.axis_x.setTitleText("Pixel Intensity")
        self.axis_x.setRange(0, 1)
        self.data_fit_chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.axis_y = QtCharts.QValueAxis()
        self.axis_y.setTitleText("Voxel Height (\u03BCm)")
        self.axis_y.setRange(0, 10)
        self.data_fit_chart.addAxis(self.axis_y, Qt.AlignLeft)
        chart_layout.addWidget(self.data_fit_chart_view, 0, 0, 1, 4)
        chart_widget.setLayout(chart_layout)

        buttons_widget = QWidget(self.__color_calibration_widget)
        buttons_layout = QHBoxLayout(buttons_widget)
        analyze_data_button = QPushButton("Analyze Data")
        analyze_data_button.clicked.connect(self.analyze_images)
        self.parameters_estimation_label = QLabel(f'Estimated parameters: \u03B1 = {self.dlp_color_calibrator.optimized_parameters[0]:.3f}, \u03B2 = {self.dlp_color_calibrator.optimized_parameters[1]:.3f}, \u03B3 =  {self.dlp_color_calibrator.optimized_parameters[2]:.3f}',
                                buttons_widget)
        buttons_layout.addWidget(analyze_data_button)
        buttons_layout.addWidget(self.parameters_estimation_label)
        buttons_widget.setLayout(buttons_layout)
        color_calibration_layout.addWidget(chart_widget)
        color_calibration_layout.addWidget(buttons_widget)
        self.__color_calibration_widget.setLayout(color_calibration_layout)

    @Slot()
    def analyze_images(self):
        file_names = QFileDialog.getOpenFileNames(caption='Select data', dir='../data_analysis/asc_data',
                                                  filter="Image Files (*.asc)")
        self.dlp_color_calibrator.analyze_data_files(file_names[0])

    @Slot()
    def update_charts(self):
        self.data_fit_chart = QtCharts.QChart()
        self.data_fit_chart.setAnimationOptions(QtCharts.QChart.AllAnimations)
        self.add_series(self.data_fit_chart, "Measured Data", self.dlp_color_calibrator.input_values, self.dlp_color_calibrator.average_data)
        self.add_series(self.data_fit_chart, "Fitted Curve", self.dlp_color_calibrator.input_values,
                        self.dlp_color_calibrator.fitted_curve)
        self.add_series(self.data_fit_chart, "Predicted Result", self.dlp_color_calibrator.input_values,
                        self.dlp_color_calibrator.corrected_output_values)
        series = self.data_fit_chart.series()
        self.data_fit_chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.axis_y.setRange(0, self.dlp_color_calibrator.measured_thickness)
        self.data_fit_chart.addAxis(self.axis_y, Qt.AlignLeft)
        for s in series:
            s.attachAxis(self.axis_x)
            s.attachAxis(self.axis_y)

        self.data_fit_chart_view.setRenderHint(QPainter.Antialiasing)
        self.data_fit_chart_view.setChart(self.data_fit_chart)

        self.parameters_estimation_label.setText(f'Estimated parameters: \u03B1 = {self.dlp_color_calibrator.optimized_parameters[0]:.3f}, \u03B2 = {self.dlp_color_calibrator.optimized_parameters[1]:.3f}, \u03B3 =  {self.dlp_color_calibrator.optimized_parameters[2]:.3f}')

    def add_series(self, chart, title, x, y):
        series = QtCharts.QLineSeries()
        series.setName(title)
        for idx, elem in enumerate(x):
            series.append(x[idx], y[idx])
        chart.addSeries(series)

    def __init_table_widget__(self, parent=None):
        self.__default_parameters_widget = QGroupBox("Default Parameters", parent)
        self.printer_parameters_list = self.dlp_controller.get_default_parameters()
        self.table_view = QTableView()
        self.table_model = self.MyTableModel(parent=self, data_list=self.printer_parameters_list)
        self.table_view.setModel(self.table_model)
        self.table_view.update()
        self.table_view.resizeColumnsToContents()
        self.table_view.horizontalHeader().setVisible(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setStretchLastSection(False)
        apply_button = QPushButton("Apply Changes", self)
        apply_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        apply_button.clicked.connect(self.dlp_controller.save_default_parameters)
        default_parameters_layout = QVBoxLayout(self.__default_parameters_widget)
        default_parameters_layout.addWidget(self.table_view)
        default_parameters_layout.addWidget(apply_button)
        self.__default_parameters_widget.setLayout(default_parameters_layout)
        self.__default_parameters_widget.updateGeometry()
        default_parameters_layout.update()
        QGuiApplication.processEvents()

    @Slot()
    def __adjust_table_size__(self):
        self.table_view.resizeColumnToContents(0)
        self.table_view.resizeColumnToContents(1)
        rect = self.table_view.geometry()
        rect.setWidth(1 + self.table_view.verticalHeader().width() + self.table_view.columnWidth(0) +
                      self.table_view.columnWidth(1) + self.table_view.verticalScrollBar().width())
        self.table_view.setGeometry(rect)
        self.table_view.resize(rect.width(), rect.height())

    class MyTableModel(QAbstractTableModel):
        def __init__(self, parent, data_list, *args):
            QAbstractTableModel.__init__(self, parent, *args)
            self.parent = parent
            self.data_list = data_list

        def rowCount(self, parent):
            return len(self.data_list)

        def columnCount(self, parent):
            return 2

        def data(self, index, role):
            if not index.isValid():
                return None
            elif role != Qt.DisplayRole:
                return None
            return list(self.data_list.items())[index.row()][index.column()]

        def setData(self, index, value, role):
            if role == Qt.EditRole:
                if not index.isValid():
                    return False
                elif index.column() == 0:
                    return False
                else:
                    key = list(self.data_list.items())[index.row()][0]
                    old_value = list(self.data_list.items())[index.row()][1]
                    try:
                        if isinstance(old_value, float):
                            self.data_list[key] = float(value)
                        elif isinstance(old_value, bool):
                            if value == "True" or value == "true":
                                self.data_list[key] = True
                            else:
                                self.data_list[key] = False
                        elif isinstance(old_value, str):
                            if index.row() == 0:
                                if not (value.upper() == "TOP-DOWN" or value.upper() == "BOTTOM-UP"):
                                    return False
                            self.data_list[key] = str(value).upper()
                    except ValueError:
                        return False
                    self.dataChanged.emit(index, index)
                    return True
            else:
                return False

        def flags(self, index):
            if not index.isValid() or index.column() == 0:
                return Qt.ItemIsEnabled
            return Qt.ItemFlags(QAbstractTableModel.flags(self, index) |
                                Qt.ItemIsEditable)


