import os
import webbrowser

from maya.api import OpenMaya as om
from mpy import mpyscene, mpynode
from Qt import QtCore, QtWidgets, QtGui, QtCompat
from six import string_types, integer_types
from fnmatch import fnmatchcase
from dcc.python import stringutils
from dcc.ui import quicwindow
from dcc.decorators.staticinitializer import staticInitializer
from dcc.decorators.classproperty import classproperty
from dcc.maya.decorators.undo import undo
from . import resources
from ..libs import rigutils
from ..libs import rigconfiguration

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def onSceneChanged(*args, **kwargs):
    """
    Callback method for any scene IO changes.

    :rtype: None
    """

    # Check if instance exists
    #
    instance = QEzPoser.getInstance()

    if instance is None:

        return

    # Evaluate if instance is still valid
    #
    if QtCompat.isValid(instance):

        instance.sceneChanged(*args, **kwargs)

    else:

        log.warning('Unable to process scene changed callback!')


def selectControls(visible=False):
    """
    Selects animatable controls using the current rig configuration.

    :type visible: bool
    :rtype: None
    """

    # Check if instance exists
    #
    instance = QEzPoser.getInstance()

    if instance is None:

        return

    # Evaluate if instance is still valid
    #
    if QtCompat.isValid(instance):

        instance.selectControls(visible=visible)

    else:

        log.warning('Unable to process scene changed callback!')


@staticInitializer
class QEzPoser(quicwindow.QUicWindow):
    """
    Overload of `QUicWindow` used to edit poses when animating.
    """

    # region Signals
    cwdChanged = QtCore.Signal(str)
    # endregion

    # region Dunderscores
    __scene__ = None
    __configurations__ = []
    __configuration__ = None
    __namespace__ = ''

    @classmethod
    def __static_init__(cls, *args, **kwargs):
        """
        Private method called after this class has been initialized.

        :rtype: None
        """

        # Store reference to scene interface
        #
        cls.__scene__ = mpyscene.MPyScene.getInstance(asWeakReference=True)

        # Load rig configurations
        #
        settings = cls.getSettings()
        configIndex = settings.value('editor/currentConfiguration', defaultValue=-1)

        cls.__configurations__ = rigutils.loadConfigurations()
        cls.__configuration__ = cls.__configurations__[configIndex]

        # Load user namespaces
        #
        cls.__namespace__ = settings.value('editor/customNamespace', defaultValue='')

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :key parent: QtWidgets.QWidget
        :key flags: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        super(QEzPoser, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._cwd = kwargs.get('cwd', self.scene.projectPath)
        self._callbackId = None

        # Declare public variables
        #
        self.tabControl = None
        self.libraryTab = None
        self.plotterTab = None
        self.alignTab = None
        self.mocapTab = None

        self.fileMenu = None
        self.setProjectFolderAction = None

        self.settingsMenu = None
        self.changeRigConfigurationAction = None
        self.rigConfigurationAction = None
        self.namespaceSection = None
        self.defaultNamespaceAction = None
        self.namespaceActionGroup = None
        self.namespaceSeparator = None

        self.helpMenu = None
        self.usingEzPoserAction = None
    # endregion

    # region Properties
    @classproperty
    def scene(cls):
        """
        Returns the scene interface.

        :rtype: mpyscene.MPyScene
        """

        return cls.__scene__()

    @classproperty
    def configurations(cls):
        """
        Returns a list of active rig configurations.

        :rtype: List[rigconfiguration.RigConfiguration]
        """

        return cls.__configurations__
    # endregion

    # region Callbacks
    def sceneChanged(self, *args, **kwargs):
        """
        Notifies all tabs of a scene change.

        :key clientData: Any
        :rtype: None
        """

        self.invalidateNamespaces()

        for tab in self.iterTabs():

            tab.sceneChanged()
    # endregion

    # region Events
    def showEvent(self, event):
        """
        Event method called after the window has been shown.

        :type event: QtGui.QShowEvent
        :rtype: None
        """

        # Call parent method
        #
        super(QEzPoser, self).showEvent(event)

        # Add scene callback
        #
        self._callbackId = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen, onSceneChanged)
        self.sceneChanged()

    def closeEvent(self, event):
        """
        Event method called after the window has been closed.

        :type event: QtGui.QCloseEvent
        :rtype: None
        """

        # Call parent method
        #
        super(QEzPoser, self).closeEvent(event)

        # Remove scene callback
        #
        om.MSceneMessage.removeCallback(self._callbackId)
    # endregion

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QEzPoser, self).postLoad(*args, **kwargs)

        # Add file menu actions
        #
        self.setProjectFolderAction = QtWidgets.QAction('Set Project Folder', parent=self.fileMenu)
        self.setProjectFolderAction.setObjectName('setProjectFolderAction')
        self.setProjectFolderAction.triggered.connect(self.on_setProjectFolderAction_triggered)

        self.fileMenu.addAction(self.setProjectFolderAction)

        # Add settings menu actions
        #
        self.rigConfigurationAction = QtWidgets.QAction('Rig:', parent=self.settingsMenu)
        self.rigConfigurationAction.setObjectName('rigConfigurationAction')
        self.rigConfigurationAction.setEnabled(False)

        self.changeRigConfigurationAction = QtWidgets.QAction('Change Rig Configuration', parent=self.settingsMenu)
        self.changeRigConfigurationAction.setObjectName('changeRigConfigurationAction')
        self.changeRigConfigurationAction.triggered.connect(self.on_changeRigConfigurationAction_triggered)

        self.namespaceActionGroup = QtWidgets.QActionGroup(self.settingsMenu)
        self.namespaceActionGroup.setObjectName('namespaceActionGroup')
        self.namespaceActionGroup.setExclusive(True)

        self.namespaceSection = QtWidgets.QAction('Namespaces:', parent=self.settingsMenu)
        self.namespaceSection.setObjectName('namespaceSection')
        self.namespaceSection.setSeparator(True)

        self.namespaceSeparator = QtWidgets.QAction('', parent=self.settingsMenu)
        self.namespaceSeparator.setObjectName('namespaceSeparator')
        self.namespaceSeparator.setSeparator(True)

        self.settingsMenu.addActions(
            [
                self.rigConfigurationAction,
                self.changeRigConfigurationAction,
                self.namespaceSection,
                self.namespaceSeparator
            ]
        )

        # Add help menu actions
        #
        self.usingEzPoserAction = QtWidgets.QAction("Using Ez'Poser", parent=self.settingsMenu)
        self.usingEzPoserAction.setObjectName('usingEzPoserAction')
        self.usingEzPoserAction.triggered.connect(self.on_usingEzPoserAction_triggered)

        self.helpMenu.addAction(self.usingEzPoserAction)

    def loadSettings(self, settings):
        """
        Loads the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QEzPoser, self).loadSettings(settings)

        # Load user preferences
        #
        self.tabControl.setCurrentIndex(settings.value('editor/currentTabIndex', defaultValue=0))
        self.setCwd(settings.value('editor/cwd', defaultValue=self.scene.projectPath))
        self.setCurrentConfiguration(settings.value('editor/currentConfiguration', defaultValue=-1))

        # Load tab settings
        #
        for tab in self.iterTabs():

            tab.loadSettings(settings)

    def saveSettings(self, settings):
        """
        Saves the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QEzPoser, self).saveSettings(settings)

        # Save user preferences
        #
        settings.setValue('editor/currentTabIndex', self.currentTabIndex())
        settings.setValue('editor/cwd', self.cwd())
        settings.setValue('editor/currentConfiguration', self.configurations.index(self.currentConfiguration()))
        settings.setValue('editor/customNamespace', self.currentNamespace())

        # Save tab settings
        #
        for tab in self.iterTabs():

            tab.saveSettings(settings)

    def currentTab(self):
        """
        Returns the tab widget that is currently open.

        :rtype: QAbstractTab
        """

        return self.tabControl.currentWidget()

    def currentTabIndex(self):
        """
        Returns the tab index that currently open.

        :rtype: int
        """

        return self.tabControl.currentIndex()

    def iterTabs(self):
        """
        Returns a generator that yields tab widgets.

        :rtype: Iterator[QtWidget.QWidget]
        """

        # Iterate through tab control
        #
        for i in range(self.tabControl.count()):

            # Check if widget is valid
            #
            widget = self.tabControl.widget(i)

            if QtCompat.isValid(widget):

                yield widget

            else:

                continue

    def cwd(self):
        """
        Returns the current working directory.

        :rtype: str
        """

        return self._cwd

    def setCwd(self, cwd):
        """
        Updates the current working directory.

        :type cwd: str
        :rtype: None
        """

        # Check if path is valid
        #
        if stringutils.isNullOrEmpty(cwd):

            return

        # Check if directory exists
        #
        if os.path.isdir(cwd) and os.path.isabs(cwd):

            self._cwd = os.path.normpath(cwd)
            self.cwdChanged.emit(self._cwd)

    @classmethod
    def currentNamespace(cls):
        """
        Returns the current namespace.

        :rtype: str
        """

        return cls.__namespace__

    @classmethod
    def currentConfiguration(cls):
        """
        Returns the current rig configuration.

        :rtype: rigconfiguration.RigConfiguration
        """

        return cls.__configuration__

    @classmethod
    def setCurrentConfiguration(cls, configuration):
        """
        Updates the current rig configuration.

        :type configuration: Union[int, str, rigconfiguration.RigConfiguration]
        :rtype: None
        """

        # Evaluate configuration type
        #
        if isinstance(configuration, integer_types):

            configuration = cls.__configurations__[configuration]
            cls.__configuration__ = configuration

        elif isinstance(configuration, string_types):

            configurations = [config.name for config in cls.__configurations__]
            index = configurations.index(configuration)
            configuration = cls.__configurations__[index]

            cls.__configuration__ = configuration

        elif isinstance(configuration, rigconfiguration.RigConfiguration):

            cls.__configuration__ = configuration

        else:

            raise TypeError(f'setCurrentConfiguration() expects a valid configuration ({type(configuration).__name__} given)!')

        # Update rig configuration action
        #
        instance = cls.getInstance()

        if instance is not None:

            instance.rigConfigurationAction.setText(f'Rig: {configuration.name}')

    @classmethod
    def controllerPatterns(cls):
        """
        Returns the controller patterns used for saving poses.

        :rtype: List[str]
        """

        return cls.__configuration__.controllerPatterns

    @classmethod
    def controllerPriorities(cls):
        """
        Returns the controller priorities for setting poses.

        :rtype: List[str]
        """

        return cls.__configuration__.controllerPriorities

    @classmethod
    def getSortPriority(cls, node):
        """
        Returns the sort priority index for the supplied node.

        :type node: mpynode.MPyNode
        :rtype: int
        """

        priorities = cls.controllerPriorities()
        lastIndex = len(priorities)

        matches = [i for (i, pattern) in enumerate(priorities) if fnmatchcase(node.name(), pattern)]
        numMatches = len(matches)

        if numMatches > 0:

            return matches[0]  # Use the first known match!

        else:

            return lastIndex  # Send to end of list...

    def getSelection(self, sort=False):
        """
        Returns the active selection.
        If no nodes are selected then the controller patterns are queried instead!

        :type sort: bool
        :rtype: List[mpynode.MPyNode]
        """

        # Evaluate active selection
        #
        selection = self.scene.selection(apiType=om.MFn.kTransform)
        selectionCount = len(selection)

        if selectionCount == 0:

            selection = self.getControls()

        # Check if selection requires sorting
        #
        if sort:

            return sorted(selection, key=self.getSortPriority)

        else:

            return selection

    def clearNamespaces(self):
        """
        Clears all namespace actions from the action group.

        :rtype: None
        """

        actions = self.namespaceActionGroup.actions()

        for (i, action) in reversed(list(enumerate(actions))):

            self.namespaceActionGroup.removeAction(action)
            self.settingsMenu.removeAction(action)

            action.deleteLater()

    def invalidateNamespaces(self):
        """
        Rebuilds the namespace action group based on the current scene's namespaces.

        :rtype: None
        """

        # Remove pre-existing namespaces
        #
        self.clearNamespaces()

        # Iterate through namespaces
        #
        currentNamespace = self.currentNamespace()
        namespaces = self.getNamespaces()

        for (i, namespace) in enumerate(namespaces):

            # Create action
            #
            title = ':' if stringutils.isNullOrEmpty(namespace) else namespace

            action = QtWidgets.QAction(title, parent=self.settingsMenu)
            action.setObjectName(f'namespace{str(i + 1).zfill(2)}Action')
            action.setWhatsThis(namespace)
            action.setCheckable(True)
            action.triggered.connect(self.on_namespaceAction_triggered)

            self.namespaceActionGroup.addAction(action)

            # Check if action should be checked
            #
            if namespace == currentNamespace:

                action.setChecked(True)

        # Insert namespace actions
        #
        self.settingsMenu.insertActions(self.namespaceSeparator, self.namespaceActionGroup.actions())

    @classmethod
    def getNamespaces(cls):
        """
        Returns a list of namespaces from the current scene file.

        :rtype: List[str]
        """

        # Check if custom namespace should be appended
        #
        namespaces = ['']
        namespaces.extend(om.MNamespace.getNamespaces(recurse=True))

        if cls.__namespace__ not in namespaces:

            namespaces.append(cls.__namespace__)

        return namespaces

    def iterControls(self, visible=False):
        """
        Returns a generator that yields controls from the scene.

        :type visible: bool
        :rtype: Iterator[mpynode.MPyNode]
        """

        # Iterate through nodes
        #
        namespace = self.currentNamespace()
        patterns = [f'{namespace}:{pattern}' for pattern in self.controllerPatterns()]

        for node in self.scene.iterNodesByPattern(*patterns, apiType=om.MFn.kTransform):

            # Check if this is a constraint
            #
            if any(map(node.hasFn, (om.MFn.kConstraint, om.MFn.kPluginConstraintNode))):

                continue

            # Check if invisible nodes should be skipped
            #
            isVisible = node.dagPath().isVisible()

            if visible and not isVisible:

                continue

            # Yield controller
            #
            yield node

    def getControls(self, visible=False):
        """
        Returns a list of controls from the scene.

        :type visible: bool
        :rtype: Iterator[mpynode.MPyNode]
        """

        return list(self.iterControls(visible=visible))

    @undo(state=False)
    def selectControls(self, visible=False):
        """
        Selects any controls that match the active controller patterns.

        :type visible: bool
        :rtype: None
        """

        nodes = [node.object() for node in self.iterControls(visible=visible)]
        self.scene.setSelection(nodes)
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_setProjectFolderAction_triggered(self, checked=False):
        """
        Slot method for the setProjectFolderAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for save path
        #
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
            caption='Select Project Folder',
            dir=self.cwd(),
            options=QtWidgets.QFileDialog.ShowDirsOnly
        )

        # Check if path is valid
        # A null value will be returned if the user exited
        #
        if os.path.isdir(directory) and os.path.exists(directory):

            self.setCwd(directory)

        else:

            log.info('Operation aborted.')

    @QtCore.Slot(bool)
    def on_namespaceAction_triggered(self, checked=False):
        """
        Slot method for the changeNamespaceAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.__class__.__namespace__ = self.sender().whatsThis()

    @QtCore.Slot(bool)
    def on_changeRigConfigurationAction_triggered(self, checked=False):
        """
        Slot method for the changeRigConfigurationAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user for patterns
        #
        configurations = [config.name for config in self.configurations]
        currentConfiguration = self.currentConfiguration()
        current = configurations.index(currentConfiguration.name)

        configuration, response = QtWidgets.QInputDialog.getItem(
            self,
            'Select Rig Configuration',
            'Configurations:',
            configurations,
            editable=False,
            current=current
        )

        if response:

            self.setCurrentConfiguration(configuration)

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_usingEzPoserAction_triggered(self, checked=False):
        """
        Slot method for the usingEzPoser's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        webbrowser.open('https://github.com/bhsingleton/ezposer')
    # endregion
