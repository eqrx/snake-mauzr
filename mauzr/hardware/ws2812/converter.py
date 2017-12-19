""" Converter for WS2812 leds. """

import mauzr
from mauzr.platform.serializer import Struct
import numpy # pylint: disable=import-error


def convert(core, cfgbase="ws2812", **kwargs):
    """ Converter for WS2812 leds.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict
    """

    cfg = core.config[cfgbase]
    cfg.update(kwargs)

    amount = sum([s["length"] for s in cfg["slices"]])
    core.mqtt.setup_publish(cfg["topic"], None, 0)
    # pylint: disable=no-member
    colors = buf = numpy.zeros(amount*3, dtype=numpy.uint8)
    buf = numpy.zeros(amount*4*3, dtype=numpy.uint8)

    def _on_message(topic, data):
        o = [s["offset"]*3 for s in cfg["slices"] if s["topic"] == topic][0]
        for i in range(0, len(data), 3):
            r, g, b = data[i:i+3]
            colors[o+i:o+i+3] = (int(g*255), int(r*255), int(b*255))

        for i in range(4):
            buf[3-i::4] = (((colors >> (2*i+1)) & 1) * 96 +
                           ((colors >> (2*i)) & 1) * 6 + 136)

        core.mqtt.publish(cfg["topic"], buf.tobytes(), True)

    for slicecfg in cfg["slices"]:
        serializer = Struct("!" + "f" * slicecfg["length"] * 3)
        core.mqtt.subscribe(slicecfg["topic"], _on_message, serializer, 0)

def main():
    """ Main method for the Converter. """
    # Setup core
    core = mauzr.linux("mauzr", "ws2812converter")
    # Setup MQTT
    core.setup_mqtt()
    # Spin up converter
    convert(core)
    # Run core
    core.run()

if __name__ == "__main__":
    main()