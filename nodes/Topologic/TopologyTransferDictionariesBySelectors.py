import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty
from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import updateNode

import topologic
from topologic import Vertex, Edge, Wire, Face, Shell, Cell, CellComplex, Cluster, Topology, Dictionary
import time

# From https://stackabuse.com/python-how-to-flatten-list-of-lists/
def flatten(element):
	returnList = []
	if isinstance(element, list) == True:
		for anItem in element:
			returnList = returnList + flatten(anItem)
	else:
		returnList = [element]
	return returnList

def relevantSelector(topology):
	returnVertex = None
	if topology.Type() == topologic.Vertex.Type():
		return topology
	elif topology.Type() == topologic.Edge.Type():
		return topologic.EdgeUtility.PointAtParameter(topology, 0.5)
	elif topology.Type() == topologic.Face.Type():
		return topologic.FaceUtility.InternalVertex(topology, 0.0001)
	elif topology.Type() == topologic.Cell.Type():
		return topologic.CellUtility.InternalVertex(topology, 0.0001)
	else:
		return topology.CenterOfMass()

def topologyContains(topology, vertex, tol):
	contains = False
	if topology.Type() == topologic.Vertex.Type():
		try:
			contains = (topologic.VertexUtility.Distance(topology, vertex) <= tol)
		except:
			contains = False
		return contains
	elif topology.Type() == topologic.Edge.Type():
		try:
			_ = topologic.EdgeUtility.ParameterAtPoint(topology, vertex)
			contains = True
		except:
			contains = False
		return contains
	elif topology.Type() == topologic.Face.Type():
		return topologic.FaceUtility.IsInside(topology, vertex, tol)
	elif topology.Type() == topologic.Cell.Type():
		return (topologic.CellUtility.Contains(topology, vertex, tol) == 0)
	return False

def listAttributeValues(listAttribute):
	listAttributes = listAttribute.ListValue()
	returnList = []
	for attr in listAttributes:
		if isinstance(attr, topologic.IntAttribute):
			returnList.append(attr.IntValue())
		elif isinstance(attr, topologic.DoubleAttribute):
			returnList.append(attr.DoubleValue())
		elif isinstance(attr, topologic.StringAttribute):
			returnList.append(attr.StringValue())
	return returnList

def valueAtKey(item, key):
	try:
		attr = item.ValueAtKey(key)
	except:
		raise Exception("Dictionary.ValueAtKey - Error: Could not retrieve a Value at the specified key ("+key+")")
	if isinstance(attr, topologic.IntAttribute):
		return (attr.IntValue())
	elif isinstance(attr, topologic.DoubleAttribute):
		return (attr.DoubleValue())
	elif isinstance(attr, topologic.StringAttribute):
		return (attr.StringValue())
	elif isinstance(attr, topologic.ListAttribute):
		return (listAttributeValues(attr))
	else:
		return None

def processKeysValues(keys, values):
	if len(keys) != len(values):
		raise Exception("DictionaryByKeysValues - Keys and Values do not have the same length")
	stl_keys = []
	stl_values = []
	for i in range(len(keys)):
		if isinstance(keys[i], str):
			stl_keys.append(keys[i])
		else:
			stl_keys.append(str(keys[i]))
		if isinstance(values[i], list) and len(values[i]) == 1:
			value = values[i][0]
		else:
			value = values[i]
		if isinstance(value, bool):
			if value == False:
				stl_values.append(topologic.IntAttribute(0))
			else:
				stl_values.append(topologic.IntAttribute(1))
		elif isinstance(value, int):
			stl_values.append(topologic.IntAttribute(value))
		elif isinstance(value, float):
			stl_values.append(topologic.DoubleAttribute(value))
		elif isinstance(value, str):
			stl_values.append(topologic.StringAttribute(value))
		elif isinstance(value, list):
			l = []
			for v in value:
				if isinstance(v, bool):
					l.append(topologic.IntAttribute(v))
				elif isinstance(v, int):
					l.append(topologic.IntAttribute(v))
				elif isinstance(v, float):
					l.append(topologic.DoubleAttribute(v))
				elif isinstance(v, str):
					l.append(topologic.StringAttribute(v))
			stl_values.append(topologic.ListAttribute(l))
		else:
			raise Exception("Error: Value type is not supported. Supported types are: Boolean, Integer, Double, String, or List.")
	myDict = topologic.Dictionary.ByKeysValues(stl_keys, stl_values)
	return myDict

def transferDictionariesOld(sources, sinks, tol):
	usedSources = []
	for i in range(len(sources)):
		usedSources.append(False)
	print(usedSources)
	for i in range(len(sinks)):
		print("sink")
		for j in range(len(sources)):
			print("  "+ str(j))
			source = sources[j]
			if usedSources[j] == False:
				iv = relevantSelector(sources[j])
				if topologyContains(sinks[i], iv, tol):
					usedSources[j] = True
					d = sources[j].GetDictionary()
					if d == None:
						continue
					else:
						_ = sinks[i].SetDictionary(d)

def transferDictionaries(sources, sinks, tol):
	usedSources = []
	for i in range(len(sources)):
		usedSources.append(False)
	for sink in sinks:
		sinkKeys = []
		sinkValues = []
		for j in range(len(sources)):
			source = sources[j]
			if usedSources[j] == False:
				iv = relevantSelector(source)
				if topologyContains(sink, iv, tol):
					usedSources[j] = True
					d = source.GetDictionary()
					if d == None:
						continue
					else:
						stlKeys = d.Keys()
						if len(stlKeys) > 0:
							sourceKeys = d.Keys()
							for aSourceKey in sourceKeys:
								if aSourceKey not in sinkKeys:
									sinkKeys.append(aSourceKey)
									sinkValues.append("")
							for i in range(len(sourceKeys)):
								index = sinkKeys.index(sourceKeys[i])
								sourceValue = valueAtKey(d, sourceKeys[i])
								if sourceValue != None:
									if sinkValues[index] != "":
										if isinstance(sinkValues[index], list):
											sinkValues[index].append(sourceValue)
										else:
											sinkValues[index] = [sinkValues[index], sourceValue]
									else:
										sinkValues[index] = sourceValue
		if len(sinkKeys) > 0 and len(sinkValues) > 0:
			newDict = processKeysValues(sinkKeys, sinkValues)
			_ = sink.SetDictionary(newDict)
		else:
			print("**** ERROR ****")

def highestDimension(topology):
	if (topology.Type() == topologic.Cluster.Type()):
		cellComplexes = []
		_ = topology.CellComplexes(cellComplexes)
		if len(cellComplexes) > 0:
			return topologic.CellComplex.Type()
		cells = []
		_ = topology.Cells(cells)
		if len(cells) > 0:
			return topologic.Cell.Type()
		shells = []
		_ = topology.Shells(shells)
		if len(shells) > 0:
			return topologic.Shell.Type()
		faces = []
		_ = topology.Faces(faces)
		if len(faces) > 0:
			return topologic.Face.Type()
		wires = []
		_ = topology.Wires(wires)
		if len(wires) > 0:
			return topologic.Wire.Type()
		edges = []
		_ = topology.Edges(edges)
		if len(edges) > 0:
			return topologic.Edge.Type()
		vertices = []
		_ = topology.Vertices(vertices)
		if len(vertices) > 0:
			return topologic.Vertex.Type()
	else:
		return(topology.Type())

def processItem(sources, sink, tranVertices, tranEdges, tranFaces, tranCells, tolerance):
	sourceVertices = []
	sourceEdges = []
	sourceFaces = []
	sourceCells = []
	sinVertices = []
	sinkEdges = []
	sinkFaces = []
	sinkCells = []
	hidimSink = highestDimension(sink)
	if tranVertices == True:
		sinkVertices = []
		if sink.Type() == topologic.Vertex.Type():
			sinkVertices.append(sink)
		elif hidimSink >= topologic.Vertex.Type():
			sink.Vertices(sinkVertices)
		_ = transferDictionaries(sources, sinkVertices, tolerance)
	if tranEdges == True:
		sinkEdges = []
		if sink.Type() == topologic.Edge.Type():
			sinkEdges.append(sink)
		elif hidimSink >= topologic.Edge.Type():
			sink.Edges(sinkEdges)
			_ = transferDictionaries(sources, sinkEdges, tolerance)
	if tranFaces == True:
		sinkFaces = []
		if sink.Type() == topologic.Face.Type():
			sinkFaces.append(sink)
		elif hidimSink >= topologic.Face.Type():
			sink.Faces(sinkFaces)
		_ = transferDictionaries(sources, sinkFaces, tolerance)
	if tranCells == True:
		sinkCells = []
		if sink.Type() == topologic.Cell.Type():
			sinkCells.append(sink)
		elif hidimSink >= topologic.Cell.Type():
			sink.Cells(sinkCells)
		_ = transferDictionaries(sources, sinkCells, tolerance)
	return sink

class SvTopologyTransferDictionariesBySelectors(bpy.types.Node, SverchCustomTreeNode):

	"""
	Triggers: Topologic
	Tooltip: Transfers the Dictionaries of the source Topologies to the sink Topology based on location of input selectors
	"""
	bl_idname = 'SvTopologyTransferDictionariesBySelectors'
	bl_label = 'Topology.TransferDictionariesBySelectors'
	TransferVertexDicts: BoolProperty(name="Transfer to Vertices", default=True, update=updateNode)
	TransferEdgeDicts: BoolProperty(name="Transfer to Edges", default=True, update=updateNode)
	TransferFaceDicts: BoolProperty(name="Transfer to Faces", default=True, update=updateNode)
	TransferCellDicts: BoolProperty(name="Transfer to Cells", default=True, update=updateNode)
	Tolerance: FloatProperty(name="Tolerance",  default=0.001, precision=4, update=updateNode)

	def sv_init(self, context):
		self.inputs.new('SvStringsSocket', 'Selectors')
		self.inputs.new('SvStringsSocket', 'Sink')
		self.inputs.new('SvStringsSocket', 'Transfer Vertex Dicts').prop_name = 'TransferVertexDicts'
		self.inputs.new('SvStringsSocket', 'Transfer Edge Dicts').prop_name = 'TransferEdgeDicts'
		self.inputs.new('SvStringsSocket', 'Transfer Face Dicts').prop_name = 'TransferFaceDicts'
		self.inputs.new('SvStringsSocket', 'Transfer Cell Dicts').prop_name = 'TransferCellDicts'
		self.inputs.new('SvStringsSocket', 'Tolerance').prop_name = 'Tolerance'
		self.outputs.new('SvStringsSocket', 'Sink')

	def process(self):
		start = time.time()
		if not any(socket.is_linked for socket in self.outputs):
			return
		if not any(socket.is_linked for socket in self.inputs):
			self.outputs['Topology'].sv_set([])
			return
		sources = self.inputs['Selectors'].sv_get(deepcopy=False)
		sink = self.inputs['Sink'].sv_get(deepcopy=False)[0]
		tranVertexDicts = self.inputs['Transfer Vertex Dicts'].sv_get(deepcopy=False)[0][0]
		tranEdgeDicts = self.inputs['Transfer Edge Dicts'].sv_get(deepcopy=False)[0][0]
		tranFaceDicts = self.inputs['Transfer Face Dicts'].sv_get(deepcopy=False)[0][0]
		tranCellDicts = self.inputs['Transfer Cell Dicts'].sv_get(deepcopy=False)[0][0]
		tolerance = self.inputs['Tolerance'].sv_get(deepcopy=False)[0][0]
		output = processItem(sources, sink, tranVertexDicts, tranEdgeDicts, tranFaceDicts, tranCellDicts, tolerance)
		self.outputs['Sink'].sv_set([output])
		end = time.time()
		print("Topology.TransferDictionaries Operation consumed "+str(round(end - start,2))+" seconds")

def register():
    bpy.utils.register_class(SvTopologyTransferDictionariesBySelectors)

def unregister():
    bpy.utils.unregister_class(SvTopologyTransferDictionariesBySelectors)
