from DSR_ROBOT2 import set_digital_output, wait

OFF = 0
ON = 1

def grasp():
    set_digital_output(2, OFF)
    set_digital_output(1, ON)
    wait(1)

def release():
    set_digital_output(1, OFF)
    set_digital_output(2, ON)
    wait(1)