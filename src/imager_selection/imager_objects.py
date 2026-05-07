from typing import Optional
import numpy as np

# All lengths are in mm.


class Camera:
    def __init__(self, res_x: int, res_y: int, pp: float, fps_max: Optional[float] = None):
        """Initialize a camera sensor.

        Args:
            res_x: Horizontal resolution in pixels. Must be positive.
            res_y: Vertical resolution in pixels. Must be positive.
            pp: Pixel pitch in mm. Must be positive.
            fps_max: Maximum frame rate in frames per second. Must be positive if provided.
        """
        if res_x <= 0 or not isinstance(res_x, int):
            raise ValueError(f"res_x must be a positive integer, got {res_x!r}")
        if res_y <= 0 or not isinstance(res_y, int):
            raise ValueError(f"res_y must be a positive integer, got {res_y!r}")
        if pp <= 0:
            raise ValueError(f"pp (pixel pitch) must be positive, got {pp!r}")
        if fps_max is not None and fps_max <= 0:
            raise ValueError(f"fps_max must be positive, got {fps_max!r}")

        self.res_x = res_x
        self.res_y = res_y
        self.pp = pp
        self.fps_max = fps_max

        self.calc_sensor_format()

    def get_sensor_wh(self) -> list[float]:
        """Return sensor width and height in mm as [width, height]."""
        return [self.res_x * self.pp, self.res_y * self.pp]

    def calc_sensor_format(self) -> None:
        """Compute and store sensor format as diagonal / 16 in mm."""
        [w, h] = self.get_sensor_wh()
        d = np.sqrt(w**2 + h**2)
        self.sensor_format = d / 16


class Lens:
    def __init__(self, focal_length: float, sensor_format_max: float, f_num: tuple, working_distance: tuple):
        """Initialize a lens.

        Args:
            focal_length: Focal length in mm. Must be positive.
            sensor_format_max: Maximum supported sensor format (diagonal / 16) in mm. Must be positive.
            f_num: (min, max) f-number range. Both values must be positive and min <= max.
            working_distance: (min, max) working distance range in mm. Both values must be positive and min <= max.
        """
        if focal_length <= 0:
            raise ValueError(f"focal_length must be positive, got {focal_length!r}")
        if sensor_format_max <= 0:
            raise ValueError(f"sensor_format_max must be positive, got {sensor_format_max!r}")
        if len(f_num) != 2 or f_num[0] <= 0 or f_num[1] <= 0 or f_num[0] > f_num[1]:
            raise ValueError(f"f_num must be a (min, max) tuple with positive values and min <= max, got {f_num!r}")
        if len(working_distance) != 2 or working_distance[0] <= 0 or working_distance[1] <= 0 or working_distance[0] > working_distance[1]:
            raise ValueError(f"working_distance must be a (min, max) tuple with positive values and min <= max, got {working_distance!r}")

        self.focal_length = focal_length
        self.sensor_format_max = sensor_format_max
        self.f_num = f_num
        self.working_distance = working_distance


class Imager:
    def __init__(self, camera: Camera, lens: Lens):
        """Initialize an imager pairing a camera sensor with a lens.

        Args:
            camera: Camera instance.
            lens: Lens instance.
        """
        if not isinstance(camera, Camera):
            raise TypeError(f"camera must be a Camera instance, got {type(camera).__name__!r}")
        if not isinstance(lens, Lens):
            raise TypeError(f"lens must be a Lens instance, got {type(lens).__name__!r}")

        self.camera = camera
        self.lens = lens
