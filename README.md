# 3DOpenSource
################################################################################################

This repo is part of the Open Additive Manufacturing project carried out at the Mechanical Department of the Technical University of Denmark, and funded by the Poul Due Jensen foundation (https://www.pdjf.dk/en/program/open-additive-manufacturing/).

################################################################################################
This framework can be used to print using a DLP 3D printer. Code for controlling a Powder Bed Fusion metal printer will be released in the future.
Add the moment this software supports only Visitech LRS WQ projector, which uses i2c for communication. 
The projector came with a usb-i2c adpter by Diolan. To make the code work, place the executable i2c_cmd.exe inside the ./resources folder of this project.
We also use a clearpath SDSK motor which is controlled through an arduino running Marlin firmware.

You are welcome to implement new scripts for different models of motors and projectors :)
You can find an example under DLPPrinter/projectors/ and DLPPrinter/motors. As long as you implement the same public functions in your script, your code should work.
Remember to add the name of your motor/projector in dlpGUI.py, and dlpMotorController.py and dlpProjectorController.py

A new projector should implement the following interface:
- init_projector()  # initialize and turn on the projector, return True if succeeds, False otherwise
- stop_projector() # shut down projector
- set_amplitude(a) # set the projector amplitude to the value of the parameter a

A new motor should implement the following interface:
- get_step_length_microns() # return the length of a single motor step in microns
- connect_printer(serial_port) # connect and activate motor, return True or False. serial_port parameter could be ignored if different connection is used
- disconnect_printer() # disconnect motor, return True or False
- reset_printer() #reset motor status, this function could be left empty, return True or False
- home_building_plate()  #send building plate to home position, return True or False
- move_building_plate(distance, feed_rate, relative_move) # move building plate, relative_move is a boolean indicating if the movement is relative to the current position or absolute.
- move_projector(distance, feed_rate, relative_move) # move projector, relative_move is a boolean indicating if the movement is relative to the current position or absolute. This function could be left empty if the projector is not attached to a motor.
- home_projector() # send projector to home position, return True or False. This function could be left empty if the projector is not attached to a motor.
- lock_projector() # lock/unlock motor break attached to the projector. This function could be left empty if there is no break on the projector.
- print_motor_position() # get and print to console the current position of the motor
- stop_motor_movement() # stop all motor movements

################################################################################################

To make the code work:

- open a python terminal in the position of this project.
- create a new venv by running "py -m venv your_name"
- activate the environment "./your_name/Scripts/activate"
- run "pip install -r requirements.txt"

################################################################################################
