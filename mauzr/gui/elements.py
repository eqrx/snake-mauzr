""" GUI elements. """
__author__ = "Alexander Sowitzki"

import math
from mauzr.platform.serializer import Bool as BS
from mauzr.gui import TextMixin, ColorStateMixin, RectBackgroundMixin
from mauzr.gui import BaseElement, ColorState
import pygame # pylint: disable=import-error

class AgentIndicator(ColorStateMixin, TextMixin, RectBackgroundMixin,
                     BaseElement):

    """ Indicate the presence of a mauzr agent.

    :param core: Core instance.
    :type core: object
    :param topic: Topic containing the presence information.
    :type topic: str
    :param location: Center of the element.
    :type location: mauzr.gui.Vector
    :param size: Size of the element.
    :type size: mauzr.gui.Vector
    """

    def __init__(self, core, topic, location, size):
        BaseElement.__init__(self, location, size)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, topic.split("/")[-1], size)
        conditions = {ColorState.UNKNOWN: lambda v: v is None,
                      ColorState.ERROR: lambda v: v is False,
                      ColorState.INFORMATION: lambda v: v is True}
        ColorStateMixin.__init__(self, conditions)

        core.mqtt.subscribe(topic, self._on_state_change, BS, 2)
        if topic.split("/")[-1] == core.config.id:
            core.mqtt.connection_listeners.append(self._on_connection_change)

    def _on_connection_change(self, status):
        # In any case, connection change means the value in invalid
        self._update_state(None)
        self.state_acknowledged = False

    def _on_state_change(self, _topic, value):
        # Update state
        self._update_state(value)
        self.state_acknowledged = False

    def _on_click(self):
        # Assume click means acknowledge
        self.state_acknowledged = True


class Indicator(ColorStateMixin, TextMixin, RectBackgroundMixin, BaseElement):
    """ Display for the value of a topic.

    :param core: Core instance.
    :type core: object
    :param topic: Topic to monitor.
    :type topic: str
    :param serializer: Serializer for the topic.
    :type serializer: object
    :param label: Label to prepend the value with. Is separated from \
                 it by ": ".
    :type label: str
    :param fmt: Format to use for displaying the topic value. Is expected to \
                be in curly braces and with implicit position reference. \
                Will be concatenated to the internal format.
    :type fmt: str
    :param state_conditions: Dictionary mapping :class:`mauzr.gui.ColorState` \
                             to functions. The function receives one parameter \
                             and should return True if the value indicates \
                             the mapped state.
    :type state_conditions: dict
    :param timeout: If not None, an update of the topic is expected each \
                    ``timeout`` milliseconds. If a timeout occurs, \
                    the indicator is going into \
                    :class:`mauzr.gui.ColorState.ERROR`.
    :type timeout: int
    :param location: Center of the element.
    :type location: mauzr.gui.Vector
    :param size: Size of the element.
    :type size: mauzr.gui.Vector
    """

    def __init__(self, core, topic, serializer, label, fmt,
                 state_conditions, timeout, location, size):
        BaseElement.__init__(self, location, size)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, label + ": ?", size)
        state_conditions[ColorState.UNKNOWN] = lambda v: v is None
        ColorStateMixin.__init__(self, state_conditions)

        self.state_acknowledged = True
        self._fmt = fmt
        self._label = label
        self._timer = None
        if timeout:
            self._timer = core.scheduler(self._on_timeout, timeout,
                                         single=True).enable()

        core.mqtt.subscribe(topic, self._on_message, serializer, 2)

    def _on_timeout(self):
        # No update, complain
        self._state = ColorState.ERROR
        self.state_acknowledged = False

    def _on_message(self, _topic, value):
        self._update_state(value)
        # Update text
        self._text = self._label + ": " + self._fmt.format(value)
        if self._timer is not None:
            # Delay timeout
            self._timer.enable()

    def _on_click(self):
        # Assume click means acknowledge
        self.state_acknowledged = True

class SimpleController(TextMixin, RectBackgroundMixin, BaseElement):
    """ Controller for sending a value when clicked.

    :param core: Core instance.
    :type core: object
    :param send_topic: Topic to send on.
    :type send_topic: str
    :param cond_topic: Topic that has to be True to send.
    :type cond_topic: str
    :param qos: QoS to use for publish.
    :type qos: int
    :param retain: True if publish shall be retained.
    :type retain: bool
    :param payload: Payload to send.
    :type payload: bool
    :param label: Label to prepend the value with. Is separated from
                 it by ": ".
    :type label: str
    :param location: Center of the element.
    :type location: mauzr.gui.Vector
    :param size: Size of the element.
    :type size: mauzr.gui.Vector
    """

    COLOR_READY = (0, 150, 0)
    """ Color that indicates a tap sends a value. """
    COLOR_NOT_READY = (100, 100, 100)
    """ Color that indicates the condition is not met. """

    def __init__(self, core, send_topic, cond_topic, qos, retain, payload,
                 label, location, size):
        BaseElement.__init__(self, location, size)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, label, size)

        core.mqtt.subscribe(cond_topic, self._on_change, BS, qos)
        core.mqtt.setup_publish(send_topic, BS, qos)

        self._retain = retain
        self._send_topic = send_topic
        self._mqtt = core.mqtt
        self._ready = False
        self._payload = payload

    def _on_change(self, _topic, value):
        self._ready = value

    def _on_click(self):
        if self._ready:
            self._mqtt.publish(self._send_topic, self._payload, self._retain)

    @property
    def _color(self):
        if self._ready:
            return self.COLOR_READY
        return self.COLOR_NOT_READY

class ToggleController(TextMixin, RectBackgroundMixin, BaseElement):
    """ Controller for toggling a values between two states.

    :param core: Core instance.
    :type core: object
    :param topic: Topic to manage.
    :type topic: str
    :param qos: QoS to use for publish.
    :type qos: int
    :param retain: True if publish shall be retained.
    :type retain: bool
    :param label: Label to prepend the value with. Is separated from
                 it by ": ".
    :type label: str
    :param location: Center of the element.
    :type location: mauzr.gui.Vector
    :param size: Size of the element.
    :type size: mauzr.gui.Vector
    """

    COLOR_ON = (150, 150, 0)
    """ Color for on state. """
    COLOR_OFF = (0, 100, 200)
    """ color for off state. """
    COLOR_UNKNOWN = (70, 70, 70)
    """ Color for unknown state. """

    def __init__(self, core, topic, qos, retain, label,
                 location, size):
        BaseElement.__init__(self, location, size)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, label, size)

        core.mqtt.subscribe(topic, self._on_change, BS, qos)
        core.mqtt.setup_publish(topic, BS, qos)

        self._retain = retain
        self._topic = topic
        self._mqtt = core.mqtt
        self._current = None

    def _on_change(self, _topic, value):
        self._current = value

    def _on_click(self):
        self._mqtt.publish(self._topic, not self._current, self._retain)

    @property
    def _color(self):
        if self._current is None:
            return self.COLOR_UNKNOWN
        elif self._current:
            return self.COLOR_ON
        return self.COLOR_OFF

class FeedDisplayer(BaseElement):
    """ Display an image feed.

    :param core: Core instance.
    :type core: object
    :param topic: Topic to receive images by.
    :type topic: str
    :param qos: QoS to use for publish.
    :type qos: int
    :param location: Center of the element.
    :type location: mauzr.gui.Vector
    :param size: Size of the element.
    :type size: mauzr.gui.Vector
    """

    def __init__(self, core, topic, qos, location, size):
        from mauzr.util.image.serializer import Pygame as SurfaceSerializer
        core.mqtt.subscribe(topic, self._on_image,
                            SurfaceSerializer, qos)
        BaseElement.__init__(self, location, size)
        self._image_surface = None
        self._image_rect = None

    def _on_image(self, _topic, surface):
        self._image_surface = pygame.transform.scale(surface, self._size.values)
        self._image_rect = self._image_surface.get_rect()

    def _draw_foreground(self):
        """ Draw the element. """

        if self._image_surface:
            self._surface.blit(self._image_surface, self._image_rect)

class Acceptor(TextMixin, RectBackgroundMixin, BaseElement):
    """ Acknowledge all states via one click.

    :param location: Center of the element.
    :type location: mauzr.gui.Vector
    :param size: Size of the element.
    :type size: mauzr.gui.Vector
    :param panel: Panel to control.
    :type panel: mauzr.gui.panel.Table
    """

    def __init__(self, location, size, panel):
        BaseElement.__init__(self, location, size)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, "Clear", size)
        self._panel = panel

    def _on_click(self):
        # Assume click means acknowledge
        for element in self._panel.elements:
            element.state_acknowledged = True

    @property
    def _color(self):
        """ Color of the element as tuple. """

        return ColorState.INFORMATION.value[0]

class Muter(ColorStateMixin, TextMixin, RectBackgroundMixin, BaseElement):
    """ Mute audio notifications.

    :param location: Center of the element.
    :type location: mauzr.gui.Vector
    :param size: Size of the element.
    :type size: mauzr.gui.Vector
    :param panel: Panel to control.
    :type panel: mauzr.gui.panel.Table
    """

    def __init__(self, location, size, panel):
        BaseElement.__init__(self, location, size)
        RectBackgroundMixin.__init__(self)
        TextMixin.__init__(self, "Mute", size)
        conditions = {ColorState.WARNING: lambda v: v,
                      ColorState.INFORMATION: lambda v: not v}
        ColorStateMixin.__init__(self, conditions)
        self._muted = False
        self._panel = panel

    def _on_click(self):
        # Assume click means acknowledge
        self._muted = not self._muted
        self._update_state(self._muted)
        self._panel.mute(self._muted)

    @property
    def _color(self):
        """ Color of the element as tuple. """

        if self._muted:
            return ColorState.WARNING.value[0]
        return ColorState.INFORMATION.value[0]

class Gauge(RectBackgroundMixin, BaseElement):
    """ Gauge element. """

    def __init__(self, location, size):
        BaseElement.__init__(self, location, size)
        RectBackgroundMixin.__init__(self)

        self._gauge_value = math.pi * 0.5

    def _draw_foreground(self):
        pygame.draw.arc(self._surface, [255, 255, 0], self._surface.get_rect(),
                        0, self._gauge_value, 20)
