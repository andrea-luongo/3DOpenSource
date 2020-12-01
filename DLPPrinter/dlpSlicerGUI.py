import sys
from PySide2.QtWidgets import QVBoxLayout, QSpinBox, QWidget, QGroupBox, QSlider, QLabel, \
    QGridLayout, QDoubleSpinBox, QCheckBox, QPushButton, QFileDialog, QHBoxLayout, QMessageBox, QComboBox, QSizePolicy
from PySide2.QtCore import Signal, Slot, Qt, QFileInfo
from PySide2.QtGui import QGuiApplication
from DLPPrinter.dlpSlicer import DLPSlicer


class DLPSlicerGUI(QWidget):

    def __init__(self, dlp_controller=None, parent=None):
        QWidget.__init__(self, parent)
        if dlp_controller:
            self.dlp_controller = dlp_controller
        self.main_layout = QVBoxLayout()
        self.__init_slicer_widget__()
        self.__init_options_widget__()
        self.__options_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)
        self.main_layout.addWidget(self.__slicer_widget)
        self.main_layout.addWidget(self.__options_widget)
        self.setLayout(self.main_layout)

    def __init_slicer_widget__(self):
        self.__slicer_widget = DLPSlicer(parent=self, dlp_controller=self.dlp_controller)
        self.__slicer_widget.update_physical_size.connect(self.update_size_label)
        self.__slicer_widget.update_fps.connect(self.update_fps_label)
        self.__slicer_widget.update_slice_counts.connect(self.update_slices_label)

    def __init_options_widget__(self):
        self.__options_widget = QWidget(self)
        self.__init_info_widget__()
        self.__init_geometry_widget__()
        self.__init_slicer_options_widget__()
        self.__options_layout = QGridLayout()
        self.__options_layout.addWidget(self.__info_widget, 0, 0, 1, 3)
        self.__options_layout.addWidget(self.__geometry_widget, 1, 0, 1, 2)
        self.__options_layout.addWidget(self.__slicer_options_widget, 1, 2)
        self.__options_widget.setLayout(self.__options_layout)

    def __init_info_widget__(self):
        self.__info_widget = QWidget(self)
        current_geometry_label = QLabel("Selected Geometry:", self.__info_widget)
        self.current_geometry_index = -1
        self.geometry_list = MyQComboBox(self.__info_widget)
        self.geometry_list.currentIndexChanged.connect(self.update_geometry_transformations)
        self.fps_label = QLabel(f'fps: {0:.2f}', self.__info_widget)
        self.physical_size_label = QLabel(f'Width: {0:.2f} \u03BCm, Depth: {0:.2f} \u03BCm, Height: {0:.2f} \u03BCm',
                                          self.__info_widget)
        info_layout = QHBoxLayout()
        info_layout.addWidget(current_geometry_label)
        info_layout.addWidget(self.geometry_list)
        info_layout.addWidget(self.physical_size_label)
        info_layout.addWidget(self.fps_label)
        self.__info_widget.setLayout(info_layout)
        self.__info_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

    def __init_geometry_widget__(self):
        self.__geometry_widget = QGroupBox("Geometry", self)

        load_geometry_button = QPushButton("Load Geometry")
        load_geometry_button.clicked.connect(self.load_geometry)
        remove_geometry_button = QPushButton("Remove Geometry")
        remove_geometry_button.clicked.connect(self.remove_geometry)
        rotate_x_label = QLabel("Rotate X:", self.__geometry_widget)
        self.rotate_x_slider = QSlider(orientation=Qt.Horizontal, parent=self.__geometry_widget)
        self.rotate_x_slider.setTickPosition(QSlider.TicksBothSides)
        self.rotate_x_slider.setTickInterval(45)
        self.rotate_x_slider.setRange(-180, 180)
        self.rotate_x_slider.setValue(0)
        self.rotate_x_spin = QSpinBox(self.__geometry_widget)
        self.rotate_x_spin.setMinimum(-180)
        self.rotate_x_spin.setMaximum(180)
        self.rotate_x_spin.setValue(0)
        self.rotate_x_slider.valueChanged.connect(self.rotate_x_spin.setValue)
        self.rotate_x_slider.valueChanged.connect(self.__slicer_widget.set_x_rotation)
        self.rotate_x_spin.valueChanged.connect(self.rotate_x_slider.setValue)
        self.rotate_x_spin.valueChanged.connect(self.__slicer_widget.set_x_rotation)

        rotate_y_label = QLabel("Rotate Y:", self.__geometry_widget)
        self.rotate_y_slider = QSlider(orientation=Qt.Horizontal, parent=self.__geometry_widget)
        self.rotate_y_slider.setTickPosition(QSlider.TicksBothSides)
        self.rotate_y_slider.setTickInterval(45)
        self.rotate_y_slider.setRange(-180, 180)
        self.rotate_y_slider.setValue(0)
        self.rotate_y_spin = QSpinBox(self.__geometry_widget)
        self.rotate_y_spin.setMinimum(-180)
        self.rotate_y_spin.setMaximum(180)
        self.rotate_y_spin.setValue(0)
        self.rotate_y_slider.valueChanged.connect(self.rotate_y_spin.setValue)
        self.rotate_y_slider.valueChanged.connect(self.__slicer_widget.set_y_rotation)
        self.rotate_y_spin.valueChanged.connect(self.rotate_y_slider.setValue)
        self.rotate_y_spin.valueChanged.connect(self.__slicer_widget.set_y_rotation)

        rotate_z_label = QLabel("Rotate Z:", self.__geometry_widget)
        self.rotate_z_slider = QSlider(orientation=Qt.Horizontal, parent=self.__geometry_widget)
        self.rotate_z_slider.setTickPosition(QSlider.TicksBothSides)
        self.rotate_z_slider.setTickInterval(45)
        self.rotate_z_slider.setRange(-180, 180)
        self.rotate_z_slider.setValue(0)
        self.rotate_z_spin = QSpinBox(self.__geometry_widget)
        self.rotate_z_spin.setMinimum(-180)
        self.rotate_z_spin.setMaximum(180)
        self.rotate_z_spin.setValue(0)
        self.rotate_z_slider.valueChanged.connect(self.rotate_z_spin.setValue)
        self.rotate_z_slider.valueChanged.connect(self.__slicer_widget.set_z_rotation)
        self.rotate_z_spin.valueChanged.connect(self.rotate_z_slider.setValue)
        self.rotate_z_spin.valueChanged.connect(self.__slicer_widget.set_z_rotation)

        translate_x_label = QLabel("Translate X:", self.__geometry_widget)
        self.translate_x_slider = QSlider(orientation=Qt.Horizontal, parent=self.__geometry_widget)
        self.translate_x_slider.setTickPosition(QSlider.TicksBothSides)
        self.translate_x_slider.setTickInterval(self.dlp_controller.projector_pixel_size)
        self.translate_x_slider.setRange(-self.dlp_controller.projector_width * self.dlp_controller.projector_pixel_size * 0.5, self.dlp_controller.projector_width * self.dlp_controller.projector_pixel_size * 0.5)
        self.translate_x_slider.setValue(0)
        self.translate_x_spin = QDoubleSpinBox(self.__geometry_widget)
        self.translate_x_spin.setMinimum(-self.dlp_controller.projector_width * self.dlp_controller.projector_pixel_size * 0.5)
        self.translate_x_spin.setMaximum(self.dlp_controller.projector_width * self.dlp_controller.projector_pixel_size * 0.5)
        self.translate_x_spin.setSingleStep(self.dlp_controller.projector_pixel_size)
        self.translate_x_spin.setValue(0)
        self.translate_x_slider.valueChanged.connect(self.translate_x_spin.setValue)
        self.translate_x_slider.valueChanged.connect(self.__slicer_widget.set_x_pos)
        self.translate_x_spin.valueChanged.connect(self.translate_x_slider.setValue)
        self.translate_x_spin.valueChanged.connect(self.__slicer_widget.set_x_pos)

        translate_z_label = QLabel("Translate Z:", self.__geometry_widget)
        self.translate_z_slider = QSlider(orientation=Qt.Horizontal, parent=self.__geometry_widget)
        self.translate_z_slider.setTickPosition(QSlider.TicksBothSides)
        self.translate_z_slider.setTickInterval(self.dlp_controller.projector_pixel_size)
        self.translate_z_slider.setRange(-self.dlp_controller.projector_height * self.dlp_controller.projector_pixel_size * 0.5, self.dlp_controller.projector_height * self.dlp_controller.projector_pixel_size * 0.5)
        self.translate_z_slider.setValue(0)
        self.translate_z_spin = QDoubleSpinBox(self.__geometry_widget)
        self.translate_z_spin.setMinimum(-self.dlp_controller.projector_height * self.dlp_controller.projector_pixel_size * 0.5)
        self.translate_z_spin.setMaximum(self.dlp_controller.projector_height * self.dlp_controller.projector_pixel_size * 0.5)
        self.translate_z_spin.setSingleStep(self.dlp_controller.projector_pixel_size)
        self.translate_z_spin.setValue(0)
        self.translate_z_slider.valueChanged.connect(self.translate_z_spin.setValue)
        self.translate_z_slider.valueChanged.connect(self.__slicer_widget.set_z_pos)
        self.translate_z_spin.valueChanged.connect(self.translate_z_slider.setValue)
        self.translate_z_spin.valueChanged.connect(self.__slicer_widget.set_z_pos)

        scale_x_label = QLabel("Scale X:", self.__geometry_widget)
        self.scale_x_spin = QDoubleSpinBox(self.__geometry_widget)
        self.scale_x_spin.setMinimum(-1000)
        self.scale_x_spin.setMaximum(1000)
        self.scale_x_spin.setDecimals(2)
        self.scale_x_spin.setValue(1)
        self.scale_x_spin.setSingleStep(0.01)
        self.scale_x_spin.setObjectName("scale_x_spin")
        self.scale_x_spin.valueChanged.connect(self.set_scaling)

        scale_y_label = QLabel("Scale Y:", self.__geometry_widget)
        self.scale_y_spin = QDoubleSpinBox(self.__geometry_widget)
        self.scale_y_spin.setMinimum(-1000)
        self.scale_y_spin.setMaximum(1000)
        self.scale_y_spin.setDecimals(2)
        self.scale_y_spin.setValue(1)
        self.scale_y_spin.setSingleStep(0.01)
        self.scale_y_spin.setObjectName("scale_y_spin")
        self.scale_y_spin.valueChanged.connect(self.set_scaling)

        scale_z_label = QLabel("Scale Z:", self.__geometry_widget)
        self.scale_z_spin = QDoubleSpinBox(self.__geometry_widget)
        self.scale_z_spin.setMinimum(-1000)
        self.scale_z_spin.setMaximum(1000)
        self.scale_z_spin.setDecimals(2)
        self.scale_z_spin.setValue(1)
        self.scale_z_spin.setSingleStep(0.01)
        self.scale_z_spin.setObjectName("scale_z_spin")
        self.scale_z_spin.valueChanged.connect(self.set_scaling)

        self.uniform_scaling = QCheckBox("Uniform Scaling", self.__geometry_widget)
        self.uniform_scaling.setChecked(True)
        # self.uniform_scaling.setLayoutDirection(Qt.RightToLeft)

        list_of_measures = ('\u03BCm', 'mm', 'cm', 'dm', 'm')
        self.list_of_measures_coefficients = [0.001, 1, 10, 100, 1000]
        unit_of_measure_label = QLabel("Unit of Measure", self.__geometry_widget)
        self.unit_of_measure_combo = QComboBox(self.__geometry_widget)
        for measure in list_of_measures:
            self.unit_of_measure_combo.addItem(measure)
        self.unit_of_measure_combo.setCurrentIndex(1)
        self. unit_of_measure_combo.currentIndexChanged.connect(self.update_unit_of_measure)

        rotate_x_row = 0
        rotate_y_row = rotate_x_row + 1
        rotate_z_row = rotate_y_row + 1
        translate_x_row = rotate_z_row + 1
        translate_z_row = translate_x_row + 1
        scale_x_row = translate_z_row + 1
        scale_y_row = scale_x_row + 1
        scale_z_row = scale_y_row + 1
        uniform_scaling_row = scale_x_row
        unit_of_measure_row = scale_y_row
        load_geometry_row = scale_z_row + 1
        remove_geometry_row = load_geometry_row

        geometry_layout = QGridLayout(self.__geometry_widget)
        geometry_layout.addWidget(load_geometry_button, load_geometry_row, 1, 1, 2)
        geometry_layout.addWidget(remove_geometry_button, remove_geometry_row, 3, 1, 2)
        geometry_layout.addWidget(rotate_x_label, rotate_x_row, 0)
        geometry_layout.addWidget(self.rotate_x_slider, rotate_x_row, 1, 1, 4)
        geometry_layout.addWidget(self.rotate_x_spin, rotate_x_row, 5)
        geometry_layout.addWidget(rotate_y_label, rotate_y_row, 0)
        geometry_layout.addWidget(self.rotate_y_slider, rotate_y_row, 1, 1, 4)
        geometry_layout.addWidget(self.rotate_y_spin, rotate_y_row, 5)
        geometry_layout.addWidget(rotate_z_label, rotate_z_row, 0)
        geometry_layout.addWidget(self.rotate_z_slider, rotate_z_row, 1, 1, 4)
        geometry_layout.addWidget(self.rotate_z_spin, rotate_z_row, 5)
        geometry_layout.addWidget(translate_x_label, translate_x_row, 0)
        geometry_layout.addWidget(self.translate_x_slider, translate_x_row, 1, 1, 4)
        geometry_layout.addWidget(self.translate_x_spin, translate_x_row, 5)
        geometry_layout.addWidget(translate_z_label, translate_z_row, 0)
        geometry_layout.addWidget(self.translate_z_slider, translate_z_row, 1, 1, 4)
        geometry_layout.addWidget(self.translate_z_spin, translate_z_row, 5)
        geometry_layout.addWidget(scale_x_label, scale_x_row, 0)
        geometry_layout.addWidget(self.scale_x_spin, scale_x_row, 1)
        geometry_layout.addWidget(scale_y_label, scale_y_row, 0)
        geometry_layout.addWidget(self.scale_y_spin, scale_y_row, 1)
        geometry_layout.addWidget(scale_z_label, scale_z_row, 0)
        geometry_layout.addWidget(self.scale_z_spin, scale_z_row, 1)
        geometry_layout.addWidget(self.uniform_scaling, uniform_scaling_row, 3, 1, 2)
        geometry_layout.addWidget(unit_of_measure_label, unit_of_measure_row, 4)
        geometry_layout.addWidget(self.unit_of_measure_combo, unit_of_measure_row, 3)
        self.__geometry_widget.setLayout(geometry_layout)

    def __init_slicer_options_widget__(self):
        self.__slicer_options_widget = QGroupBox("Slicer Options", self)

        thickness_label = QLabel("Layer Thickness", self.__slicer_options_widget)
        thickness_edit = QDoubleSpinBox(self.__slicer_options_widget)
        thickness_edit.setSuffix(str('\u03BCm'))
        thickness_edit.setMaximum(1000000)
        thickness_edit.setMinimum(0)
        thickness_edit.setDecimals(3)
        thickness_edit.setSingleStep(0.001)
        thickness_edit.setValue(self.dlp_controller.support_thickness * 1000)
        # self.__opengl_widget.set_slice_thickness(self.dlp_controller.support_thickness)
        thickness_edit.valueChanged.connect(self.__slicer_widget.set_slice_thickness)

        pixel_size_label = QLabel("Projector Pixel Size", self.__slicer_options_widget)
        pixel_size_edit = QDoubleSpinBox(self.__slicer_options_widget)
        pixel_size_edit.setSuffix(str('\u03BCm'))
        pixel_size_edit.setMaximum(1000000)
        pixel_size_edit.setMinimum(0)
        pixel_size_edit.setDecimals(2)
        pixel_size_edit.setSingleStep(0.01)
        pixel_size_edit.setValue(self.dlp_controller.projector_pixel_size * 1000)
        pixel_size_edit.valueChanged.connect(self.__slicer_widget.set_pixel_size)

        projector_resolution_label = QLabel("Projector Resolution", self.__slicer_options_widget)
        projector_resolution_edit_x = QSpinBox(self.__slicer_options_widget)
        projector_resolution_edit_x.setSuffix(str('W'))
        projector_resolution_edit_x.setMaximum(1000000)
        projector_resolution_edit_x.setMinimum(0)
        projector_resolution_edit_x.setValue(self.dlp_controller.projector_width)
        projector_resolution_edit_x.valueChanged.connect(self.__slicer_widget.set_projector_width)
        projector_resolution_edit_y = QSpinBox(self.__slicer_options_widget)
        projector_resolution_edit_y.setSuffix(str('H'))
        projector_resolution_edit_y.setMaximum(1000000)
        projector_resolution_edit_y.setMinimum(0)
        projector_resolution_edit_y.setValue(self.dlp_controller.projector_height)
        projector_resolution_edit_y.valueChanged.connect(self.__slicer_widget.set_projector_height)

        samples_per_pixel_label = QLabel("Samples per Pixel", self.__slicer_options_widget)
        samples_per_pixel_edit = QSpinBox(self.__slicer_options_widget)
        samples_per_pixel_edit.setMaximum(1000000)
        samples_per_pixel_edit.setMinimum(1)
        samples_per_pixel_edit.setValue(self.dlp_controller.samples_per_pixel)
        samples_per_pixel_edit.valueChanged.connect(self.__slicer_widget.set_samples_per_pixel)

        slice_geometry_button = QPushButton("Slice Geometry")
        slice_geometry_button.clicked.connect(self.start_slicing_process)

        slice_interrupt_button = QPushButton("Stop Slicing")
        slice_interrupt_button.clicked.connect(self.__slicer_widget.interrupt_slicing)

        self.slices_label = QLabel(f'Slicing progress: {0:.0f}/{0:.0f}', self.__info_widget)

        thickness_label_row = 0
        pixel_size_row = 1
        projector_resolution_row = 2
        samples_per_pixel_row = 3
        slice_button_row = 4
        slices_label_row = 5
        # slice_interrupt_row = slice_button_row

        slice_layout = QGridLayout(self.__slicer_options_widget)
        slice_layout.addWidget(thickness_label, thickness_label_row, 0)
        slice_layout.addWidget(thickness_edit, thickness_label_row, 1)
        slice_layout.addWidget(pixel_size_label, pixel_size_row, 0)
        slice_layout.addWidget(pixel_size_edit, pixel_size_row, 1)
        slice_layout.addWidget(projector_resolution_label, projector_resolution_row, 0)
        slice_layout.addWidget(projector_resolution_edit_x, projector_resolution_row, 1)
        slice_layout.addWidget(projector_resolution_edit_y, projector_resolution_row, 2)
        slice_layout.addWidget(self.slices_label, slice_button_row, 0)
        slice_layout.addWidget(slice_geometry_button, slice_button_row, 1)
        slice_layout.addWidget(slice_interrupt_button, slice_button_row, 2)
        slice_layout.addWidget(samples_per_pixel_label, samples_per_pixel_row, 0)
        slice_layout.addWidget(samples_per_pixel_edit, samples_per_pixel_row, 1)
        self.__slicer_options_widget.setLayout(slice_layout)

    @Slot(float)
    def set_scaling(self, value):
        if self.uniform_scaling.isChecked():
            self.__slicer_widget.set_x_scale(value)
            self.__slicer_widget.set_y_scale(value)
            self.__slicer_widget.set_z_scale(value)
            self.scale_x_spin.setValue(value)
            self.scale_y_spin.setValue(value)
            self.scale_z_spin.setValue(value)
        else:
            self.__slicer_widget.set_x_scale(self.scale_x_spin.value())
            self.__slicer_widget.set_y_scale(self.scale_y_spin.value())
            self.__slicer_widget.set_z_scale(self.scale_z_spin.value())

    @Slot()
    def load_geometry(self):
        file_names = QFileDialog.getOpenFileNames(caption='Select Geometry', dir='../',
                                                  filter="Files (*.obj *.stl)", parent=self)
        loading_dialog = QMessageBox()
        loading_dialog.setText("Loading Geometry...")
        loading_dialog.setWindowTitle("AMLab Software")
        loading_dialog.setStandardButtons(QMessageBox.NoButton)
        loading_dialog.open()
        QGuiApplication.processEvents()
        swapyz = True
        for file_name in file_names[0]:
            if self.__slicer_widget.load_geometry(file_name, swapyz):
                self.geometry_list.addItem(self.__slicer_widget.geometry_name_list[self.__slicer_widget.geometries_loaded - 1])
                self.geometry_list.setCurrentIndex(self.geometry_list.count() - 1)
        QGuiApplication.processEvents()

    @Slot()
    def remove_geometry(self):
        self.__slicer_widget.remove_geometry()
        self.geometry_list.removeItem(self.geometry_list.currentIndex())

    @Slot()
    def start_slicing_process(self):
        directory_name = QFileDialog.getExistingDirectory(caption='Select Directory', dir='../', parent=self)
        if len(directory_name) > 0:
            self.__slicer_widget.prepare_for_slicing(directory=directory_name)

    @Slot(float, float, float)
    def update_size_label(self, width, depth, height):
        self.physical_size_label.setText(f'Width: {width:.3f} mm, Depth: {depth:.3f} mm, Height: {height:.3f} mm')

    @Slot(float)
    def update_fps_label(self, fps):
        self.fps_label.setText(f'fps: {fps:.2f}')

    @Slot(float, float)
    def update_slices_label(self, slice, total_slices):
        self.slices_label.setText(f'Slicing progress: {slice:.0f}/{total_slices:.0f}')

    @Slot(int)
    def update_unit_of_measure(self, index):
        self.__slicer_widget.set_unit_of_measurement(self.list_of_measures_coefficients[index])

    @Slot(int)
    def update_geometry_transformations(self, index):
        if index >= 0:
            self.__slicer_widget.current_geometry_idx = index
            x_rot = self.__slicer_widget.get_x_rot()
            y_rot = self.__slicer_widget.get_y_rot()
            z_rot = self.__slicer_widget.get_z_rot()
            x_scale = self.__slicer_widget.get_x_scale()
            y_scale = self.__slicer_widget.get_y_scale()
            z_scale = self.__slicer_widget.get_z_scale()
            x_pos = self.__slicer_widget.get_x_pos()
            z_pos = self.__slicer_widget.get_z_pos()
            unit_measurement = self.__slicer_widget.get_unit_of_measurement()
            self.__geometry_widget.blockSignals(True)
            self.rotate_x_slider.setValue(x_rot)
            self.rotate_x_spin.setValue(x_rot)
            self.rotate_y_slider.setValue(y_rot)
            self.rotate_y_spin.setValue(y_rot)
            self.rotate_z_slider.setValue(z_rot)
            self.rotate_z_spin.setValue(z_rot)
            self.translate_x_slider.setValue(x_pos)
            self.translate_x_spin.setValue(x_pos)
            self.translate_z_slider.setValue(z_pos)
            self.translate_z_spin.setValue(z_pos)
            self.scale_x_spin.setValue(x_scale)
            self.scale_y_spin.setValue(y_scale)
            self.scale_z_spin.setValue(z_scale)
            self.unit_of_measure_combo.setCurrentIndex(self.list_of_measures_coefficients.index(unit_measurement))
            self.__geometry_widget.blockSignals(False)


class MyQComboBox(QComboBox):

    combo_box_clicked = Signal()

    @Slot()
    def showPopup(self):
        self.combo_box_clicked.emit()
        super(MyQComboBox, self).showPopup()