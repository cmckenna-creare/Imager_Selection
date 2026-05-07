from typing import Optional
import numpy as np

### All lengths are in mm. 

class Camera:
    def __init__(self, res_x:int, res_y:int, pp:float, fps_max:Optional[float]=None):
        self.res_x = res_x
        self.res_y = res_y
        self.pp=pp
        self.fps_max = fps_max

        self.calc_sensor_format()

    def get_sensor_wh(self):
        return [self.res_x*self.pp, self.res_y*self.pp]
    
    def calc_sensor_format(self):
        [w,h] = self.get_sensor_wh()
        d = np.sqrt(w**2+h**2)
        self.sensor_format = d/16


class Lens:
    def __init__(self, focal_length:float, sensor_format_max:float, f_num:tuple, working_distance:tuple):
        self.focal_length = focal_length
        self.sensor_format_max = sensor_format_max
        self.f_num = f_num
        self.working_distance = working_distance


class Imager():
    def __init__(self,camera:Camera,lens:Lens):
        self.camera = camera
        self.Lens = lens
