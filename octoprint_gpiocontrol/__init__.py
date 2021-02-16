# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.server
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
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

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
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        for configuration in self._settings.get(["gpio_configurations"]):
            self._logger.info(
                "Reconfigured GPIO{}: {},{} ({})".format(
                    configuration["pin"],
                    configuration["active_mode"],
                    configuration["default_state"],
                    configuration["name"],
                )
            )

            GPIO.setup(int(configuration["pin"]), GPIO.OUT)

            if configuration["active_mode"] == "active_low":
                if configuration["default_state"] == "default_on":
                    GPIO.output(int(configuration["pin"]), GPIO.LOW)
                elif configuration["default_state"] == "default_off":
                    GPIO.output(int(configuration["pin"]), GPIO.HIGH)
            elif configuration["active_mode"] == "active_high":
                if configuration["default_state"] == "default_on":
                    GPIO.output(int(configuration["pin"]), GPIO.HIGH)
                elif configuration["default_state"] == "default_off":
                    GPIO.output(int(configuration["pin"]), GPIO.LOW)

    def on_after_startup(self):
        self._logger.info("GpioControl started")

        for configuration in self._settings.get(["gpio_configurations"]):
            self._logger.info(
                "Configured GPIO{}: {},{} ({})".format(
                    configuration["pin"],
                    configuration["active_mode"],
                    configuration["default_state"],
                    configuration["name"],
                )
            )

            GPIO.setup(int(configuration["pin"]), GPIO.OUT)

            if configuration["active_mode"] == "active_low":
                if configuration["default_state"] == "default_on":
                    GPIO.output(int(configuration["pin"]), GPIO.LOW)
                elif configuration["default_state"] == "default_off":
                    GPIO.output(int(configuration["pin"]), GPIO.HIGH)
            elif configuration["active_mode"] == "active_high":
                if configuration["default_state"] == "default_on":
                    GPIO.output(int(configuration["pin"]), GPIO.HIGH)
                elif configuration["default_state"] == "default_off":
                    GPIO.output(int(configuration["pin"]), GPIO.LOW)

    def is_api_adminonly(self):
        return True

    def get_api_commands(self):
        return dict(turnGpioOn=["id"], turnGpioOff=["id"], getGpioState=["id"])

    def on_api_get(self, request):
        return self.on_api_command("getGpioState", [])

    def on_api_command(self, command, data):
        configuration = self._settings.get(["gpio_configurations"])[int(data["id"])]

        if command == "getGpioState":
            if configuration["active_mode"] == "active_low":
                return flask.jsonify(
                    "off" if GPIO.input(int(configuration["pin"])) else "on"
                )
            elif configuration["active_mode"] == "active_high":
                return flask.jsonify(
                    "on" if GPIO.input(int(configuration["pin"])) else "off"
                )
        elif command == "turnGpioOn":
            self._logger.info("Turned on GPIO{}".format(configuration["pin"]))

            if configuration["active_mode"] == "active_low":
                GPIO.output(int(configuration["pin"]), GPIO.LOW)
            elif configuration["active_mode"] == "active_high":
                GPIO.output(int(configuration["pin"]), GPIO.HIGH)
        elif command == "turnGpioOff":
            self._logger.info("Turned off GPIO{}".format(configuration["pin"]))

            if configuration["active_mode"] == "active_low":
                GPIO.output(int(configuration["pin"]), GPIO.HIGH)
            elif configuration["active_mode"] == "active_high":
                GPIO.output(int(configuration["pin"]), GPIO.LOW)

    def get_update_information(self):
        return dict(
            gpiocontrol=dict(
                displayName="GPIO Control",
                displayVersion=self._plugin_version,
                type="github_release",
                user="catgiggle",
                repo="OctoPrint-GpioControl",
                current=self._plugin_version,
                pip="https://github.com/catgiggle/OctoPrint-GpioControl/archive/{target_version}.zip",
            )
        )


__plugin_name__ = "GPIO Control"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = GpioControlPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
