## Todo

- Gives drone status in binary format.
- Gyroscope calculation, stable at low altitude.
- Windspeed tilt condition.
- Dust storm affects battery drain.
- Low altitude causes more battery drain, high altitude causes less battery drain (thickness of atm).
- Only calculate time/iteration when speed != 0, i.e, flight time.
- Ground proximity, altitude is at sea level.
- Drone condition detoriates at higher altitude.
- Option to repair drone when its condition is critical at the cost of battery. Drone crashes when condition is 0.
- Drone crashes if user doesn't provide instruction for 2-3 iterations.
- Update tests accordingly.

## Crash conditions implemented

- Battery Drains to 0.
- Altitude becomes negative. Need to incorporate ground proximity level.