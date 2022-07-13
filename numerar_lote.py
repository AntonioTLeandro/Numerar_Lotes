# -*- coding: utf-8 -*-
"""
/***************************************************************************
 numerar_lote
                                 A QGIS plugin
 Numerar Loteamento
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-07-01
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Gloria Santos/Antonio Teles
        email                : mdgss.gloria@gmail.com/antoniot.leandro@gmail.com
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
from re import T
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qgis.PyQt import QtCore
from qgis.gui import *
from PyQt5 import QtCore, QtGui
import pdb
from qgis.core import *

from qgis.gui import QgsMessageBar, QgsMapCanvas, QgsMapCanvasItem
import qgis.utils
import os
from collections import defaultdict

from shapely.wkb import loads
from osgeo import ogr
import processing

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QDialog

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .numerar_lote_dialog import numerar_loteDialog
import os.path
import numpy as np

#Redefinir Ordem
def redefine_order(coordPoly, vertices, coordPoly_inters, tipo):
    CoordX = 0
    CoordY = 0
    if tipo == 1002 or tipo == 2:
        CoordX = coordPoly_inters.GetX(0)
        CoordY = coordPoly_inters.GetY(0)
    else:
        y = 0
        for coord_itens in coordPoly_inters:
            if y == 0:
                CoordX = coord_itens.GetX(0)
                CoordY = coord_itens.GetY(0)

    x = 0
    k = 0
    x = 0

    temp = []
    ti = 0
    maxY = 0 #coordPoly.GetY(0)
    n_vert = len(vertices)
    copy = np.ones((len(vertices), 2))

    for t in range(n_vert):
        if coordPoly.GetY(t) == CoordY and coordPoly.GetX(t) == CoordX:
            maxY = coordPoly.GetY(t)
            ti = t

    for t in range(ti, n_vert):
        if x == 0:
            temp.append(coordPoly.GetX(t))
            temp.append(coordPoly.GetY(t))
            copy[x][0] = temp[0]
            copy[x][1] = temp[1]
            x += 1
        else:
            if t == n_vert:
                k = 0
            else:
                k = x
            if copy[k][0] != coordPoly.GetX(t) and copy[k][1] != coordPoly.GetY(t):
                temp[0] = coordPoly.GetX(t)
                temp[1] = coordPoly.GetY(t)
                copy[x][0] = temp[0]
                copy[x][1] = temp[1]
                x += 1
        t += 1

    for t in range(ti - 1):
        if t == n_vert:
            k = 0
        else:
            k = x
        if copy[x - 1][0] != coordPoly.GetX(t) and copy[x -1][1] != coordPoly.GetY(t):
            temp[0] = coordPoly.GetX(t)
            temp[1] = coordPoly.GetY(t)
            copy[x][0] = coordPoly.GetX(t)
            copy[x][1] = coordPoly.GetY(t)
            x += 1

    if clockUnclock(coordPoly, vertices) == True:
        #sentido anti-horario
        copyUnClock = np.ones((len(vertices), 2))
        r = 0
        for rT in copy:
            copyUnClock[r][0] = rT[0]
            copyUnClock[r][1] = rT[1]
            r += 1

        for t in range(1, n_vert):
            copy[t][0] = copyUnClock[n_vert - t][0]
            copy[t][1] = copyUnClock[n_vert - t][1]
            t += 1

    return copy

def clockUnclock(coordPoly, vertices):
    maxX = coordPoly.GetX(0)
    minX = coordPoly.GetX(0)
    maxY = coordPoly.GetY(0)
    minY = coordPoly.GetY(0)

    n_vert = len(vertices)
    t = 0
    for t in range(n_vert):
        if coordPoly.GetX(t) > maxX: maxX = coordPoly.GetX(t)
        if coordPoly.GetX(t) < minX: minX = coordPoly.GetX(t)
        if coordPoly.GetY(t) > maxY: maxY = coordPoly.GetY(t)
        if coordPoly.GetY(t) < minY: minY = coordPoly.GetY(t)
        t += 1

    fst = "" 
    sec = ""
    t = 0
    for t in range(n_vert):
        if coordPoly.GetX(t) == maxX:
            if fst == "" :
                fst = 1
            else:
                sec = 1
        elif coordPoly.GetY(t) == maxY:
            if fst == "":
                fst = 0
            else:
                sec = 0
        elif coordPoly.GetX(t) == minX:
            if fst == "":
                fst = 3
            else:
                sec = 3
        elif coordPoly.GetY(t) == maxY:
            if fst == "":
                fst = 2
            else:
                sec = 2
        t += 1
    if (fst == 0 and sec == 1) or (fst == 1 and sec == 2) or (fst == 2 and sec == 3) or (fst == 3 and sec == 0):
        return True
    else:
        return False    

def verificar_intersect(camadaLote, camadaQuadra):
    intersect = camadaQuadra.intersection(camadaLote)
    corrdsList = []
    if intersect:
        wkb = intersect.asWkb() 
        geom_ogr = ogr.CreateGeometryFromWkb(wkb)
        tipo_line = intersect.wkbType()
        d = 0
        coords = []
        coords_i = []
        list_coords_aux = []
        if tipo_line == 1002 or tipo_line == 2:
            coords.append(QgsPointXY(geom_ogr.GetX(0), geom_ogr.GetY(0)))
            coords.append(QgsPointXY(geom_ogr.GetX(1), geom_ogr.GetY(1)))  
            corrdsList.append([coords])
        else:
            for items in geom_ogr:
                if d == 0:
                    if items.GetX(0) != items.GetX(1) and items.GetY(0) != items.GetY(1):
                        coords_i.append(QgsPointXY(items.GetX(0), items.GetY(0)))
                        coords_i.append(QgsPointXY(items.GetX(1), items.GetY(1)))
                        item_anterior = items
                        d += 1
                else:
                    if items.GetX(0) != items.GetX(1) and items.GetY(0) != items.GetY(1):
                        if (item_anterior.GetX(1) != items.GetX(0) and item_anterior.GetY(1) != items.GetY(0)) and (item_anterior.GetX(0) != items.GetX(0) and item_anterior.GetY(0) != items.GetY(0)):
                            list_coords_aux.append(coords_i)
                            coords_i = []
                            coords_i.append(QgsPointXY(items.GetX(0), items.GetY(0)))
                            coords_i.append(QgsPointXY(items.GetX(1), items.GetY(1)))
                            item_anterior = items
                        else:
                            coords_i.append(QgsPointXY(items.GetX(1), items.GetY(1)))
                            item_anterior = items
                    d += 1 
        if coords_i:
            list_coords_aux.append(coords_i)
            j_1 = 0
            v_list = []
            for list_coords_1 in list_coords_aux:
                j_2 = 0
                for list_coords_2 in list_coords_aux:
                    if j_1 != j_2:
                        if list_coords_1[0] == list_coords_2[len(list_coords_2) - 1]:
                            if j_1 not in v_list:
                                coords_ii = list_coords_2
                                for coord in list_coords_aux[j_1]:
                                    coords_ii.append(coord)
                                corrdsList.append([coords_ii])
                                v_list.append(j_1)
                                v_list.append(j_2)
                    j_2 += 1
                j_1 += 1

            j_1 = 0
            for list_coords_1 in list_coords_aux:
                if j_1 not in v_list:
                    corrdsList.append([list_coords_1])
                j_1 += 1

    retorno = 0
    for item in corrdsList:   
        feature_lineg = QgsFeature()
        geom_lineg =  QgsGeometry.fromPolylineXY(item[0])
        tam = geom_lineg.length()
        retorno = int(tam)
    
    return retorno

def dissolver(layer):
    p_dissolver = {'INPUT':layer,'FIELD':'','GEOMETRY':'geometry','EXPLODE_COLLECTIONS':True,'KEEP_ATTRIBUTES':False,'COUNT_FEATURES':False,'COMPUTE_AREA':False,'COMPUTE_STATISTICS':False,'STATISTICS_ATTRIBUTE':'','OPTIONS':'','OUTPUT':'TEMPORARY_OUTPUT'}
    dissolver = processing.run("gdal:dissolve",p_dissolver)
    return dissolver['OUTPUT']

class numerar_lote:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'numerar_lote_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.dlg = numerar_loteDialog()
        self.actions = []
        self.menu = self.tr(u'&Numerar Lote')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('numerar_lote', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/numerar_lote/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Numerar Lote'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

        self.dlg.caminho.clear()
        self.dlg.select_caminho.clicked.connect(self.selecione_caminho)
        self.dlg.salvememoria.clicked.connect(self.verificar_salvememeoria)
        self.dlg.pushButton.clicked.connect(self.definir_inicial)
        self.dlg.numeracaoS.setEnabled(True)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Numerar Lote'),
                action)
            self.iface.removeToolBarIcon(action)

    def definir_inicial(self):
        for select in QgsProject.instance().mapLayers().values():
            if select.name() == self.dlg.select_layer.currentText():
                layerselect = select
                field_names = layerselect.fields()
                ver_table = True
                for field_attr in field_names:
                    if field_attr.name() == "DEF_LOTE":
                        ver_table = False
                if ver_table:
                    layerselect.dataProvider().addAttributes([QgsField("DEF_LOTE",QVariant.String)])
                    layerselect.updateFields()
                
                idcoluna = layerselect.fields().indexFromName("DEF_LOTE")

                #layer_line = QgsVectorLayer("LineString?", "layer_line", "memory" )

                rr_dissolver = dissolver(select) 
                layer_dissolver = QgsVectorLayer(rr_dissolver,'dissolver','ogr')

                selection = layerselect.selectedFeatures()
                list_id_select = []
                for feature_selec in selection:
                    list_id_select.append(feature_selec.id())

                #pr = layer_line.dataProvider()
                #for feature in layer_dissolver.getFeatures():
                #    geom_feat = feature.geometry()
                #    geom_feat_m = geom_feat.asMultiPolygon()
                #    for geom_listi in geom_feat_m:
                #        for geom_list_ti in geom_listi:
                #            feature_line = QgsFeature()

                #            geom_line =  QgsGeometry.fromPolylineXY(geom_list_ti)
                #            feature_line.setGeometry(geom_line)
                #            pr.addFeature(feature_line) 

                list_quadras = []         
                for feature in layer_dissolver.getFeatures():
                    geom_quadra =  feature.geometry()
                    for feature_Lote in layerselect.getFeatures():

                        geom_lote =  feature_Lote.geometry()
                        attr = feature_Lote.attributes() 
                        intersect = geom_quadra.intersection(geom_lote)
                        if intersect and feature_Lote.id() in list_id_select:
                            list_quadras.append(feature)
                            
                pr_lote = layerselect.dataProvider()
                for feature in list_quadras:
                    geom_quadra = feature.geometry()
                    for feature_Lote in layerselect.getFeatures():
                        geom_lote =  feature_Lote.geometry()
                        attr = feature_Lote.attributes() 
                        intersect = geom_quadra.intersection(geom_lote)
                        if intersect:
                            if feature_Lote.id() in list_id_select:
                                pr_lote.changeAttributeValues({feature_Lote.id(): { idcoluna: 'true'}})
                            else:
                                pr_lote.changeAttributeValues({feature_Lote.id(): { idcoluna: ''}})

                layerselect.removeSelection() 
                del layer_dissolver
                del layerselect





    def verificar_salvememeoria(self):
        verificar = self.dlg.salvememoria.isChecked()
        if verificar: 
            self.dlg.select_caminho.setEnabled(False)
            self.dlg.caminho.setEnabled(False)
            self.dlg.label_5.setEnabled(False)
        else: 
            self.dlg.select_caminho.setEnabled(True)
            self.dlg.caminho.setEnabled(True)
            self.dlg.label_5.setEnabled(True)

    def selecione_caminho(self):
        # Abri janela para escolher caminho onde vai salvar o shape
        filtering="Shapefiles (*.shp *.SHP)"
        settings = QSettings()
        dirName = settings.value("/UI/lastShapefileDir")
        encode = settings.value("/UI/encoding")
        fileDialog = QgsEncodingFileDialog(None, QCoreApplication.translate("fTools", "Save output shapefile"), dirName, filtering, encode)
        fileDialog.setDefaultSuffix("shp")
        fileDialog.setFileMode(QFileDialog.AnyFile)
        fileDialog.setAcceptMode(QFileDialog.AcceptSave)
        #fileDialog.setConfirmOverwrite(True)
        if not fileDialog.exec_() == QDialog.Accepted:
            return None, None

        files = fileDialog.selectedFiles()
        settings.setValue("/UI/lastShapefileDir", QFileInfo(unicode(files[0])).absolutePath())
        self.outFilePath = unicode(files[0])
        self.encoding = unicode(fileDialog.encoding())
        self.dlg.caminho.setText(self.outFilePath)
        self.nomeshape = files

    def run(self):
        """Run method that performs all the real work"""
        self.dlg.caminho.clear() 
        self.dlg.numeracaoS.setChecked(True)

        layers = QgsProject.instance().mapLayers().values()
        self.dlg.select_layer.clear()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.dlg.select_layer.addItem( layer.name(), layer )  
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        #if self.first_start == True:
        #    self.first_start = False
        #    self.dlg = numerar_loteDialog()

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.

            if not self.dlg.salvememoria.isChecked() and not self.dlg.caminho.text():
                self.iface.messageBar().pushMessage("Alerta", "Existe campos obrigatório sem preenchimento.", level=Qgis.Warning) 
            else: 
                shape_informacao = []
                layerselect = ''
                layer_line = QgsVectorLayer("LineString?", "layer_line", "memory" )
                for select in QgsProject.instance().mapLayers().values():
                    if select.name() == self.dlg.select_layer.currentText():
                        layerselect = select
                        sRs = layerselect.crs()
                        r_dissolver = dissolver(select) 
                        layer_dissolver = QgsVectorLayer(r_dissolver,'dissolver','ogr')

                        
                        pr = layer_line.dataProvider()
                        for feature in layer_dissolver.getFeatures():

                        #for feat in select.getFeatures():
                            geom_feat = feature.geometry()
                            geom_feat_m = geom_feat.asMultiPolygon()
                            for geom_listi in geom_feat_m:
                                for geom_list_ti in geom_listi:
                                    feature_line = QgsFeature()

                                    geom_line =  QgsGeometry.fromPolylineXY(geom_list_ti)
                                    feature_line.setGeometry(geom_line)
                                    pr.addFeature(feature_line) 


                #pr_layer_lotes = layerselect.dataProvider()
                lista_dados = []
                
                for feature in layer_line.getFeatures():
                    lista_ids = []
                    numero_lote = 0
                    d = 0
                    geom_quadra = feature.geometry()
                    filter = QgsFeatureRequest().setFilterExpression('"DEF_LOTE" = true')
                    for feature_Lote in layerselect.getFeatures(filter):
                        geom_lote =  feature_Lote.geometry()
                        attr = feature_Lote.attributes() 
                        intersect = geom_quadra.intersection(geom_lote)
                        if intersect:
                            if self.dlg.numeracaoS.isChecked():
                                numero_lote = numero_lote + 1
                                attr.append(numero_lote)

                            if self.dlg.numeracaoT.isChecked():
                                tamTestada = verificar_intersect(geom_quadra, geom_lote)
                                numero_lote = numero_lote + tamTestada
                                attr.append(numero_lote)

                            if d == 0:
                                lista_ids.append(feature_Lote.id())
                                lista_dados.append([geom_lote, attr])   

                            #attrs = { 1: numero_lote}
                            #pr_layer_lotes.changeAttributeValues({feature_Lote.id(): attrs})

                            wkb_q = geom_quadra.asWkb() 
                            geom_ogr_q = ogr.CreateGeometryFromWkb(wkb_q)
                            vertices = geom_quadra.asPolyline()
                            
                            wkb_i = intersect.asWkb() 
                            geom_ogr_i = ogr.CreateGeometryFromWkb(wkb_i)
                            tipo_line = intersect.wkbType()

                            cord = redefine_order(geom_ogr_q, vertices, geom_ogr_i, tipo_line)

                            for itens in cord:
                                qgs_cord = QgsPoint(itens[0],itens[1])
                                qgs_geom = QgsGeometry(qgs_cord)
                                for feature_Lote_1 in layerselect.getFeatures():
                                    geom_lote_1 =  feature_Lote_1.geometry()
                                    attr_1 = feature_Lote_1.attributes()
                                    intersect_1 = qgs_geom.intersection(geom_lote_1)
                                    if intersect_1:
                                        if feature_Lote_1.id() not in lista_ids :
                                            lista_ids.append(feature_Lote_1.id())
                                            if  self.dlg.numeracaoS.isChecked():
                                                numero_lote = numero_lote + 1
                                            if self.dlg.numeracaoT.isChecked():
                                                tamTestada = verificar_intersect(geom_quadra, geom_lote_1)
                                                numero_lote = numero_lote + tamTestada

                                            attr_1.append(numero_lote)
                                            lista_dados.append([geom_lote_1, attr_1])
                                            #attrs_2 = { 1: numero_lote}
                                            #pr_layer_lotes.changeAttributeValues({feature_Lote_1.id(): attrs_2})   
                
                field_names = layerselect.fields()

                if self.dlg.salvememoria.isChecked(): 

                    shapeLotes = QgsVectorLayer("polygon?crs=" + sRs.authid(), "LOTES", "memory" )
                    pr_shapeLotes = shapeLotes.dataProvider()

                    for field_attr in field_names:
                        pr_shapeLotes.addAttributes([QgsField(field_attr.name(),field_attr.type())])
                        shapeLotes.updateFields()

                    pr_shapeLotes.addAttributes([QgsField("NLATUAL", QVariant.Int)])
                    shapeLotes.updateFields()

                    for item in lista_dados:
                        self.featu = QgsFeature()
                        self.featu.setGeometry(item[0])
                        self.featu.setAttributes(item[1])
                        pr_shapeLotes.addFeature(self.featu)

                    QgsProject.instance().addMapLayer(shapeLotes)

                else:

                    self.Fields = QgsFields()

                    for field_attr in field_names:
                        self.Fields.append(QgsField(field_attr.name(),field_attr.type()))
                    self.Fields.append(QgsField("NLATUAL", QVariant.Int))

                    global SHPCaminho
                    SHPCaminho = self.outFilePath
                    self.shape_articulacao = QgsVectorFileWriter(SHPCaminho, self.encoding, self.Fields, QgsWkbTypes.Polygon, sRs, "ESRI Shapefile")
                    
                    for item in lista_dados:
                        self.featu = QgsFeature()
                        self.featu.setGeometry(item[0])
                        self.featu.setAttributes(item[1])
                        self.shape_articulacao.addFeature(self.featu)

                    pegarNome = self.outFilePath
                    Nomes = pegarNome.split( '/' )
                    contNomes = len(Nomes) - 1
                    nomefinalshp = Nomes[contNomes]
                    nomefinalshp =  nomefinalshp.replace('.shp','')
                    nomefinalshp =  nomefinalshp.replace('.SHP','')
                    self.layer = QgsVectorLayer(self.outFilePath, nomefinalshp, "ogr")
                    if not self.layer.isValid():
                        raise ValueError("Failed to open the layer")
                    self.canvas = QgsMapCanvas()
                    QgsProject.instance().addMapLayer(self.layer)
                    self.canvas.setExtent(self.layer.extent())
                    self.canvas.setLayers([self.layer])
                    del self.shape_articulacao
                    QgsProject.instance().removeMapLayer(self.layer)
                    self.layer = QgsVectorLayer(self.outFilePath, nomefinalshp, "ogr")
                    QgsProject.instance().addMapLayer(self.layer)
                












            pass
