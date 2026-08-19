from simple_pid import PID


class PIDController:

    def __init__(self, kp: float, ki: float, kd: float):
        self.pid_x = PID(kp, ki, kd, setpoint=0)
        self.pid_y = PID(kp, ki, kd, setpoint=0)
        self.pid_z = PID(kp, ki, kd, setpoint=0)

        self.pid_x.output_limits = (-1, 1)
        self.pid_y.output_limits = (-1, 1)
        self.pid_z.output_limits = (-1, 1)

    def compute(self, error_x: float, error_y: float, error_z: float = 0.0):
        return (
            self.pid_x(error_x),
            self.pid_y(error_y),
            self.pid_z(error_z)
        )