# flux++
Home Assistant custome component to let coloured lights folow the day's and circadian rythm

This is heavily based on the original Flux component in Homeassistant: https://home-assistant.io/components/switch.flux/

Improvements:
  - Lights that have their color changed manually will not be updated
  - New service force_update to have all lights in the Flux++ switch 
    which are turned on participate in the future updates again
  - New functionality to listen for newly turned on slights that are 
    part of the Flux++ switch. Newly turned on lights will be updated
    to the flux color and participate in future updates
  - New conf parameter init_on_turn_on to define if newly turned on
    lights shall participate and be reset to the flux color or not
  - It is now possible to call the force_update service specifying 
    one or more entity_ids of the lights that should be updated. 
    If no entities are given, all lights in the flux switch will be 
    updated

Installation:
  To install flux++
   - create a folder custom_components\switch under your Home Assistant config dir
   - download and copy the file flux++.py int this directory
   - add the definition on which switches to include in the flux automatic updates with the following section in configuration.yaml
   
Configuration variables:

- lights (Required) array: List of light entities.
- name (Optional): The name to use when displaying this switch.
- start_time (Optional): The start time. Default to sunrise.
- stop_time (Optional): The stop time. Defaults to 22:00.
- start_colortemp (Optional): The color temperature at the start. Defaults to 4000.
- sunset_colortemp (Optional): The sun set color temperature. Defaults to 3000.
- stop_colortemp (Optional): The color temperature at the end. Defaults to 1900.
- brightness (Optional): The brightness of the lights. Calculated with RGB_to_xy by default.
- disable_brightness_adjust (Optional): If true, brightness will not be adjusted besides color temperature. Defaults to False.
- mode (Optional): Select how color temperature is passed to lights. Valid values are xy, mired and rgb. Defaults to xy.
- transition (Optional): Transition time for the light changes (high values may not be supported by all light models). Defaults to 30.
- interval (Optional): Frequency at which the lights should be updated. Defaults to 30.
- init_on_turn_on (Optional): Defines if a newly turned on light within the Flux Switch will be reset to the Flux color and join in future updates. Defaults to true

Example:

switch:
  - platform: flux++
    disable_brightness_adjust: true
    init_on_turn_on: true
    mode: mired
    transition: 300
    interval: 300
    lights:
      - light.matbord
      - light.stalampa
      - light.bank_tv
      - light.fonster_tv
      - light.vardagsrum_ceiling
      
Shortcomings: 
This has currently only been fully tested with Philips Hue bulbs with the mired color selection mode.
I would love to get feedback from others to knwo if this works with other bulb types
