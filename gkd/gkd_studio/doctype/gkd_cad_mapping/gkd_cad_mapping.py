# Copyright (c) 2026, raaj@akhilaminc.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

# The UOM a quantity basis produces, after lengths are converted to feet.
UOM_FOR_BASIS = {"Area": "Square Foot", "Length": "Running Foot", "Count": "Nos"}


class GKDCADMapping(Document):
	def validate(self):
		self.cad_layer = (self.cad_layer or "").strip().upper()
		self.cad_block = (self.cad_block or "").strip().upper()
		self.validate_unique()
		self.validate_basis_matches_uom()
		if flt(self.conversion_factor) <= 0:
			frappe.throw(_("Conversion Factor must be more than 0."), title=_("Invalid Conversion Factor"))

	def validate_unique(self):
		duplicate = frappe.db.exists(
			"GKD CAD Mapping",
			{"cad_layer": self.cad_layer, "cad_block": self.cad_block or ("is", "not set"), "name": ("!=", self.name)},
		)
		if duplicate:
			frappe.throw(
				_("Layer {0} with block {1} is already mapped in {2}.").format(
					frappe.bold(self.cad_layer), frappe.bold(self.cad_block or _("(any)")), frappe.bold(duplicate)
				),
				title=_("Duplicate CAD Mapping"),
			)

	def validate_basis_matches_uom(self):
		uom = frappe.db.get_value("Item", self.item, "stock_uom")
		expected = UOM_FOR_BASIS[self.quantity_basis]
		if uom != expected:
			frappe.throw(
				_("{0} measures in {1}, but item {2} is stocked in {3}. Pick another basis or item.").format(
					frappe.bold(_(self.quantity_basis)), frappe.bold(_(expected)), frappe.bold(self.item),
					frappe.bold(_(uom)),
				),
				title=_("Basis and UOM Do Not Match"),
			)
