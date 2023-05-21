from dcc.json import psonobject

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class RigConfiguration(psonobject.PSONObject):
    """
    Overload of `PSONObject` used to store rig configuration settings.
    """

    # region Dunderscores
    __slots__ = ('_name', '_controllerPatterns', '_controllerPriorities')

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :rtype: None
        """

        # Declare private variables
        #
        self._name = kwargs.get('name', '')
        self._controllerPatterns = kwargs.get('controllerPatterns', [])
        self._controllerPriorities = kwargs.get('controllerPriorities', [])

        # Call parent method
        #
        super(RigConfiguration, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
    @property
    def name(self):
        """
        Getter method that returns the name of the configuration.

        :rtype: str
        """

        return self._name

    @name.setter
    def name(self, name):
        """
        Setter method that updates the name of the configuration.

        :type name: str
        :rtype: None
        """

        self._name = name

    @property
    def controllerPatterns(self):
        """
        Getter method that returns the rig's controller patterns.

        :rtype: List[str]
        """

        return self._controllerPatterns

    @controllerPatterns.setter
    def controllerPatterns(self, controllerPatterns):
        """
        Setter method that updates the rig's controller patterns.

        :type controllerPatterns: List[str]
        :rtype: None
        """

        self._controllerPatterns.clear()
        self._controllerPatterns.extend(controllerPatterns)

    @property
    def controllerPriorities(self):
        """
        Getter method that updates the rig's controller priorities.

        :rtype: List[str]
        """

        return self._controllerPriorities

    @controllerPriorities.setter
    def controllerPriorities(self, controllerPriorities):
        """
        Setter method that updates the rig's controller priorities.

        :type controllerPriorities: List[str]
        :rtype: None
        """

        self._controllerPriorities.clear()
        self._controllerPriorities.extend(controllerPriorities)
    # endregion
