import random
import numpy as np

class Sandstorm:
    def __init__(self):
        self.pitch_disturbance = 0.0
        self.windspeed = random.uniform(15, 25)  # Moderate sandstorm windspeed is usually 15-25 in m/s

    def apply_effect(self, gyroscope):
        wind_direction = random.choice([-1, 1])  # -1 for forward wind , 1 for backward wind
        # Calculate pitch disturbance based on windspeed and direction
        self.pitch_disturbance = wind_direction * np.interp(self.windspeed, [15, 25], [0, 1]) #pitch disturbance -1 to 1
        gyroscope[1] += self.pitch_disturbance  # Modify the pitch value
        return gyroscope