# coding=utf-8
from __future__ import absolute_import, print_function
from octoprint.server import user_permission

import octoprint.plugin
import flask
import RPi.GPIO as GPIO


class GpioControlPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.RestartNeedingPlugin,
):
    mode = None
    active_states = {'active_low': GPIO.LOW, 'active_high': GPIO.HIGH}
    pin_states = {}

    def on_startup(self, *args, **kwargs):
        GPIO.setwarnings(False)

        self.mode = GPIO.getmode()

        if self.mode is None:
            self.mode = GPIO.BCM
            GPIO.setmode(self.mode)

        self._logger.info("Detected GPIO mode: {}".format(self.mode))

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True),
            dict(
                type="sidebar",
                custom_bindings=True,
                template="gpiocontrol_sidebar.jinja2",
                icon="map-signs",
            ),
        ]

    def get_assets(self):
        return dict(
            js=["js/gpiocontrol.js", "js/fontawesome-iconpicker.min.js"],
            css=["css/gpiocontrol.css", "css/fontawesome-iconpicker.min.css"],
        )

    def get_settings_defaults(self):
        return dict(gpio_configurations=[])

    def on_settings_save(self, data):
        for configuration in self._settings.get(["gpio_configurations"]):
            self._logger.info(
                "Cleaned GPIO{}: {},{} ({})".format(
                    configuration["pin"],
                    configuration["active_mode"],
                    configuration["default_state"],
                    configuration["name"],
                )
            )

            pin = self.get_pin_number(int(configuration["pin"]))

            if pin > 0:
                GPIO.cleanup(pin)

        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        self._logger.info("Reloading GPIO pins settings after save")
        self.on_after_startup()

    def on_after_startup(self):
        for configuration in self._settings.get(["gpio_configurations"]):
            self._logger.info(
                "Configured GPIO{}: {},{} ({})".format(
                    configuration["pin"],
                    configuration["active_mode"],
                    configuration["default_state"],
                    configuration["name"],
                )
            )

            pin = self.get_pin_number(int(configuration["pin"]))

            if pin != -1:
                self._setup_pin(pin, configuration["default_state"], configuration["active_mode"])

    def get_api_commands(self):
        return dict(turnGpioOn=["id"], turnGpioOff=["id"], getGpioState=["id"])

    def on_api_command(self, command, data):
        if not user_permission.can():
            return flask.make_response("Insufficient rights", 403)

        configuration = self._settings.get(["gpio_configurations"])[int(data["id"])]
        pin = self.get_pin_number(int(configuration["pin"]))

        if command == "getGpioState":
            return flask.jsonify("" if pin < 0 else self._get_pin_state(pin, configuration))
        elif command == "turnGpioOn":
            if pin > 0:
                self.pin_states[pin] = True
                GPIO.output(pin, self.active_states[configuration["active_mode"]])
                self._logger.info("Turned on GPIO{}".format(configuration["pin"]))
        elif command == "turnGpioOff":
            if pin > 0:
                self.pin_states[pin] = False
                GPIO.output(pin, not self.active_states[configuration["active_mode"]])
                self._logger.info("Turned off GPIO{}".format(configuration["pin"]))

    def on_api_get(self, request):
        states = []
        for configuration in self._settings.get(["gpio_configurations"]):
            pin = self.get_pin_number(int(configuration["pin"]))
            states.append("" if pin < 0 else self._get_pin_state(pin))

        return flask.jsonify(states)

    def get_update_information(self):
        return dict(
            gpiocontrol=dict(
                displayName="GPIO Control",
                displayVersion=self._plugin_version,
                type="github_release",
                user="catgiggle",
                repo="OctoPrint-GpioControl",
                current=self._plugin_version,
                stable_branch=dict(
                    name="Stable",
                    branch="master",
                    comittish=["master"],
                ),
                prerelease_branches=[
                    dict(
                        name="Prerelease",
                        branch="development",
                        comittish=["development", "master"],
                    )
                ],
                pip="https://github.com/catgiggle/OctoPrint-GpioControl/archive/{target_version}.zip",
            )
        )

    PIN_MAPPINGS = [-1, -1, 3, 5, 7, 29, 31, 26, 24, 21, 19, 23, 32, 33, 8, 10, 36, 11, 12, 35, 38, 40, 15, 16, 18, 22, 37, 13]

    def get_pin_number(self, pin):
        if 2 <= pin <= 27:
            if self.mode == GPIO.BCM:
                return pin

            if self.mode == GPIO.BOARD:
                return self.PIN_MAPPINGS[pin]

        return -1

    def _get_pin_state(self, pin, configuration=None):
        if configuration is not None:
            gpio_pin_state = GPIO.input(pin) if configuration["active_mode"] == "active_high" else not GPIO.input(pin)
            if self.pin_states[pin] != gpio_pin_state:
                self._logger.info("Different GPIO states #{}: {},{}".format(pin, gpio_pin_state, self.pin_states[pin]))
        return 'on' if self.pin_states[pin] else 'off'

    def _setup_pin(self, pin, default_state, active_mode):
        GPIO.setup(pin, GPIO.OUT)

        if default_state == "default_on":
            self.pin_states[pin] = True
            GPIO.output(pin, self.active_states[active_mode])
        elif default_state == "default_off":
            self.pin_states[pin] = False
            GPIO.output(pin, not self.active_states[active_mode])


__plugin_name__ = "GPIO Control"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = GpioControlPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
