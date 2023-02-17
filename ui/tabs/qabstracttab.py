from dcc.ui import quicwidget

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QAbstractTab(quicwidget.QUicWidget):
    """
    Overload of `QUicWidget` used to outline the structure for alignment tabs.
    """

    # region Properties
    @property
    def scene(self):
        """
        Returns the scene interface.

        :rtype: mpyfactory.MPyFactory
        """

        return self.window().scene
    # endregion

    # region Callbacks
    def sceneChanged(self):
        """
        Callback method that notifies the tab of a scene change.

        :rtype: None
        """

        pass
    # endregion

    # region Methods
    def loadSettings(self, settings):
        """
        Loads the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        pass

    def saveSettings(self, settings):
        """
        Saves the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        pass

    def cwd(self):
        """
        Returns the current working directory.

        :rtype: str
        """

        return self.window().cwd()

    def currentNamespace(self):
        """
        Returns the current namespace.

        :rtype: str
        """

        return self.window().currentNamespace()

    def controllerPatterns(self):
        """
        Returns the controller patterns used for saving poses.

        :rtype: List[str]
        """

        return self.window().controllerPatterns()

    def controllerPriorities(self):
        """
        Returns the controller priorities for setting poses.

        :rtype: List[str]
        """

        return self.window().controllerPriorities()
    # endregion
