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

import os
from __main__ import qt, ctk, slicer
from WorkflowStep import *

class LoadDataStep( WorkflowStep ) :

  def __init__( self ):
    super(LoadDataStep, self).__init__()

    self.initialize( 'LoadData' )
    self.setName( 'Load input scans' )
    self.setDescription('Load CT or MR images')

  def setupUi( self ):
    self.loadUi('LoadDataStep.ui')
    loadIcon = self.style().standardIcon(qt.QStyle.SP_DialogOpenButton)
    # Volume 1
    self.get('Volume1NodeComboBox').connect('currentNodeChanged(vtkMRMLNode*)', self.validate)
    self.get('Volume1NodeComboBox').connect('currentNodeChanged(vtkMRMLNode*)', self.onVolumeChanged)
    self.get('Volume1NodeToolButton').icon = loadIcon
    self.get('Volume1NodeToolButton').connect('clicked()', self.loadVolume1Node)
    # Volume 2
    self.get('Volume2NodeComboBox').connect('currentNodeChanged(vtkMRMLNode*)', self.validate)
    self.get('Volume2NodeComboBox').connect('currentNodeChanged(vtkMRMLNode*)', self.onVolumeChanged)
    self.get('Volume2NodeToolButton').icon = loadIcon
    self.get('Volume2NodeToolButton').connect('clicked()', self.loadVolume2Node)
    # Go to Volumes
    self.get('GoToVolumesModulePushButton').connect('clicked()', self.goToVolumesModule)

  def validate( self, desiredBranchId = None ):
    validVolumes = (self.get('Volume1NodeComboBox').currentNode() != None and
                    self.get('Volume2NodeComboBox').currentNode() != None)
    self.Workflow.setDisplaySettingsEnabled(validVolumes)

    self.validateStep(validVolumes, desiredBranchId)

  def onVolumeChanged( self ):
    self.setViews(self.get('Volume1NodeComboBox').currentNode(),
                     self.get('Volume2NodeComboBox').currentNode())

  def loadVolume1Node(self):
    self.loadFile('First Volume', 'VolumeFile', self.get('Volume1NodeComboBox'))

  def loadVolume2Node(self):
    self.loadFile('Second Volume', 'VolumeFile', self.get('Volume2NodeComboBox'))

  def goToVolumesModule(self):
    self.openModule('Volumes')

  def updateConfiguration( self, config ):
    self.get('Volume1Label').setText(config['Volume1Name'])
    self.get('Volume2Label').setText(config['Volume2Name'])

  def onEntry(self, comingFrom, transitionType):
    super(LoadDataStep, self).onEntry(comingFrom, transitionType)

    self.Workflow.setDisplaySettingsVisible(True)
