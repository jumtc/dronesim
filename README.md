## Todo

- Gives drone status in binary format. [Asmit]
- Gyroscope calculation, stable at low altitude. [Priyam]
- Windspeed tilt condition. [Priyam]
- Dust storm affects battery drain. [Trishit]
- Low altitude causes more battery drain, high altitude causes less battery drain (thickness of atm). [Trishit]
- Only calculate time/iteration when speed != 0, i.e, flight time. [Samrat]
- Drone condition detoriates at higher altitude. [Samrat]
- Option to repair drone when its condition is critical at the cost of battery. Drone crashes when condition is 0. [Samrat]
- Drone crashes if user doesn't provide instruction for 2-3 iterations. [Shrestha the god killer]
- Update tests accordingly. [AI]

## Crash conditions implemented

- Battery Drains to 0.
- Altitude becomes negative.