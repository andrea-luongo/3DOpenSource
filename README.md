# 3DOpenSource
Open source framework for 3D printing. 

Code for controlling a Powder Bed Fusion metal printer will be released in the future.

Add the moment this software supports only Visitech LRS WQ projector, which uses i2c for communication. 
The projector came with a usb-i2c adpter by Diolan. To make the code work, place the executable i2c_cmd.exe inside the ./resources folder of this project.
We also use a clearpath SDSK motor which is controlled through an arduino running Marlin firmware.

You are welcome to implement new scripts for different models of motors and projectors :)
You can find an example under DLPPrinter/projectors/ and DLPPrinter/motors. As long as you implement the same public functions in your script, your code should work.
Remember to add the name of your motor/projector in dlpGUI.py, and dlpMotorController.py and dlpProjectorController.py

To make the code work:

- open a python terminal in the position of this project.
- create a new venv by running "py -m venv your_name"
- activate the environment "./your_name/Scripts/activate"
- run "pip install -r requirements.txt"