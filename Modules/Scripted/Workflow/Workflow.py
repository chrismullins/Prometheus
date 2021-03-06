#============================================================================
#
# Copyright (c) Kitware Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#============================================================================

import imp, sys, os, unittest

from __main__ import vtk, qt, ctk, slicer

import Widgets
import json

class Workflow:
  def __init__(self, parent):
    parent.title = "Prometheus"
    parent.categories = ["", "TubeTK"]
    parent.dependencies = []
    parent.contributors = ["Julien Finet (Kitware), Johan Andruejol (Kitware)"]
    parent.helpText = """
    Step by step workflow to monitor RFA of lesions. See <a href=\"http://public.kitware.com/Wiki/TubeTK\"</a> for more information.
    """
    parent.acknowledgementText = """
    This work is supported by the National Institute of Health
    """
    self.parent = parent

#
# Workflow widget
class WorkflowWidget:
  def __init__(self, parent = None):
    self.moduleName = 'Workflow'
    self._ViewNodeIDs = { 'Active' : None, 'Secondary' : None, 'Label' : None}
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

  def setup(self):

    self.level = 0
    self.workflow = ctk.ctkWorkflow(self.parent)

    #workflowWidget = ctk.ctkWorkflowStackedWidget()
    workflowWidget = ctk.ctkWorkflowWidget()

    workflowWidget.setWorkflow( self.workflow )
    self.workflowWidget = workflowWidget
    self.Settings = None

    workflowWidget.buttonBoxWidget().hideInvalidButtons = True
    workflowWidget.buttonBoxWidget().hideGoToButtons = True
    workflowWidget.buttonBoxWidget().backButtonFormat = '[<-]{back:#}"/"{!#}") "{back:name}(back:description)'
    workflowWidget.buttonBoxWidget().nextButtonFormat = '{next:#}"/"{!#}") "{next:name}(next:description)[->]'
    workflowWidget.workflowGroupBox().titleFormat = '[current:icon]{#}"/"{!#}") "{current:name}'
    workflowWidget.workflowGroupBox().hideWidgetsOfNonCurrentSteps = True

    #Creating each step of the workflow
    self.steps = [Widgets.InitialStep(),
                  Widgets.LoadDataStep(),
                  Widgets.RegisterStep(),
                  Widgets.ResampleStep(),
                  Widgets.SegmentationStep(),
                  Widgets.VesselEnhancementStep(),
                  Widgets.ExtractSkeletonStep(),
                  Widgets.VesselExtractionStep(),
                 ]
    i = 0
    for step in self.steps:
      # \todo: b) steps should be able to access the workflow widget automatically
      step.Workflow = self
      # \todo: f) have an option to setup all the gui at startup
      step.createUserInterface()

      #Connecting the created steps of the workflow
      if i != 0:
        self.workflow.addTransition(self.steps[i-1], self.steps[i])
      i += 1

    self.layout.addWidget(workflowWidget)

    # Link slices together
    sliceCompositeNodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLSliceCompositeNode")
    sliceCompositeNodes.SetReferenceCount(sliceCompositeNodes.GetReferenceCount()-1)
    for i in range(0, sliceCompositeNodes.GetNumberOfItems()):
      sliceCompositeNode = sliceCompositeNodes.GetItemAsObject(i)
      sliceCompositeNode.SetLinkedControl(True)

    # Settings
    self.Settings = self.loadUi('WorkflowSettingsPanel.ui')

    # Display settings
    opacitySlider = self.findWidget(self.Settings, 'OpacityRatioDoubleSlider')
    opacitySlider.connect('valueChanged(double)', self.setOpacityRatio)
    self.setOpacityRatio(opacitySlider.value)

    # Hide and disable until step 1 is validated
    self.setDisplaySettingsVisible(False)
    self.setDisplaySettingsEnabled(False)

    # Advanced settings
    levelComboBox = self.findWidget(self.Settings, 'WorkflowLevelComboBox')
    levelComboBox.connect('currentIndexChanged(int)', self.setWorkflowLevel)
    self.setWorkflowLevel(levelComboBox.currentIndex)

    self.reloadButton = self.findWidget(self.Settings, 'ReloadPushButton')
    self.reloadButton.connect('clicked()', self.reloadModule)

    # Add CLI progress bar
    self.CLIProgressBar = slicer.qSlicerCLIProgressBar()
    self.CLIProgressBar.setStatusVisibility(self.CLIProgressBar.VisibleAfterCompletion)
    self.CLIProgressBar.setProgressVisibility(self.CLIProgressBar.HiddenWhenIdle)
    self.Settings.layout().insertWidget(1, self.CLIProgressBar) # insert after spacer

    # Insert settings before workflow's buttons
    collapsibleGroupBox = self.findWidget(self.workflowWidget.workflowGroupBox(), 'CollapsibleButton')
    collapsibleGroupBox.layout().addWidget(self.Settings)

    # Init naming and jsons.
    self.step('Initial').onPresetSelected()

    # Starting and showing the module in layout
    self.workflow.start()

  def step(self, stepid):
    for s in self.steps:
      if s.stepid == stepid:
        return s

  def reloadModule(self,moduleName=None):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    import imp, sys, os, slicer, qt

    if moduleName == None:
      moduleName = self.moduleName
    widgetName = moduleName + "Widget"

    # reload the source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    globals()[moduleName] = imp.load_module(
        moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
    fp.close()

    # rebuild the widget
    # - find and hide the existing widget
    # - create a new widget in the existing parent
    parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent()
    for child in parent.children():
      try:
        child.hide()
      except AttributeError:
        pass

    self.layout.removeWidget(self.workflowWidget)
    self.workflowWidget.deleteLater()
    self.workflowWidget = None

    # Remove spacer items
    item = parent.layout().itemAt(0)
    while item:
      parent.layout().removeItem(item)
      item = parent.layout().itemAt(0)
    # create new widget inside existing parent
    globals()[widgetName.lower()] = eval(
        'globals()["%s"].%s(parent)' % (moduleName, widgetName))
    globals()[widgetName.lower()].setup()

  def loadUi(self, uiFileName):
    loader = qt.QUiLoader()
    moduleName = 'Workflow'
    scriptedModulesPath = eval('slicer.modules.%s.path' % moduleName.lower())
    scriptedModulesPath = os.path.dirname(scriptedModulesPath)
    path = os.path.join(scriptedModulesPath, 'Widgets', 'Resources', 'UI', uiFileName)

    qfile = qt.QFile(path)
    qfile.open(qt.QFile.ReadOnly)
    widget = loader.load(qfile)
    widget.setAutoFillBackground(False)

    return widget

  def findWidget(self, widget, objectName):
    if widget.objectName == objectName:
        return widget
    else:
        children = []
        for w in widget.children():
            resulting_widget = self.findWidget(w, objectName)
            if resulting_widget:
                return resulting_widget
        return None

  def setWorkflowLevel(self, level):
    self.level = level
    for step in self.steps:
      step.setWorkflowLevel(level)

  def setOpacityRatio(self, ratio):
    # 0 == all background <-> 1 == all foreground
    sliceCompositeNodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLSliceCompositeNode")
    sliceCompositeNodes.SetReferenceCount(sliceCompositeNodes.GetReferenceCount()-1)
    for i in range(0, sliceCompositeNodes.GetNumberOfItems()):
      sliceCompositeNode = sliceCompositeNodes.GetItemAsObject(i)
      sliceCompositeNode.SetForegroundOpacity(ratio)

  def getProgressBar( self ):
    return self.CLIProgressBar

  def enter(self):
    self.updateViews()
    for s in self.steps:
      s.updateFromCLIParameters()

  def getJsonParameters( self, module ):
    presets = self.step('Initial').getPresets()
    parameters = {}
    try:
      jsonFilePath = presets[module.name]
    except KeyError:
      return parameters

    jsonData = open(jsonFilePath)
    try:
      data = json.load(jsonData)
    except ValueError:
      print 'Could not read JSON file %s. Make sure the file is valid' % jsonFilePath
      return parameters

    # For all the parameters not already there, add the json parameters
    # Try to be as robust as possible
    jsonParametersList = data['ParameterGroups'][1]['Parameters']
    for p in jsonParametersList:
      try:
        parameters[p['Name']] = p['Value']
      except KeyError:
        print 'Could not find value for %s. Passing.' % p['Name']
        continue
    return parameters

  def updateConfiguration(self):
    config = self.step('Initial').getConfigurationData()
    if not config:
      return

    for step in self.steps:
      step.updateConfiguration(config)

  def setDisplaySettingsVisible( self, visible ):
    if not self.Settings:
      return
    displayGroupbox = self.findWidget(self.Settings, 'DisplaySettingsCollapsibleGroupBox')
    displayGroupbox.setVisible(visible)

  def setDisplaySettingsEnabled( self, enabled ):
    if not self.Settings:
      return

    opacitySlider = self.findWidget(self.Settings, 'OpacityRatioDoubleSlider')
    opacitySlider.setEnabled(enabled)

  def setViews( self, activeNode, secondaryNode = None, labelNode = None ):
    '''Set the node used to update the slice views with the given volume nodes'''
    updateNodes = self._setViewNodeID('Active', activeNode)
    updateNodes = self._setViewNodeID('Secondary', secondaryNode) or updateNodes
    updateNodes = self._setViewNodeID('Label', labelNode) or updateNodes

    if updateNodes:
      self.updateViews()

  def _setViewNodeID( self, type, node ):
    oldID = self._ViewNodeIDs[type]
    if node and self._ViewNodeIDs[type] != node.GetID():
      self._ViewNodeIDs[type] = node.GetID()
    elif not node:
      self._ViewNodeIDs[type] = None

    return oldID != self._ViewNodeIDs[type]

  def _getViewNode( self, type ):
    id = self._ViewNodeIDs[type]
    if id:
      return slicer.mrmlScene.GetNodeByID(id)
    return None

  def updateViews( self ):
    '''Update the slice views with the cached volume nodes'''
    backgroundLabel = self.findWidget(self.Settings, 'BackgroundLabel')
    foregroundLabel = self.findWidget(self.Settings, 'ForegroundLabel')
    backgroundText = 'Background volume'
    forergoundText = 'Foreground volume'

    appLogic = slicer.app.applicationLogic()
    selectionNode = appLogic.GetSelectionNode()
    selectionNode.SetActiveVolumeID(self._ViewNodeIDs['Active'])
    selectionNode.SetSecondaryVolumeID(self._ViewNodeIDs['Secondary'])
    selectionNode.SetActiveLabelVolumeID(self._ViewNodeIDs['Label'])
    appLogic.PropagateVolumeSelection(1)

    backgroundNode = self._getViewNode('Active')
    foregroundNode = self._getViewNode('Secondary')
    if backgroundNode:
      backgroundText = backgroundNode.GetName()
    if foregroundNode:
      forergoundText = foregroundNode.GetName()

    backgroundLabel.setText(backgroundText)
    foregroundLabel.setText(forergoundText)
