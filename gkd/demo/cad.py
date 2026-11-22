"""CAD layer and block mappings, and the Bhatia BOQ built from the architect's CAD quantity export."""

import os

import frappe

from gkd.demo.people import acting_as
from gkd.gkd_studio.cad_import import import_cad_export

EXPORTS = frappe.get_app_path("gkd", "public", "demo")

# (layer, block, quantity basis, item, trade, conversion factor)
MAPPINGS = [
	("A-FLOR-TILE", "", "Area", "FLR-VITRIFIED", "Civil", 1.05),  # 5% cutting wastage
	("A-FLOR-WOOD", "", "Area", "FLR-OAK", "Civil", 1.05),
	("A-FLOR-MRBL", "", "Area", "FLR-STATUARIO", "Civil", 1.08),  # 8% for vein matching
	("A-FLOR-SKRT", "", "Length", "FLR-SKIRTING", "Civil", 1),
	("A-CNTR-GRNT", "", "Length", "FLR-GRANITE-TOP", "Civil", 1),
	("A-CLNG-GYPS", "", "Area", "FC-GYPSUM", "False Ceiling", 1),
	("A-CLNG-COVE", "", "Length", "FC-COVE", "False Ceiling", 1),
	("A-CLNG-SLAT", "", "Area", "FC-WOOD-SLAT", "False Ceiling", 1),
	("A-WALL-PNT", "", "Area", "PNT-EMULSION", "Painting", 1),
	("A-WALL-TXTR", "", "Area", "PNT-TEXTURE", "Painting", 1),
	("A-WALL-PANL", "", "Area", "CRP-PANELLING", "Carpentry", 1),
	("A-WALL-BRCK", "", "Area", "CIV-BRICK-WALL", "Civil", 1),
	("P-WTPF", "", "Area", "CIV-WATERPROOF", "Civil", 1.1),  # 10% for the wall upturn
	("A-FURN-CASE", "WARDROBE-SLIDING", "Area", "CRP-WARDROBE", "Carpentry", 1),
	("A-FURN-CASE", "TV-UNIT", "Area", "CRP-TV-UNIT", "Carpentry", 1),
	("A-FURN-KTCH", "KITCHEN-BASE", "Length", "CRP-KITCHEN-BASE", "Carpentry", 1),
	("A-FURN-KTCH", "KITCHEN-WALL", "Length", "CRP-KITCHEN-WALL", "Carpentry", 1),
	("A-FURN-CASE", "DISPLAY-SHELF", "Length", "CRP-DISPLAY", "Carpentry", 1),
	("A-DOOR", "DOOR-FLUSH", "Count", "CRP-DOOR", "Carpentry", 1),
	("A-GLAZ-PART", "", "Area", "HW-GLASS-PARTITION", "Carpentry", 1),
	("A-GLAZ-MIRR", "", "Area", "HW-MIRROR", "Carpentry", 1),
	("E-LITE", "DL-12W", "Count", "LGT-DOWNLIGHT", "Lighting", 1),
	("E-LITE", "PENDANT", "Count", "LGT-PENDANT", "Lighting", 1),
	("E-LITE", "TRACK-20W", "Count", "LGT-TRACK", "Lighting", 1),
	("E-LITE-STRP", "", "Length", "LGT-PROFILE", "Lighting", 1),
	("E-POWR", "", "Count", "ELE-POINT", "Electrical", 1),
	("E-DATA", "", "Count", "ELE-DATA", "Electrical", 1),
	("A-SOFT-CRTN", "", "Length", "SFT-CURTAIN", "Furniture", 1),
	("A-FURN-LOOS", "SOFA-3S", "Count", "FUR-SOFA", "Furniture", 1),
	("A-FURN-LOOS", "DINING-6S", "Count", "FUR-DINING", "Furniture", 1),
]


def create_mappings():
	for layer, block, basis, item, trade, factor in MAPPINGS:
		if frappe.db.exists("GKD CAD Mapping", {"cad_layer": layer, "cad_block": block or ("is", "not set")}):
			continue
		frappe.get_doc({
			"doctype": "GKD CAD Mapping", "cad_layer": layer, "cad_block": block, "quantity_basis": basis,
			"item": item, "default_trade": trade, "conversion_factor": factor,
		}).insert(ignore_permissions=True)


def import_export(boq_name, designer, file_name):
	"""The designer attaches the architect's export to the BOQ and imports it."""
	if os.path.basename(file_name) != file_name:
		frappe.throw(f"Demo export must be a plain file name: {file_name}")
	with acting_as(designer):
		# nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal -- reviewed: plain file name, inside the app's demo folder
		with open(os.path.join(EXPORTS, file_name), "rb") as export:
			file = frappe.get_doc({
				"doctype": "File", "file_name": file_name, "is_private": 1, "content": export.read(),
				"attached_to_doctype": "GKD Project BOQ", "attached_to_name": boq_name,
			}).insert()
		return import_cad_export(boq_name, file.file_url)
