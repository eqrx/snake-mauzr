""" Connect with MQTT brokers. """
__author__ = "Alexander Sowitzki"

import ssl
import paho.mqtt.client

class Client:
    """ Use the Paho MQTT implementation to provide MQTT support.

    :param core: Core instance.
    :type core: object
    :param cfgbase: Configuration entry for this unit.
    :type cfgbase: str
    :param kwargs: Keyword arguments that will be merged into the config.
    :type kwargs: dict

    **Configuration:**

        - *client_id*: MQTT client ID (``str``).
        - *status_topic*: Topic to publish information to.
    """

    def __init__(self, core, cfgbase="mqtt", **kwargs):
        cfg = core.config[cfgbase]
        cfg.update(kwargs)

        self._log = core.logger("mqtt-client")
        if "client_id" in cfg:
            client_id = cfg["client_id"]
        else:
            client_id = "-".join(core.config["id"])

        self.client = paho.mqtt.client.Client(client_id=client_id,
                                              clean_session=True)
        self._agent_topic = cfg["status_topic"]
        self.manager = None

        self._subscriptions = {}
        self._publications = {}

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self._keepalive = 30

        self.client.will_set(self._agent_topic, payload=bytearray(b'\x00'),
                             qos=2, retain=True)

    def __enter__(self):
        # Start the connector.

        self.client.loop_start()

    def set_host(self, **kwargs):
        """ Set host to connect to.

        :param kwargs: Host Configuration
        :type kwargs: dict
        """
        self.client.username_pw_set(username=kwargs["user"],
                                    password=kwargs["password"])
        # Fix for library
        # pylint: disable=protected-access
        self.client._ssl_context = None
        if "ca" in kwargs:
            self.client.tls_set(ca_certs=kwargs["ca"],
                                cert_reqs=ssl.CERT_REQUIRED,
                                tls_version=ssl.PROTOCOL_TLSv1_2,
                                ciphers=None)

        self.client.connect_async(kwargs["host"], kwargs["port"],
                                  self._keepalive)

    def __exit__(self, *exc_details):
        # Disconnect and stop connector.

        self.client.publish(self._agent_topic, payload=bytearray(b'\x00'),
                            qos=2, retain=True)
        self.client.loop_stop()
        self.client.disconnect()

    def _on_disconnect(self, *details):
        # Indicate that the client disconnected from the broker.

        self.manager.on_disconnect(*details)

    def _on_connect(self, *details):
        # Indicate that the client connected to the broker.

        self.client.publish(self._agent_topic, payload=bytearray(b'\xff'),
                            qos=2, retain=True)
        self.manager.on_connect(*details)

    def _on_message(self, client, userdata, message):
        # Handle messages received via the mqtt broker.

        # Fetch information and dispatch callback
        topic = message.topic
        payload = message.payload
        self.manager.on_message(topic, payload)


    def subscribe(self, topic, qos):
        """ Subscribe to a topic.

        :param topic: Topic to publish to.
        :type topic: str
        :param qos: QoS level to request.
        :type qos: int
        :returns: Return value from the client.
        :rtype: object
        """

        return self.client.subscribe(topic, qos)

    def publish(self, topic, value, qos, retain):
        """ Publish a value to a topic.

        :param topic: Topic to publish to.
        :type topic: str
        :param value: Value to publish.
        :type value: object
        :param qos: QoS level to use.
        :type qos: int
        :param retain: True if value shall be retained by the server.
        :type retain: bool
        :returns: Return value from the client.
        :rtype: object
        """

        return self.client.publish(topic, value, qos, retain)
