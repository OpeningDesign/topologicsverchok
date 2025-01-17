import bpy
from bpy.props import IntProperty, FloatProperty, StringProperty
from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import updateNode

try:
	import openstudio
except:
	raise Exception("Error: Could not import openstudio.")

# From https://stackabuse.com/python-how-to-flatten-list-of-lists/
def flatten(element):
	returnList = []
	if isinstance(element, list) == True:
		for anItem in element:
			returnList = returnList + flatten(anItem)
	else:
		returnList = [element]
	return returnList

def processItem(item):
    translator = openstudio.osversion.VersionTranslator()
    osmFile = openstudio.openstudioutilitiescore.toPath(item)
    model = translator.loadModel(osmFile)
    if model.isNull():
        raise Exception("File Path is not a valid path to an OpenStudio Model")
        return None
    else:
        model = model.get()
    return model
		
class SvEnergyModelByImportedOSM(bpy.types.Node, SverchCustomTreeNode):
	"""
	Triggers: Topologic
	Tooltip: Creates an Energy Model from the input OSM file
	"""
	bl_idname = 'SvEnergyModelByImportedOSM'
	bl_label = 'EnergyModel.ByImportedOSM'
	def sv_init(self, context):
		self.inputs.new('SvStringsSocket', 'File Path')
		self.outputs.new('SvStringsSocket', 'Energy Model')

	def process(self):
		if not any(socket.is_linked for socket in self.outputs):
			return
		if not any(socket.is_linked for socket in self.inputs):
			self.outputs['Eneregy Model'].sv_set([])
			return
		inputs = self.inputs['File Path'].sv_get(deepcopy=False)
		inputs = flatten(inputs)
		outputs = []
		for anInput in inputs:
			outputs.append(processItem(anInput))
		self.outputs['Energy Model'].sv_set(outputs)

def register():
	bpy.utils.register_class(SvEnergyModelByImportedOSM)

def unregister():
	bpy.utils.unregister_class(SvEnergyModelByImportedOSM)
