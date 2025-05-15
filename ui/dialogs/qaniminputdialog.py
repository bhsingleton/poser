from maya import cmds as mc
from itertools import chain
from dcc.vendor.Qt import QtCore, QtWidgets, QtGui
from dcc.ui import qtimespinbox
from dcc.ui.dialogs import qmaindialog

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QAnimInputDialog(qmaindialog.QMainDialog):
    """
    Overload of `QMainDialog` that prompts users for animation related inputs.
    """

    # region Dunderscores
    def __post_init__(self, *args, **kwargs):
        """
        Private method called after an instance has initialized.

        :rtype: None
        """

        # Call parent method
        #
        super(QAnimInputDialog, self).__post_init__(*args, **kwargs)

        # Modify dialog title
        #
        title = kwargs.get('title', 'Create Animation:')
        self.setWindowTitle(title)

        # Update label
        #
        label = kwargs.get('label', 'Enter Name:')
        self.label.setText(label)

        # Update line-edit
        #
        text = kwargs.get('text', '')
        mode = kwargs.get('mode', QtWidgets.QLineEdit.Normal)

        self.lineEdit.setText(text)
        self.lineEdit.setEchoMode(mode)

        # Update animation-range
        #
        startTime, endTime = kwargs.get('animationRange', self.defaultRangeValue())
        self.startTimeSpinBox.setValue(startTime)
        self.endTimeSpinBox.setValue(endTime)

    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that initializes the user interface.

        :rtype: None
        """

        # Initialize dialog
        #
        self.setWindowTitle("Create Animation:")
        self.setMinimumSize(QtCore.QSize(300, 170))

        # Initialize central layout
        #
        centralLayout = QtWidgets.QVBoxLayout()
        centralLayout.setObjectName('centralLayout')

        self.setLayout(centralLayout)

        # Initialize line-edit
        #
        self.label = QtWidgets.QLabel('Enter Name:')
        self.label.setObjectName('label')
        self.label.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.label.setFixedHeight(24)
        self.label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.lineEdit = QtWidgets.QLineEdit()
        self.lineEdit.setObjectName('lineEdit')
        self.lineEdit.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.lineEdit.setFixedHeight(24)

        centralLayout.addWidget(self.label)
        centralLayout.addWidget(self.lineEdit)

        # Initialize segment widget
        #
        self.segmentLayout = QtWidgets.QHBoxLayout()
        self.segmentLayout.setObjectName('segmentLayout')
        self.segmentLayout.setContentsMargins(0, 0, 0, 0)

        self.segmentWidget = QtWidgets.QWidget()
        self.segmentWidget.setObjectName('segmentWidget')
        self.segmentWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.segmentWidget.setFixedHeight(24)
        self.segmentWidget.setLayout(self.segmentLayout)

        self.segmentCheckBox = QtWidgets.QCheckBox('Segment')
        self.segmentCheckBox.setObjectName('segmentCheckBox')
        self.segmentCheckBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred))
        self.segmentCheckBox.setFocusPolicy(QtCore.Qt.NoFocus)

        self.spacer = QtWidgets.QSpacerItem(50, 24, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.animationRangePushButton = QtWidgets.QPushButton(QtGui.QIcon(':/dcc/icons/timeline.png'), '')
        self.animationRangePushButton.setObjectName('segmentCheckBox')
        self.animationRangePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.animationRangePushButton.setMinimumWidth(24)
        self.animationRangePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.animationRangePushButton.clicked.connect(self.on_animationRangePushButton_clicked)

        self.objectRangePushButton = QtWidgets.QPushButton(QtGui.QIcon(':/dcc/icons/time.png'), '')
        self.objectRangePushButton.setObjectName('objectRangePushButton')
        self.objectRangePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.objectRangePushButton.setMinimumWidth(24)
        self.objectRangePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.objectRangePushButton.clicked.connect(self.on_objectRangePushButton_clicked)

        self.segmentLayout.addWidget(self.segmentCheckBox)
        self.segmentLayout.addItem(self.spacer)
        self.segmentLayout.addWidget(self.animationRangePushButton)
        self.segmentLayout.addWidget(self.objectRangePushButton)

        centralLayout.addWidget(self.segmentWidget)

        # Initialize animation-range widget
        #
        self.startTimeLayout = QtWidgets.QHBoxLayout()
        self.startTimeLayout.setObjectName('')
        self.startTimeLayout.setContentsMargins(0, 0, 0, 0)

        self.startTimeWidget = QtWidgets.QWidget()
        self.startTimeWidget.setObjectName('startTimeWidget')
        self.startTimeWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.startTimeWidget.setFixedHeight(24)
        self.startTimeWidget.setLayout(self.startTimeLayout)
        self.startTimeWidget.setEnabled(False)

        self.startTimeLabel = QtWidgets.QLabel('From:')
        self.startTimeLabel.setObjectName('startTimeLabel')
        self.startTimeLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.startTimeLabel.setFixedWidth(40)
        self.startTimeLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.startTimeSpinBox = qtimespinbox.QTimeSpinBox()
        self.startTimeSpinBox.setObjectName('')
        self.startTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
        self.startTimeSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.startTimeSpinBox.setDefaultType(qtimespinbox.QTimeSpinBox.DefaultType.START_TIME)
        self.startTimeSpinBox.setMinimum(-9999999)
        self.startTimeSpinBox.setMaximum(9999999)
        self.startTimeSpinBox.setValue(0)

        self.startTimeLayout.addWidget(self.startTimeLabel)
        self.startTimeLayout.addWidget(self.startTimeSpinBox)

        self.segmentCheckBox.toggled.connect(self.startTimeWidget.setEnabled)

        self.endTimeLayout = QtWidgets.QHBoxLayout()
        self.endTimeLayout.setObjectName('')
        self.endTimeLayout.setContentsMargins(0, 0, 0, 0)

        self.endTimeWidget = QtWidgets.QWidget()
        self.endTimeWidget.setObjectName('endTimeWidget')
        self.endTimeWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.endTimeWidget.setFixedHeight(24)
        self.endTimeWidget.setLayout(self.endTimeLayout)
        self.endTimeWidget.setEnabled(False)

        self.endTimeLabel = QtWidgets.QLabel('To:')
        self.endTimeLabel.setObjectName('endTimeLabel')
        self.endTimeLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.endTimeLabel.setFixedWidth(40)
        self.endTimeLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.endTimeSpinBox = qtimespinbox.QTimeSpinBox()
        self.endTimeSpinBox.setObjectName('')
        self.endTimeSpinBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
        self.endTimeSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.endTimeSpinBox.setDefaultType(qtimespinbox.QTimeSpinBox.DefaultType.END_TIME)
        self.endTimeSpinBox.setMinimum(-9999999)
        self.endTimeSpinBox.setMaximum(9999999)
        self.endTimeSpinBox.setValue(1)

        self.endTimeLayout.addWidget(self.endTimeLabel)
        self.endTimeLayout.addWidget(self.endTimeSpinBox)

        self.segmentCheckBox.toggled.connect(self.endTimeWidget.setEnabled)

        centralLayout.addWidget(self.startTimeWidget)
        centralLayout.addWidget(self.endTimeWidget)

        # Initialize button-box widget
        #
        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.setObjectName('buttonBox')
        self.buttonBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.buttonBox.setFixedHeight(24)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        centralLayout.addWidget(self.buttonBox)
    # endregion

    # region Methods
    def textValue(self):
        """
        Returns the text value.

        :rtype: str
        """

        return self.lineEdit.text()

    def rangeValue(self):
        """
        Returns the range value.

        :rtype: Union[Tuple[int, int], None]
        """

        enabled = self.segmentCheckBox.isChecked()

        if enabled:

            return self.startTimeSpinBox.value(), self.endTimeSpinBox.value()

        else:

            return self.defaultRangeValue()

    def defaultRangeValue(self):
        """
        Returns the default range value.

        :rtype: Tuple[int, int]
        """

        return int(mc.playbackOptions(query=True, min=True)), int(mc.playbackOptions(query=True, max=True))

    @classmethod
    def getText(cls, parent, title, label, mode, **kwargs):
        """
        Prompts the user for a text input.

        :type parent: QtWidgets.QWidget
        :type title: str
        :type label: str
        :type mode: int
        :rtype: Tuple[str, Tuple[int, int]]
        """

        instance = cls(title=title, label=label, mode=mode, parent=parent)
        response = instance.exec_()

        return instance.textValue(), instance.rangeValue(), response
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_animationRangePushButton_clicked(self, checked=False):
        """
        Slot method for the animationRangePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        startTime, endTime = self.defaultRangeValue()
        self.startTimeSpinBox.setValue(startTime)
        self.endTimeSpinBox.setValue(endTime)

    @QtCore.Slot(bool)
    def on_objectRangePushButton_clicked(self, checked=False):
        """
        Slot method for the objectRangePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        selection = mc.ls(sl=True, type='transform')

        keyframes = sorted(set(chain(*[mc.keyframe(node, query=True) for node in selection if mc.keyframe(node, query=True, keyframeCount=True) > 0])))
        numKeyframes = len(keyframes)

        if numKeyframes > 0:

            startTime, endTime = int(keyframes[0]), int(keyframes[-1])
            self.startTimeSpinBox.setValue(startTime)
            self.endTimeSpinBox.setValue(endTime)
    # endregion
