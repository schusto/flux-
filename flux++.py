"""
Flux++ for Home-Assistant by Erik Schumann (@schusto)

Improvements:
  - Lights that have their color changed manually will not be updated
  - New service force_update to have all lights in the Flux++ switch 
    which are turned on participate in the future updates again
  - New functionality to listen for newly turned on slights that are 
    part of the Fluxx++ switch. Newly turned on lights will be updated
    to the flux color and participate in future updates
  - New conf parameter init_on_turn_on to define if newly turned on
    lights shall participate and be reset to the flux color or not

Fully based on the Flux component from Home Assistant from
https://home-assistant.io/components/switch.flux/

The original HA idea was taken from https://github.com/KpaBap/hue-flux/
"""

import datetime
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
    is_on, turn_on, VALID_TRANSITION, ATTR_TRANSITION)
from homeassistant.components.switch import DOMAIN, SwitchDevice
from homeassistant.const import (
    CONF_NAME, CONF_PLATFORM, CONF_LIGHTS, CONF_MODE)
from homeassistant.helpers.event import (
    track_time_change, async_track_state_change)

from homeassistant.helpers.sun import get_astral_event_date
from homeassistant.util import slugify
from homeassistant.util.color import (
    color_temperature_to_rgb, color_RGB_to_xy,
    color_temperature_kelvin_to_mired)
from homeassistant.util.dt import now as dt_now

_LOGGER = logging.getLogger(__name__)

CONF_START_TIME = 'start_time'
CONF_STOP_TIME = 'stop_time'
CONF_START_CT = 'start_colortemp'
CONF_SUNSET_CT = 'sunset_colortemp'
CONF_STOP_CT = 'stop_colortemp'
CONF_BRIGHTNESS = 'brightness'
CONF_DISABLE_BRIGTNESS_ADJUST = 'disable_brightness_adjust'
CONF_INIT_ON_TURN_ON = 'init_on_turn_on'
CONF_INTERVAL = 'interval'

MODE_XY = 'xy'
MODE_MIRED = 'mired'
MODE_RGB = 'rgb'
DEFAULT_MODE = MODE_XY
DEPENDENCIES = ['light']


PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_PLATFORM): 'flux++',
    vol.Required(CONF_LIGHTS): cv.entity_ids,
    vol.Optional(CONF_NAME, default="MyFlux"): cv.string,
    vol.Optional(CONF_START_TIME): cv.time,
    vol.Optional(CONF_STOP_TIME, default=datetime.time(22, 0)): cv.time,
    vol.Optional(CONF_START_CT, default=4000):
        vol.All(vol.Coerce(int), vol.Range(min=1000, max=40000)),
    vol.Optional(CONF_SUNSET_CT, default=3000):
        vol.All(vol.Coerce(int), vol.Range(min=1000, max=40000)),
    vol.Optional(CONF_STOP_CT, default=1900):
        vol.All(vol.Coerce(int), vol.Range(min=1000, max=40000)),
    vol.Optional(CONF_BRIGHTNESS):
        vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    vol.Optional(CONF_DISABLE_BRIGTNESS_ADJUST): cv.boolean,
    vol.Optional(CONF_INIT_ON_TURN_ON): cv.boolean,
    vol.Optional(CONF_MODE, default=DEFAULT_MODE):
        vol.Any(MODE_XY, MODE_MIRED, MODE_RGB),
    vol.Optional(CONF_INTERVAL, default=180): cv.positive_int,
    vol.Optional(ATTR_TRANSITION, default=180): VALID_TRANSITION
})





def set_lights_xy(hass, lights, x_val, y_val, brightness, transition, lastcolor):
    """Set color of array of lights."""
    for light in lights:
        if is_on(hass, light):
            states = hass.states.get(light)
            if (lastcolor == 0) or (states.attributes.get('xy_color') == lastcolor):
                turn_on(hass, light,
                        xy_color=[x_val, y_val],
                        brightness=brightness,
                        transition=transition)
    return [x_val, y_val]


def set_lights_temp(hass, lights, mired, brightness, transition, lastcolor):
    """Set color of array of lights."""
    for light in lights:
        if is_on(hass, light):
            states = hass.states.get(light)
            if (lastcolor == 0) or (states.attributes.get('color_temp') == lastcolor):
                turn_on(hass, light,
                        color_temp=int(mired),
                        brightness=brightness,
                        transition=transition)
    return int(mired)


def set_lights_rgb(hass, lights, rgb, transition, lastcolor):
    """Set color of array of lights."""
    for light in lights:
        if is_on(hass, light):
            states = hass.states.get(light)
            if (lastcolor == 0) or (states.attributes.get('rgb_color') == lastcolor):
                turn_on(hass, light,
                    rgb_color=rgb,
                    transition=transition)
    return rgb

def force_light_xy(hass, lights, x_val, y_val, brightness):
    """Set color of light."""
    _LOGGER.debug("force_light_xy called for lights %s, xy color %s, brightness %s",
                lights, [x_val, y_val], brightness)
    if not isinstance(lights, (list, tuple)):
        lights = [lights]
    for light in lights:
        _LOGGER.debug("checking light %s for on state %s", light, is_on(hass, light))
        if is_on(hass, light):
            _LOGGER.debug("Flux forced light xy for %s",
                light)
            turn_on(hass, light,
                    xy_color=[x_val, y_val],
                    brightness=brightness)
    return [x_val, y_val]

def force_light_temp(hass, lights, mired, brightness):
    """Set color of light."""
    _LOGGER.debug("force_light_temp called for lights %s, mired %s, brightness %s",
                lights, mired, brightness)
    if not isinstance(lights, (list, tuple)):
        lights = [lights]
    for light in lights:
        _LOGGER.debug("checking light %s for on state %s", light, is_on(hass, light))
        if is_on(hass, light):
            _LOGGER.debug("Flux forced light temp for %s",
                light)
            turn_on(hass, light,
                    color_temp=int(mired),
                    brightness=brightness)
    return int(mired)

def force_light_rgb(hass, lights, rgb):
    """Set color of light."""
    _LOGGER.debug("force_light_rgb called for lights %s, rgb %s",
                lights, rgb)
    if not isinstance(lights, (list, tuple)):
        lights = [lights]
    for light in lights:
        _LOGGER.debug("checking light %s for on state %s", light, is_on(hass, light))
        if is_on(hass, light):
            _LOGGER.debug("Flux forced light rgb for %s",
                light)
            turn_on(hass, light,
                    rgb_color=rgb)
    return rgb

# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Flux switches."""
    name = config.get(CONF_NAME)
    lights = config.get(CONF_LIGHTS)
    start_time = config.get(CONF_START_TIME)
    stop_time = config.get(CONF_STOP_TIME)
    start_colortemp = config.get(CONF_START_CT)
    sunset_colortemp = config.get(CONF_SUNSET_CT)
    stop_colortemp = config.get(CONF_STOP_CT)
    brightness = config.get(CONF_BRIGHTNESS)
    disable_brightness_adjust = config.get(CONF_DISABLE_BRIGTNESS_ADJUST)
    init_on_turn_on = config.get(CONF_INIT_ON_TURN_ON)
    mode = config.get(CONF_MODE)
    interval = config.get(CONF_INTERVAL)
    transition = config.get(ATTR_TRANSITION)
    last_color = 0
    flux = FluxSwitch(name, hass, lights, start_time, stop_time,
                      start_colortemp, sunset_colortemp, stop_colortemp,
                      brightness, disable_brightness_adjust, mode, interval,
                      transition, last_color, init_on_turn_on)
    add_devices([flux])

    def update(call=None):
        """Update lights."""
        flux.flux_update()

    service_name = slugify("{} {}".format(name, 'update'))
    hass.services.register(DOMAIN, service_name, update)

    def force_update(call=None):
        """Update lights."""
        flux.flux_force_update(call)

    service_name = slugify("{} {}".format(name, 'force_update'))
    hass.services.register(DOMAIN, service_name, force_update)


class FluxSwitch(SwitchDevice):
    """Representation of a Flux switch."""

    def __init__(self, name, hass, lights, start_time, stop_time,
                 start_colortemp, sunset_colortemp, stop_colortemp,
                 brightness, disable_brightness_adjust, mode, interval,
                 transition, last_color, init_on_turn_on):
        """Initialize the Flux switch."""
        self._name = name
        self.hass = hass
        self._lights = lights
        self._start_time = start_time
        self._stop_time = stop_time
        self._start_colortemp = start_colortemp
        self._sunset_colortemp = sunset_colortemp
        self._stop_colortemp = stop_colortemp
        self._brightness = brightness
        self._disable_brightness_adjust = disable_brightness_adjust
        self._mode = mode
        self._interval = interval
        self._transition = transition
        self.unsub_tracker = None
        self._last_color = 0
        self._init_on_turn_on = False

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self.unsub_tracker is not None

    def turn_on(self):
        """Turn on flux."""

        # Make initial update
        self.flux_force_update()

        if self.is_on:
            return

        self.unsub_tracker = track_time_change(
            self.hass, self.flux_update, second=[0, self._interval])
        if self._init_on_turn_on:
            self.unsub_turn_on_trigger = async_track_state_change(self.hass, 
                self._lights, self.flux_force_update_cb, 'off', 'on')
        else:
            self.unsub_turn_on_trigger = None

        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off flux."""
        if self.unsub_tracker is not None:
            self.unsub_tracker()
            self.unsub_tracker = None
        if self.unsub_turn_on_trigger is not None:
            self.unsub_turn_on_trigger()
            self.unsub_turn_on_trigger = None

        self.schedule_update_ha_state()


    def flux_force_update(self, call=None, entity=None):
        """Forced update of given or all the lights using flux."""
        now = dt_now()

        if call is None:
            if entity is None:
                entity_id = self._lights
            else:
                entity_id = entity
        else:
            entity_id = call.data.get("entity_id", self._lights)

        _LOGGER.info("Flux forced update for %s",
            entity_id)


        sunset = get_astral_event_date(self.hass, 'sunset', now.date())
        start_time = self.find_start_time(now)
        stop_time = now.replace(
            hour=self._stop_time.hour, minute=self._stop_time.minute,
            second=0)

        if stop_time <= start_time:
            # stop_time does not happen in the same day as start_time
            if start_time < now:
                # stop time is tomorrow
                stop_time += datetime.timedelta(days=1)
        elif now < start_time:
            # stop_time was yesterday since the new start_time is not reached
            stop_time -= datetime.timedelta(days=1)

        if start_time < now < sunset:
            # Daytime
            time_state = 'day'
            temp_range = abs(self._start_colortemp - self._sunset_colortemp)
            day_length = int(sunset.timestamp() - start_time.timestamp())
            seconds_from_start = int(now.timestamp() - start_time.timestamp())
            percentage_complete = seconds_from_start / day_length
            temp_offset = temp_range * percentage_complete
            if self._start_colortemp > self._sunset_colortemp:
                temp = self._start_colortemp - temp_offset
            else:
                temp = self._start_colortemp + temp_offset
        else:
            # Nightime
            time_state = 'night'

            if now < stop_time:
                if stop_time < start_time and stop_time.day == sunset.day:
                    # we need to use yesterday's sunset time
                    sunset_time = sunset - datetime.timedelta(days=1)
                else:
                    sunset_time = sunset

                # pylint: disable=no-member
                night_length = int(stop_time.timestamp() -
                                   sunset_time.timestamp())
                seconds_from_sunset = int(now.timestamp() -
                                          sunset_time.timestamp())
                percentage_complete = seconds_from_sunset / night_length
            else:
                percentage_complete = 1

            temp_range = abs(self._sunset_colortemp - self._stop_colortemp)
            temp_offset = temp_range * percentage_complete
            if self._sunset_colortemp > self._stop_colortemp:
                temp = self._sunset_colortemp - temp_offset
            else:
                temp = self._sunset_colortemp + temp_offset
        rgb = color_temperature_to_rgb(temp)
        x_val, y_val, b_val = color_RGB_to_xy(*rgb)
        brightness = self._brightness if self._brightness else b_val
        
        if self._mode == MODE_XY:
            _LOGGER.debug("Trying to force update of %s to XY %s, %s", entity_id, x_val, y_val)
            force_light_xy(self.hass, entity_id, x_val,
                          y_val, brightness)
            new_color_xy = set_lights_xy(self.hass, self._lights, x_val,
                              y_val, brightness, self._transition, self._last_color)
            _LOGGER.info("Lights updated to x:%s y:%s brightness:%s, %s%% "
                         "of %s cycle complete at %s", x_val, y_val,
                         brightness, round(
                             percentage_complete * 100), time_state, now)
            self._last_color = new_color_xy
        elif self._mode == MODE_RGB:
            force_light_rgb(self.hass, entity_id, rgb)
            new_color_rgb = set_lights_rgb(self.hass, self._lights, rgb, self._transition, self._last_color)
            _LOGGER.info("Lights updated to rgb:%s, %s%% "
                         "of %s cycle complete at %s", rgb,
                         round(percentage_complete * 100), time_state, now)
            self._last_color = new_color_rgb
        else:
            # Convert to mired and clamp to allowed values
            mired = color_temperature_kelvin_to_mired(temp)
            _LOGGER.debug("Trying to force update of %s to mired %s", entity_id, mired)
            force_light_temp(self.hass, entity_id, mired, brightness)
            new_colortemp = set_lights_temp(self.hass, self._lights, mired, brightness,
                            self._transition, self._last_color)
            _LOGGER.info("Lights updated from %s to mired:%s brightness:%s, %s%% "
                         "of %s cycle complete at %s", self._last_color, mired, brightness,
                         round(percentage_complete * 100), time_state, now)
            self._last_color = new_colortemp

    def flux_update(self, now=None):
        """Update all the lights using flux."""
        if now is None:
            now = dt_now()

        sunset = get_astral_event_date(self.hass, 'sunset', now.date())
        start_time = self.find_start_time(now)
        stop_time = now.replace(
            hour=self._stop_time.hour, minute=self._stop_time.minute,
            second=0)

        if stop_time <= start_time:
            # stop_time does not happen in the same day as start_time
            if start_time < now:
                # stop time is tomorrow
                stop_time += datetime.timedelta(days=1)
        elif now < start_time:
            # stop_time was yesterday since the new start_time is not reached
            stop_time -= datetime.timedelta(days=1)

        if start_time < now < sunset:
            # Daytime
            time_state = 'day'
            temp_range = abs(self._start_colortemp - self._sunset_colortemp)
            day_length = int(sunset.timestamp() - start_time.timestamp())
            seconds_from_start = int(now.timestamp() - start_time.timestamp())
            percentage_complete = seconds_from_start / day_length
            temp_offset = temp_range * percentage_complete
            if self._start_colortemp > self._sunset_colortemp:
                temp = self._start_colortemp - temp_offset
            else:
                temp = self._start_colortemp + temp_offset
        else:
            # Nightime
            time_state = 'night'

            if now < stop_time:
                if stop_time < start_time and stop_time.day == sunset.day:
                    # we need to use yesterday's sunset time
                    sunset_time = sunset - datetime.timedelta(days=1)
                else:
                    sunset_time = sunset

                # pylint: disable=no-member
                night_length = int(stop_time.timestamp() -
                                   sunset_time.timestamp())
                seconds_from_sunset = int(now.timestamp() -
                                          sunset_time.timestamp())
                percentage_complete = seconds_from_sunset / night_length
            else:
                percentage_complete = 1

            temp_range = abs(self._sunset_colortemp - self._stop_colortemp)
            temp_offset = temp_range * percentage_complete
            if self._sunset_colortemp > self._stop_colortemp:
                temp = self._sunset_colortemp - temp_offset
            else:
                temp = self._sunset_colortemp + temp_offset
        rgb = color_temperature_to_rgb(temp)
        x_val, y_val, b_val = color_RGB_to_xy(*rgb)
        brightness = self._brightness if self._brightness else b_val
        if self._disable_brightness_adjust:
            brightness = None
        if self._mode == MODE_XY:
            new_color_xy = set_lights_xy(self.hass, self._lights, x_val,
                          y_val, brightness, self._transition, self._last_color)
            _LOGGER.info("Lights updated to x:%s y:%s brightness:%s, %s%% "
                         "of %s cycle complete at %s", x_val, y_val,
                         brightness, round(
                             percentage_complete * 100), time_state, now)
            self._last_color = new_color_xy
        elif self._mode == MODE_RGB:
            new_color_rgb = set_lights_rgb(self.hass, self._lights, rgb, self._transition, self._last_color)
            _LOGGER.info("Lights updated to rgb:%s, %s%% "
                         "of %s cycle complete at %s", rgb,
                         round(percentage_complete * 100), time_state, now)
            self._last_color = new_color_xy
        else:
            # Convert to mired and clamp to allowed values
            mired = color_temperature_kelvin_to_mired(temp)
            new_colortemp = set_lights_temp(self.hass, self._lights, mired, brightness,
                            self._transition, self._last_color)
            _LOGGER.info("Lights updated from %s to mired:%s brightness:%s, %s%% "
                         "of %s cycle complete at %s", self._last_color, mired, brightness,
                         round(percentage_complete * 100), time_state, now)
            self._last_color = new_colortemp

    def find_start_time(self, now):
        """Return sunrise or start_time if given."""
        if self._start_time:
            sunrise = now.replace(
                hour=self._start_time.hour, minute=self._start_time.minute,
                second=0)
        else:
            sunrise = get_astral_event_date(self.hass, 'sunrise', now.date())
        return sunrise


    def flux_force_update_cb(self, entity, old_state, new_state):
        _LOGGER.info("Flux Callback for %s triggered for entity %s",
            self, entity)
        call = None
        self.flux_force_update(call, entity)
