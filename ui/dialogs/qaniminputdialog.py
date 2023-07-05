from maya import cmds as mc
from Qt import QtCore, QtWidgets, QtGui
from itertools import chain
from dcc.ui.dialogs import quicdialog

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QAnimInputDialog(quicdialog.QUicDialog):
    """
    Overload of `QUicDialog` that prompts users for animation related inputs.
    """

    # region Dunderscores
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :key parent: QtWidgets.QWidget
        :key f: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        super(QAnimInputDialog, self).__init__(*args, **kwargs)

        # Declare public variables
        #
        self.label = None
        self.lineEdit = None
        self.segmentWidget = None
        self.segmentCheckBox = None
        self.animationRangePushButton = None
        self.objectRangePushButton = None
        self.startTimeWidget = None
        self.startTimeLabel = None
        self.startTimeSpinBox = None
        self.endTimeWidget = None
        self.endTimeLabel = None
        self.endTimeSpinBox = None
        self.buttonBox = None
    # endregion

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QAnimInputDialog, self).postLoad(*args, **kwargs)

        # Modify dialog title
        #
        title = kwargs.get('title', 'Create Animation:')
        self.setWindowTitle(title)

        # Modify label
        #
        label = kwargs.get('label', 'Enter Name:')
        self.label.setText(label)

        # Modify line-edit text
        #
        text = kwargs.get('text', '')
        mode = kwargs.get('mode', QtWidgets.QLineEdit.Normal)

        self.lineEdit.setText(text)
        self.lineEdit.setEchoMode(mode)

        # Modify animation-range values
        #
        startTime, endTime = kwargs.get('animationRange', self.defaultRangeValue())
        self.startTimeSpinBox.setValue(startTime)
        self.endTimeSpinBox.setValue(endTime)

    def textValue(self):
        """
        Returns the text value.

        :rtype: str
        """

        return self.lineEdit.text()

    def rangeValue(self):
        """
        Returns the range value.

        :rtype: Tuple[int, int]
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
