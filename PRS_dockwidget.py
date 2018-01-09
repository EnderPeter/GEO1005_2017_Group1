# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PRS_PoliceResponseSystemDockWidget
                                 A QGIS plugin
 Support decisions of police officers in catching terrorist attackers at the least possible cost.
                             -------------------
        begin                : 2018-01-04
        git sha              : $Format:%H$
        copyright            : (C) 2018 by TUDelft
        email                : meylinh52@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
from PyQt4 import QtGui, QtCore, uic
from PyQt4.QtCore import pyqtSignal, Qt, QVariant
from Qt import QtCore
from qgis._core import QgsRectangle
from qgis.utils import iface
from qgis._core import QgsMapLayerRegistry, QgsDataSourceURI, QgsRectangle, QgsVectorLayer
from . import utility_functions as uf

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'PRS_dockwidget_base.ui'))


class PRS_PoliceResponseSystemDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    layer_dic=dict()


    def __init__(self, parent=None):
        """Constructor."""
        super(PRS_PoliceResponseSystemDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # define globals
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        # Init OpenStreet Map Layer
        self.canvas.useImageToRender(False)
        self.canvas.setCanvasColor(Qt.white)
        self.canvas.show()

        # set up GUI operation signals
        # data
        #zoom_area
        self.openScenario.clicked.connect(self.zoom)
        self.incident_a.clicked.connect(self.removeMapLayersB)
        self.incident_b.clicked.connect(self.removeMapLayersA)
        self.bufferButton.clicked.connect(self.calculateBuffer)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()


    def zoom(self):
        self.iface.mapCanvas().setExtent(QgsRectangle(491948.924266, 6779060, 504837, 6787990))
        self.iface.mapCanvas().refresh()

        self.load_layer_from_db("Study_area", "study_area.qml")
        self.load_layer_from_db("RoadNetwork", "road_network.qml")
        self.load_layer_from_db("Police_stations_area", "police_station.qml")
        self.load_layer_from_db("Buffer_A", "buffer_a.qml")
        self.load_layer_from_db("Incident_A", "incident_a.qml")
        self.load_layer_from_db("Buffer_B", "buffer_b.qml")
        self.load_layer_from_db("Incident_B", "incident_b.qml")
        self.load_layer_from_db("info_A", "info_A.qml")


    def load_layer_from_db(self, layer_name,style_name):
        uri = QgsDataSourceURI()
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        filename = os.path.join(cur_dir, "data", "db.sqlite")
        filename_styles = os.path.join(cur_dir, "data", "styles",style_name)
        uri.setDatabase(filename)
        uri.setDataSource('', layer_name, 'GEOMETRY', )
        sta = QgsVectorLayer(uri.uri(), layer_name, "spatialite")
        sta.loadNamedStyle(filename_styles)
        # set the transparency of a layer
        # sta.setLayerTransparency(89)
        self.layer_dic[layer_name]=sta
        QgsMapLayerRegistry.instance().addMapLayers([sta])

    def removeMapLayersA(self):  # real signature unknown; restored from __doc__ with multiple overloadse
            #QgsMapLayerRegistry.instance().removeMapLayer(self.layer_dic.get("Buffer_A").id())
            if self.iface.legendInterface().isLayerVisible(self.layer_dic.get("Buffer_A")):
                self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_A"), False)
            else:
                self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_A"), True)
    def removeMapLayersB(self):  # real signature unknown; restored from __doc__ with multiple overloadse
        #QgsMapLayerRegistry.instance().removeMapLayer(self.layer_dic.get("Buffer_B").id())
        if  self.iface.legendInterface().isLayerVisible(self.layer_dic.get("Buffer_B")):
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_B"), False)
        else:
            self.iface.legendInterface().setLayerVisible(self.layer_dic.get("Buffer_B"), True)

        # Incident_Blocked_Area



    # after adding features to layers needs a refresh (sometimes)
    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()


    def getSelectedLayer(self):
        layer_name = "Incident_A"
        layer = uf.getLegendLayerByName(self.iface, layer_name)
        print "layer",layer
        return layer


    # buffer functions
    def getBufferCutoff(self):
        cutoff = self.bufferCutoffEdit.text()
        if uf.isNumeric(cutoff):
            return uf.convertNumeric(cutoff)
        else:
            return 0


    def calculateBuffer(self):
        origins = self.getSelectedLayer().selectedFeatures()
        layer = self.getSelectedLayer()
        if origins > 0:
            cutoff_distance = self.getBufferCutoff()
            buffers = {}
            #print "cutt_off ",cutoff_distance
            print "origins ", origins
            for point in origins:
                geom = point.geometry()
                buffers[point.id()] = geom.buffer(cutoff_distance,12).asPolygon()

            # store the buffer results in temporary layer called "Buffers"
            buffer_layer = uf.getLegendLayerByName(self.iface, "Buffers")
            # create one if it doesn't exist
            if not buffer_layer:
                attribs = ['id', 'distance']
                types = [QVariant.String, QVariant.Double]
                buffer_layer = uf.createTempLayer('Buffers','POLYGON',layer.crs().postgisSrid(), attribs, types)
                uf.loadTempLayer(buffer_layer)
                buffer_layer.setLayerName('Buffers')
            # insert buffer polygons
            geoms = []
            values = []
            for buffer in buffers.iteritems():
                # each buffer has an id and a geometry
                geoms.append(buffer[1])
                # in the case of values, it expects a list of multiple values in each item - list of lists
                values.append([buffer[0],cutoff_distance])
            uf.insertTempFeatures(buffer_layer, geoms, values)
            self.refreshCanvas(buffer_layer)
