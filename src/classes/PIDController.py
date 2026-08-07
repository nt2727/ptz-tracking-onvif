from simple_pid import PID


class PIDController:
    """
    PTZ Takip için üç eksenli (Pan, Tilt, Zoom) PID kontrolcüsü.
    NovaVision 'bootstrap' aşamasında oluşturulur ve durumunu korur.
    """

    def __init__(self, kp: float, ki: float, kd: float):
        """
        Args:
            kp (float): Oransal kazanç
            ki (float): İntegral kazanç
            kd (float): Türev kazanç
        """
        # Pan (X) ekseni için PID
        self.pid_x = PID(kp, ki, kd, setpoint=0)
        # Tilt (Y) ekseni için PID
        self.pid_y = PID(kp, ki, kd, setpoint=0)
        # Zoom (Z) ekseni için PID
        self.pid_z = PID(kp, ki, kd, setpoint=0)

        # PID çıktılarını -1.0 ile 1.0 arasına sınırla (Kamera normalize hız değerleri)
        self.pid_x.output_limits = (-1, 1)
        self.pid_y.output_limits = (-1, 1)
        self.pid_z.output_limits = (-1, 1)

    def compute(self, error_x: float, error_y: float, error_z: float = 0.0):
        """
        Hata değerlerini alır ve PID'i çalıştırarak -1..1 arası hız değerlerini döndürür.

        Args:
            error_x (float): Pan ekseni hatası (piksel)
            error_y (float): Tilt ekseni hatası (piksel)
            error_z (float): Zoom ekseni hatası (opsiyonel)

        Returns:
            tuple: (speed_x, speed_y, speed_z)
        """
        return (
            self.pid_x(error_x),
            self.pid_y(error_y),
            self.pid_z(error_z)
        )