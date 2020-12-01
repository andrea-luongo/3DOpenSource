from clearpath.ClearpathSCSK import ClearpathSCSK


if __name__ == "__main__":
    motor = ClearpathSCSK()
    is_connected, ports_count, nodes_count = motor.connect_motor()
    building_plate = 0
    wiper = 1
    # Building plate
    motor.set_node_parameters(node=building_plate, spindle_pitch_microns=4000, steps_per_revolution=6400, axis_orientation=-1)
    # Wiper
    motor.set_node_parameters(node=wiper, spindle_pitch_microns=4000, steps_per_revolution=6400, axis_orientation=1)
    # if is_connected:
    #     ## GET MOTOR POSITION
    #     motor.print_motor_position(building_plate)
    #     ## HOME MOTOR
    #     motor.home_building_plate(building_plate)
    #     ## MOVE MOTOR RELATIVE TO CURRENT POSITION
    #     motor.move_building_plate(distance_mm=10, feed_rate_mm_min=300, node=building_plate)
    #
    #     motor.print_motor_position(building_plate)
    #     ## MOVE MOTOR TO ABSOLUTE POSITION
    #     motor.move_building_plate(distance_mm=10, feed_rate_mm_min=300, is_relative=False, node=building_plate)
    #     # motor.print_motor_position(building_plate)
    #     # motor.print_motor_position(building_plate)
    #
    #     # motor.print_motor_position(wiper)
    #     # motor.move_building_plate(distance_mm=10, feed_rate_mm_min=300, node=wiper)
    #     # motor.print_motor_position(wiper)
    #     # motor.move_building_plate(distance_mm=10, feed_rate_mm_min=300, is_relative=False, node=wiper)
    #     # motor.print_motor_position(wiper)
    #     # motor.home_building_plate(wiper)
    #     # motor.print_motor_position(wiper)
    motor.disconnect_motor()

