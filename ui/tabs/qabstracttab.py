from Qt import QtCore, QtWidgets, QtGui
from abc import abstractmethod
from mpy import mpyscene
from dcc.ui.abstract import qabcmeta

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QAbstractTab(QtWidgets.QWidget, metaclass=qabcmeta.QABCMeta):
    """
    Overload of `QWidget` that outlines poser tab behavior.
    """

    # region Dunderscores
    def __post_init__(self, *args, **kwargs):
        """
        Private method called after an instance has initialized.

        :rtype: None
        """

        self.__setup_ui__(*args, **kwargs)

    @abstractmethod
    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that initializes the user interface.

        :rtype: None
        """

        pass
    # endregion

    # region Properties
    @property
    def scene(self):
        """
        Returns the scene interface.

        :rtype: mpyscene.MPyScene
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

    def customNamespace(self):
        """
        Returns the custom namespace.

        :rtype: str
        """

        return self.window().customNamespace()

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

    def getSortPriority(self, node):
        """
        Returns the sort priority index for the supplied node.

        :type node: mpynode.MPyNode
        :rtype: int
        """

        return self.window().getSortPriority(node)

    def getSelection(self, sort=False):
        """
        Returns the active selection.
        If no nodes are selected then the controller patterns are queried instead!

        :type sort: bool
        :rtype: List[mpynode.MPyNode]
        """

        return self.window().getSelection(sort=sort)

    def controllerPriorities(self):
        """
        Returns the controller priorities for setting poses.

        :rtype: List[str]
        """

        return self.window().controllerPriorities()

    def iterControls(self, visible=False):
        """
        Returns a generator that yields controls from the scene.

        :type visible: bool
        :rtype: Iterator[mpynode.MPyNode]
        """

        return self.window().iterControls(visible=visible)

    def getControls(self, visible=False):
        """
        Returns a list of controls from the scene.

        :type visible: bool
        :rtype: Iterator[mpynode.MPyNode]
        """

        return self.window().getControls(visible=visible)

    def selectControls(self, visible=False):
        """
        Selects any controls that match the active controller patterns.

        :type visible: bool
        :rtype: None
        """

        self.window().selectControls(visible=visible)

    def selectAssociatedControls(self):
        """
        Selects any controls that are in the same display layer.

        :rtype: None
        """

        self.window().selectAssociatedControls()

    def selectOppositeControls(self, replace=True):
        """
        Selects the opposite nodes from the active selection.

        :type replace: bool
        :rtype: None
        """

        self.window().selectOppositeControls(replace=replace)
    # endregion
