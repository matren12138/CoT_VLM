# LLM-CARLA_BRIDGE

### TO-DO

1. Let LLM directly control vehicle, core codes below: FYI, check auto-pilot in control_vehicles.py

```python
def _parse_vehicle_keys(self, keys, milliseconds):
    if keys[K_UP] or keys[K_w]:
        if not self._ackermann_enabled:
            self._control.throttle = min(self._control.throttle + 0.1, 1.00)
        else:
            self._ackermann_control.speed += round(milliseconds * 0.005, 2) * self._ackermann_reverse
    else:
        if not self._ackermann_enabled:
            self._control.throttle = 0.0
    if keys[K_DOWN] or keys[K_s]:
        if not self._ackermann_enabled:
            self._control.brake = min(self._control.brake + 0.2, 1)
        else:
            self._ackermann_control.speed -= min(abs(self._ackermann_control.speed), round(milliseconds * 0.005, 2)) * self._ackermann_reverse
            self._ackermann_control.speed = max(0, abs(self._ackermann_control.speed)) * self._ackermann_reverse
    else:
        if not self._ackermann_enabled:
            self._control.brake = 0

    steer_increment = 5e-4 * milliseconds
    if keys[K_LEFT] or keys[K_a]:
        if self._steer_cache > 0:
            self._steer_cache = 0
        else:
            self._steer_cache -= steer_increment
    elif keys[K_RIGHT] or keys[K_d]:
        if self._steer_cache < 0:
            self._steer_cache = 0
        else:
            self._steer_cache += steer_increment
    else:
        self._steer_cache = 0.0
    self._steer_cache = min(0.7, max(-0.7, self._steer_cache))
    if not self._ackermann_enabled:
        self._control.steer = round(self._steer_cache, 1)
        self._control.hand_brake = keys[K_SPACE]
    else:
        self._ackermann_control.steer = round(self._steer_cache, 1)
```