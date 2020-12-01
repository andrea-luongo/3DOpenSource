# 3DOpenSource
################################################################################################

This repo is part of the Open Additive Manufacturing project carried out at the Mechanical Department of the Technical University of Denmark, and funded by the Poul Due Jensen foundation (https://www.pdjf.dk/en/program/open-additive-manufacturing/).

################################################################################################

This framework can be used to print using a DLP 3D printer or a Powder Bed Fusion metal printer.

Add the moment this software supports the following projectors:

- 	Visitech LRS-WQ: this projector uses i2c for communication and it comes with a proprietary usb-i2c adapter by Diolan. 
	If you own this projector and its software, place the executable i2c_cmd.exe inside the "./resources" folder of this project.
- 	Visitech LRS4KA: this projector comes with proprietary software written in C++ from Keynote Photonics. 
	We provide a python wrapper for these libraries, in order to make it work place the following ".dll" files in the "./external_libraries/visitech/" folder: 
	- "BSL430.dll"
	- "KPDLP660.dll"
	- "KPMSP430.dll"
	- "hidapi.dll"
	
We also support the following motors:
- Clearpath SDSK: which is controlled through an arduino running Marlin firmware
- Clearpath SCSK: the software and C++ libraries to control this motor can be downloaded from www.teknic.com.
  We provide a python wrapper for such libraries, in order to make it work copy the downloaded "sFoundation20.dll" file into the "./external_libraries/clearpath/" folder
- Physik Instrumente L511: python libraries can be installed https://pypi.org/project/PIPython/


You are welcome to implement new scripts for different models of motors and projectors :)
You can find examples under DLPPrinter/projectors/ and DLPPrinter/motors. 
As long as you support the public interfaces described below, your code should work.
(Remember to add the name of your motors/projectors in dlpGUI.py, and dlpMotorController.py and dlpProjectorController.py)

A new projector should implement the following interface:
- init_projector()  # initialize and turn on the projector, return True if succeeds, False otherwise
- stop_projector() # shut down projector
- set_amplitude(a) # set the projector amplitude to the value of the parameter a

A new motor should implement the following interface:
- get_step_length_microns() # return the length of a single motor step in microns
- connect_motor(serial_port) # connect and activate motor, return True or False. serial_port parameter could be ignored if different connection is used
- disconnect_motor() # disconnect motor, return True or False
- reset_motor() #reset motor status, this function could be left empty, return True or False
- home_motor()  #send building plate to home position, return True or False. 
- move_motor(distance, feed_rate, relative_move) # move building plate, relative_move is a boolean indicating if the movement is relative to the current position or absolute.
- move_projector(distance_mm, feed_rate_mm_min, is_relative) # move projector, is_relative is a boolean indicating if the movement is relative to the current position or absolute. 
  
  The following functions could simply return False if the projector is not attached to a motor.
- home_projector() # send projector to home position, return True or False. This function could be left empty if the projector is not attached to a motor.
- lock_projector() # lock/unlock motor break attached to the projector. This function could be left empty if there is no break on the projector.
- print_motor_position() # get and print to console the current position of the motor
- stop_motor_movement() # stop all motor movements

################################################################################################

To make the code work:
- open "Anaconda Prompt" in the location of the software installation
- (to install) run "conda env create -f environment.yaml" 
- run "conda activate 3DOpenSource"
- run "python main.py"

################################################################################################
