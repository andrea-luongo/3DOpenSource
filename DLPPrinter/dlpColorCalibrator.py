from PySide2.QtCore import Signal, Slot, QObject
import numpy as np
import scipy.optimize as opt


class DLPColorCalibrator(QObject):

    analysis_completed_signal = Signal()

    def __init__(self):
        QObject.__init__(self)
        self.selected_data_files = None
        self.loaded_data = []
        self.average_data = []
        self.resized_data = []
        self.optimized_parameters = [0, 0, 0]
        self.input_values = []
        self.fitted_curve = []
        self.corrected_input_values = []
        self.corrected_output_values = []
        self.measured_thickness = 0

    def analyze_data_files(self, paths):
        self.selected_data_files = paths
        self.loaded_data = []
        self.average_data = []
        self.resized_data = []
        self.optimized_parameters = []
        self.input_values = []
        self.fitted_curve = []
        self.corrected_input_values = []
        self.corrected_output_values = []
        self.measured_thickness = 0
        for data in self.selected_data_files:
            print(data)
            tmp = self.asc_file_loader(data)
            self.loaded_data.append(tmp)
        self.average_multiple_data()
        self.input_values = np.linspace(0, 1, len(self.average_data))
        self.fit_log_function(self.input_values[1:], self.average_data[1:])
        self.fitted_curve = self.my_log_function(self.input_values, *self.optimized_parameters)
        self.measured_thickness = self.fitted_curve.max()
        self.corrected_input_values, tmp = self.my_color_correction(self.input_values, *self.optimized_parameters, self.measured_thickness)
        self.corrected_output_values = self.my_log_function(self.corrected_input_values, *self.optimized_parameters)
        self.analysis_completed_signal.emit()

    def asc_file_loader(self, file_path):
        loaded_data = np.loadtxt(file_path)
        x = loaded_data[:, 0]
        x = np.linspace(0, 1, len(x))
        y = loaded_data[:, 1]
        y = (y - y.min()) / 1000
        y = np.flip(y)
        return y

    def average_multiple_data(self):
        max_length = 0
        for d in self.loaded_data:
            if len(d) > max_length:
                max_length = len(d)
        for idx, d in enumerate(self.loaded_data):
            x = np.linspace(0, 1, max_length)
            x_old = np.linspace(0, 1, len(d))
            y = np.interp(x, x_old, d)
            self.resized_data.append(y)
        self.average_data = np.mean(np.array([i for i in self.resized_data]), axis=0)

    @staticmethod
    def my_log_function(x, a, b, c):
        return (a + b * np.nan_to_num(np.log(x - c))) * (x > np.exp(-a / b) + c)

    def fit_log_function(self, X, Y):
        self.optimized_parameters, pcov = opt.curve_fit(self.my_log_function, X, Y, bounds=(0.00001, np.inf), p0=[0.001, 0.001, 0.001])

    @staticmethod
    def im2double(input_image):
        info = np.iinfo(input_image.dtype)  # Get the data type of the input image
        return input_image.astype(np.float) / info.max

    @staticmethod
    def my_color_correction(input_image, a, b, c, thickness):
        if input_image.dtype.name == 'uint8':
            info = np.iinfo(input_image.dtype)  # Get the data type of the input image
            input_image = input_image.astype(np.float) / info.max
        corrected_input = np.nan_to_num(np.exp((thickness * input_image - a) / b)) + c
        corrected_input[input_image == 0] = 0
        corrected_input[input_image == 1] = 1
        uint_corrected_input = 255 * corrected_input  # Now scale by 255
        uint_corrected_input = uint_corrected_input.astype(np.uint8)
        return corrected_input, uint_corrected_input
