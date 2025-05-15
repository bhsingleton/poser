import os
import webbrowser

from maya.api import OpenMaya as om
from mpy import mpyscene, mpynode
from fnmatch import fnmatchcase
from itertools import chain
from dcc.python import stringutils
from dcc.ui import qsingletonwindow
from dcc.maya.libs import hotkeyutils
from dcc.vendor.six import string_types, integer_types
from dcc.vendor.Qt import QtCore, QtWidgets, QtGui, QtCompat
from dcc.decorators.staticinitializer import staticInitializer
from dcc.decorators.classproperty import classproperty
from dcc.maya.decorators import undo
from . import resources
from .tabs import qlibrarytab, qplottertab, qaligntab, qlooptab
from ..libs import rigutils, rigconfiguration

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


@staticInitializer
class QEzPoser(qsingletonwindow.QSingletonWindow):
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
    __axis_vectors__ = (om.MVector.kXaxisVector, om.MVector.kYaxisVector, om.MVector.kZaxisVector)
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
        cls.__configurations__ = rigutils.loadConfigurations()

        settings = cls.getSettings()
        configIndex = settings.value('editor/currentConfiguration', defaultValue=-1, type=int)
        cls.setCurrentConfiguration(configIndex)

        # Load user namespaces
        #
        cls.__namespace__ = settings.value('editor/customNamespace', defaultValue='', type=str)

        # Install runtime commands
        #
        cls.installRuntimeCommands()

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
        self._callbackIds = om.MCallbackIdArray()

    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that initializes the user interface.

        :rtype: None
        """

        # Call parent method
        #
        super(QEzPoser, self).__setup_ui__(self, *args, **kwargs)

        # Initialize main window
        #
        self.setWindowTitle("|| Ez'Poser")
        self.setMinimumSize(QtCore.QSize(300, 500))

        # Initialize main menu-bar
        #
        mainMenuBar = QtWidgets.QMenuBar()
        mainMenuBar.setObjectName('mainMenuBar')

        self.setMenuBar(mainMenuBar)

        # Initialize file menu
        #
        self.fileMenu = mainMenuBar.addMenu('&File')
        self.fileMenu.setObjectName('fileMenu')

        self.setProjectFolderAction = QtWidgets.QAction('Set Project Folder', parent=self.fileMenu)
        self.setProjectFolderAction.setObjectName('setProjectFolderAction')
        self.setProjectFolderAction.triggered.connect(self.on_setProjectFolderAction_triggered)

        self.fileMenu.addAction(self.setProjectFolderAction)

        # Initialize settings menu
        #
        self.settingsMenu = mainMenuBar.addMenu('&Settings')
        self.settingsMenu.setObjectName('settingsMenu')

        currentConfig = self.currentConfiguration()
        configName = currentConfig.name if (currentConfig is not None) else ''

        self.rigConfigurationAction = QtWidgets.QAction(f'Rig: {configName}', parent=self.settingsMenu)
        self.rigConfigurationAction.setObjectName('rigConfigurationAction')
        self.rigConfigurationAction.setEnabled(False)

        self.changeRigConfigurationAction = QtWidgets.QAction('Change Rig Configuration', parent=self.settingsMenu)
        self.changeRigConfigurationAction.setObjectName('changeRigConfigurationAction')
        self.changeRigConfigurationAction.triggered.connect(self.on_changeRigConfigurationAction_triggered)

        self.mirrorAxisSection = QtWidgets.QAction('Mirroring:', parent=self.settingsMenu)
        self.mirrorAxisSection.setObjectName('axisSection')
        self.mirrorAxisSection.setSeparator(True)

        self.xAxisAction = QtWidgets.QAction('X', parent=self.settingsMenu)
        self.xAxisAction.setObjectName('xAxisAction')
        self.xAxisAction.setCheckable(True)
        self.xAxisAction.setChecked(True)

        self.yAxisAction = QtWidgets.QAction('Y', parent=self.settingsMenu)
        self.yAxisAction.setObjectName('yAxisAction')
        self.yAxisAction.setCheckable(True)

        self.zAxisAction = QtWidgets.QAction('Z', parent=self.settingsMenu)
        self.zAxisAction.setObjectName('zAxisAction')
        self.zAxisAction.setCheckable(True)

        self.mirrorAxisActionGroup = QtWidgets.QActionGroup(self.settingsMenu)
        self.mirrorAxisActionGroup.setObjectName('mirrorAxisActionGroup')
        self.mirrorAxisActionGroup.setExclusive(True)
        self.mirrorAxisActionGroup.addAction(self.xAxisAction)
        self.mirrorAxisActionGroup.addAction(self.yAxisAction)
        self.mirrorAxisActionGroup.addAction(self.zAxisAction)

        self.detectMirroringAction = QtWidgets.QAction('Detect Mirroring', parent=self.settingsMenu)
        self.detectMirroringAction.setObjectName('zAxisAction')
        self.detectMirroringAction.triggered.connect(self.on_detectMirroringAction_triggered)

        self.namespaceSection = QtWidgets.QAction('Namespaces:', parent=self.settingsMenu)
        self.namespaceSection.setObjectName('namespaceSection')
        self.namespaceSection.setSeparator(True)

        self.namespaceActionGroup = QtWidgets.QActionGroup(self.settingsMenu)
        self.namespaceActionGroup.setObjectName('namespaceActionGroup')
        self.namespaceActionGroup.setExclusive(True)

        self.namespaceSeparator = QtWidgets.QAction('', parent=self.settingsMenu)
        self.namespaceSeparator.setObjectName('namespaceSeparator')
        self.namespaceSeparator.setSeparator(True)

        self.settingsMenu.addActions(
            [
                self.rigConfigurationAction,
                self.changeRigConfigurationAction,
                self.mirrorAxisSection,
                self.xAxisAction,
                self.yAxisAction,
                self.zAxisAction,
                self.detectMirroringAction,
                self.namespaceSection,
                self.namespaceSeparator
            ]
        )

        self.settingsMenu.aboutToShow.connect(self.on_settingsMenu_aboutToShow)

        # Initialize help menu
        #
        self.helpMenu = mainMenuBar.addMenu('&Help')
        self.helpMenu.setObjectName('helpMenu')

        self.usingEzPoserAction = QtWidgets.QAction("Using Ez'Poser", parent=self.helpMenu)
        self.usingEzPoserAction.setObjectName('usingEzPoserAction')
        self.usingEzPoserAction.triggered.connect(self.on_usingEzPoserAction_triggered)

        self.helpMenu.addAction(self.usingEzPoserAction)

        # Initialize central widget
        #
        centralLayout = QtWidgets.QVBoxLayout()
        centralLayout.setObjectName('centralLayout')
        centralLayout.setContentsMargins(1, 1, 1, 1)

        centralWidget = QtWidgets.QWidget(parent=self)
        centralWidget.setObjectName('centralWidget')
        centralWidget.setLayout(centralLayout)

        self.setCentralWidget(centralWidget)

        # Initialize tab-control
        #
        self.tabControl = QtWidgets.QTabWidget(parent=self)
        self.tabControl.setObjectName('tabControl')
        self.tabControl.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))

        self.libraryTab = qlibrarytab.QLibraryTab(parent=self.tabControl)
        self.plotterTab = qplottertab.QPlotterTab(parent=self.tabControl)
        self.alignTab = qaligntab.QAlignTab(parent=self.tabControl)
        self.loopTab = qlooptab.QLoopTab(parent=self.tabControl)

        self.tabControl.addTab(self.libraryTab, 'Library')
        self.tabControl.addTab(self.plotterTab, 'Plotter')
        self.tabControl.addTab(self.alignTab, 'Align')
        self.tabControl.addTab(self.loopTab, 'Loop')

        self.cwdChanged.connect(self.libraryTab.fileItemModel.setCwd)

        centralLayout.addWidget(self.tabControl)
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

        for tab in self.iterTabs():

            tab.sceneChanged()
    # endregion

    # region Methods
    def addCallbacks(self):
        """
        Adds any callbacks required by this window.

        :rtype: None
        """

        # Add callbacks
        #
        hasCallbacks = len(self._callbackIds) > 0

        if not hasCallbacks:

            callbackId = om.MSceneMessage.addCallback(om.MSceneMessage.kAfterOpen, onSceneChanged)
            self._callbackIds.append(callbackId)

        # Force scene update
        #
        self.sceneChanged()

    def removeCallbacks(self):
        """
        Removes any callbacks created by this window.

        :rtype: None
        """

        # Remove callbacks
        #
        hasCallbacks = len(self._callbackIds) > 0

        if hasCallbacks:

            om.MMessage.removeCallbacks(self._callbackIds)
            self._callbackIds.clear()

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
        self.tabControl.setCurrentIndex(settings.value('editor/currentTabIndex', defaultValue=0, type=int))
        self.setCwd(settings.value('editor/cwd', defaultValue=self.scene.projectPath, type=str))
        self.setCurrentConfiguration(settings.value('editor/currentConfiguration', defaultValue=-1, type=int))
        self.setCurrentAxis(settings.value('editor/currentAxis', defaultValue=0, type=int))

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
        settings.setValue('editor/currentAxis', self.currentAxis())
        settings.setValue('editor/customNamespace', self.currentNamespace())

        # Save tab settings
        #
        for tab in self.iterTabs():

            tab.saveSettings(settings)

    @classmethod
    def installRuntimeCommands(cls):
        """
        Installs the runtime-commands for Ez'Poser.

        :rtype: None
        """

        directory = os.path.abspath(os.path.dirname(__file__))
        filePath = os.path.abspath(os.path.join(directory, '..', 'hotkeys', 'ezposer.json'))

        hotkeyutils.installRuntimeCommandsFromFile(filePath)

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

    def currentAxis(self):
        """
        Returns the current mirror axis.

        :rtype: int
        """

        actions = self.mirrorAxisActionGroup.actions()
        checkedAction = self.mirrorAxisActionGroup.checkedAction()
        index = actions.index(checkedAction)

        return index

    def setCurrentAxis(self, axis):
        """
        Updates the current mirror axis.

        :type axis: int
        :rtype: None
        """

        actions = self.mirrorAxisActionGroup.actions()
        action = actions[axis]

        action.setChecked(True)

    @classmethod
    def currentNamespace(cls):
        """
        Returns the current namespace.

        :rtype: str
        """

        return cls.__namespace__

    @classmethod
    def setCurrentNamespace(cls, namespace):
        """
        Updates the current namespace.

        :type namespace: str
        :rtype: None
        """

        cls.__namespace__ = namespace

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

            # Check if index is valid
            #
            try:

                cls.setCurrentConfiguration(cls.__configurations__[configuration])

            except IndexError as exception:

                log.debug(exception)

        elif isinstance(configuration, string_types):

            # Check if named configuration exists
            #
            try:

                configurations = [config.name for config in cls.__configurations__]
                index = configurations.index(configuration)
                configuration = cls.__configurations__[index]

                cls.setCurrentConfiguration(configuration)

            except ValueError as exception:

                log.debug(exception)

        elif isinstance(configuration, rigconfiguration.RigConfiguration):

            # Update internal dunderscore
            #
            cls.__configuration__ = configuration

            # Check if a window instance exists
            # If so, update the rig configuration action text
            #
            instance = cls.getInstance()

            if instance is not None:

                instance.rigConfigurationAction.setText(f'Rig: {cls.__configuration__.name}')

        else:

            raise TypeError(f'setCurrentConfiguration() expects a valid configuration ({type(configuration).__name__} given)!')

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

    @classmethod
    def getSelection(cls, sort=False):
        """
        Returns the active selection.
        If no nodes are selected then the controller patterns are queried instead!

        :type sort: bool
        :rtype: List[mpynode.MPyNode]
        """

        # Evaluate active selection
        #
        selection = cls.scene.selection(apiType=om.MFn.kTransform)
        selectionCount = len(selection)

        if selectionCount == 0:

            selection = cls.getControls()

        # Check if selection requires sorting
        #
        if sort:

            return sorted(selection, key=cls.getSortPriority)

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
        namespaces.extend(om.MNamespace.getNamespaces(parentNamespace=':', recurse=True))

        if cls.__namespace__ not in namespaces:

            namespaces.append(cls.__namespace__)

        return namespaces

    @classmethod
    def iterControls(cls, visible=False):
        """
        Returns a generator that yields controls from the scene.

        :type visible: bool
        :rtype: Iterator[mpynode.MPyNode]
        """

        # Iterate through nodes
        #
        namespace = cls.currentNamespace()
        patterns = [f'{namespace}:{pattern}' for pattern in cls.controllerPatterns()]

        for node in cls.scene.iterNodesByPattern(*patterns, apiType=om.MFn.kTransform):

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

    @classmethod
    def getControls(cls, visible=False):
        """
        Returns a list of controls from the scene.

        :type visible: bool
        :rtype: Iterator[mpynode.MPyNode]
        """

        return list(cls.iterControls(visible=visible))

    @classmethod
    @undo.Undo(state=False)
    def selectControls(cls, visible=False):
        """
        Selects any controls that match the active controller patterns.

        :type visible: bool
        :rtype: None
        """

        nodes = [node.object() for node in cls.iterControls(visible=visible)]
        cls.scene.setSelection(nodes)

    @classmethod
    @undo.Undo(state=False)
    def selectAssociatedControls(self):
        """
        Selects any controls that are in the same display layer.

        :rtype: None
        """

        selection = self.getSelection()
        layers = set(filter(None, [node.getAssociatedDisplayLayer() for node in selection]))
        nodes = set(chain(*[layer.nodes() for layer in layers]))

        self.scene.setSelection(nodes)

    @classmethod
    @undo.Undo(state=False)
    def selectOppositeControls(self, replace=True):
        """
        Selects the opposite nodes from the active selection.

        :type replace: bool
        :rtype: None
        """

        selection = self.getSelection()
        oppositeNodes = set(filter(None, [node.getOppositeNode() for node in selection]))

        self.scene.setSelection(oppositeNodes, replace=replace)
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

    @QtCore.Slot()
    def on_detectMirroringAction_triggered(self):
        """
        Slot method for the `detectMirroringAction` widget's `triggered` signal.

        :rtype: None
        """

        axis = self.currentAxis()
        normal = self.__axis_vectors__[axis]

        for control in self.iterControls():

            control.detectMirroring(normal=normal)

    @QtCore.Slot()
    def on_settingsMenu_aboutToShow(self):
        """
        Slot method for the `settingsMenu` widget's `aboutToShow` signal.

        :rtype: None
        """

        self.invalidateNamespaces()

    @QtCore.Slot(bool)
    def on_namespaceAction_triggered(self, checked=False):
        """
        Slot method for the `namespaceAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        namespace = self.sender().whatsThis()
        self.setCurrentNamespace(namespace)

    @QtCore.Slot(bool)
    def on_changeRigConfigurationAction_triggered(self, checked=False):
        """
        Slot method for the `changeRigConfigurationAction` widget's `triggered` signal.

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
        Slot method for the `usingEzPoserAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        webbrowser.open('https://github.com/bhsingleton/ezposer')
    # endregion
