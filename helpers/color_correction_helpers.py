import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from PySide2.QtCore import QDir
import scipy.optimize as opt


def asc_file_loader(file_name):
    loaded_data = np.loadtxt(file_name)
    x = loaded_data[:, 0]
    x = np.linspace(0, 1, len(x))
    y = loaded_data[:, 1]
    y = (y - y.min()) / 1000
    y = np.flip(y)
    return y

def average_multiple_data(data):
    max_length = 0
    resized_data = []
    for d in data:
        if len(d) > max_length:
            max_length = len(d)
    for idx, d in enumerate(data):
        x = np.linspace(0, 1, max_length)
        x_old = np.linspace(0, 1, len(d))
        y = np.interp(x, x_old, d)
        resized_data.append(y)
    average_data = np.mean(np.array([i for i in resized_data]), axis=0)
    return average_data, resized_data


def my_log_function(x, a, b, c):
    return (a + b * np.nan_to_num(np.log(x - c))) * (x > np.exp(-a / b) + c)


def fit_log_function(X, Y):
    popt, pcov = opt.curve_fit(my_log_function, X, Y,  bounds=(0.00001, np.inf), p0=[0.001,0.001,0.001])
    popt[0:2]
    return popt


def im2double(im):
    info = np.iinfo(im.dtype) # Get the data type of the input image
    return im.astype(np.float) / info.max


def my_color_correction(image, a, b, c, thickness=10):
    corrected_image = image
    if image.dtype.name == 'uint8':
        corrected_image = im2double(image)
    corrected_image = np.nan_to_num(np.exp((thickness * image - a) / b)) + c
    corrected_image[image == 0] = 0
    corrected_image[image == 1] = 1
    return corrected_image


if __name__ == "__main__":
    base_path = Path(__file__).parent
    folder_path = str('../measured_data/grayscale_measured_data/')
    data_folder = QDir(folder_path)
    data_paths = data_folder.entryInfoList('*.asc', QDir.Files)
    loaded_data = []
    for data in data_paths:
        # print(data.absoluteFilePath())
        tmp = asc_file_loader(data.absoluteFilePath())
        loaded_data.append(tmp)
    average_data, resized_data = average_multiple_data(loaded_data)
    # for r_data in resized_data:
    #     plt.plot(np.linspace(0, 1, len(r_data)), r_data)
    #     plt.show(block=False)
    for idx, d in enumerate(loaded_data):
        x = np.linspace(0, 1, len(d))
        popt = fit_log_function(x[1:], d[1:])
        plt.figure()
        plt.subplot(221)
        plt.plot(x, x)
        plt.subplot(222)
        fitted_log = my_log_function(x, *popt)
        plt.plot(x, fitted_log)
        plt.plot(x, d)
        plt.subplot(223)
        thickness = fitted_log.max()
        corrected_x = my_color_correction(x, *popt, thickness)
        plt.plot(x, corrected_x)
        plt.subplot(224)
        corrected_output = my_log_function(corrected_x, *popt)
        plt.plot(x, corrected_output)
        plt.show(block=False)
        print(popt)

    x = np.linspace(0, 1, len(average_data))
    popt = fit_log_function(x[1:], average_data[1:])
    plt.figure()
    plt.subplot(221)
    plt.plot(x, x)
    plt.subplot(222)
    fitted_log = my_log_function(x, *popt)
    plt.plot(x, fitted_log)
    plt.plot(x, average_data)
    plt.subplot(223)
    thickness = fitted_log.max()
    corrected_x = my_color_correction(x, *popt, thickness)
    plt.plot(x, corrected_x)
    plt.subplot(224)
    corrected_output = my_log_function(corrected_x, *popt)
    plt.plot(x, corrected_output)
    plt.show(block=False)
    print(popt)
    plt.show()
