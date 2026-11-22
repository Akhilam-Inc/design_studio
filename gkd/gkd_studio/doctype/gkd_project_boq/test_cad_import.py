import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase

from gkd.gkd_studio.cad_import import import_cad_export
from gkd.gkd_studio.doctype.gkd_project_boq.test_gkd_project_boq import (
	DESIGNER, SUPERVISOR, make_employee, make_project, make_user,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Project", "Customer", "Company", "Employee", "Item", "Supplier", "User"]

HEADER = "Room,Layer,Block,Description,Length,Width,Count,Unit"
# 3048 mm is 10 ft. The floor mapping adds 5% wastage.
DRAWING_R0 = "\n".join([
	HEADER,
	"Living,ZT-FLOR,,Floor,3048,3048,1,mm",
	"Living,ZT-LITE,DL,Downlight,,,4,mm",
	"Living,ZT-LITE,DL,Downlight,,,2,mm",
	"Living,ZT-STRP,,LED strip,3048,,1,mm",
	"Bedroom,ZT-FLOR,,Floor,12,10,1,ft",
	"Bedroom,ZT-BED,QUEEN,Client's own bed,,,1,mm",
])


class TestCADImport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_user(DESIGNER, "GKD Designer")
		make_user(SUPERVISOR, "GKD Site Supervisor")
		cls.project = make_project(make_employee("Test Supervisor", SUPERVISOR))
		cls.items = {
			"floor": make_item("GKD-TEST-TILE", "Square Foot"),
			"light": make_item("GKD-TEST-LIGHT", "Nos"),
			"strip": make_item("GKD-TEST-STRIP", "Running Foot"),
		}
		for layer, block, basis, key, factor in [
			("ZT-FLOR", "", "Area", "floor", 1.05),
			("ZT-LITE", "DL", "Count", "light", 1),
			("ZT-STRP", "", "Length", "strip", 1),
		]:
			frappe.get_doc({"doctype": "GKD CAD Mapping", "cad_layer": layer, "cad_block": block,
				"quantity_basis": basis, "item": cls.items[key], "conversion_factor": factor}).insert()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_import_measures_converts_and_groups(self):
		frappe.set_user(DESIGNER)
		boq = empty_boq(self.project)
		result = import_cad_export(boq.name, attach(boq, DRAWING_R0, "r0.csv"))
		boq.reload()

		self.assertEqual((result["objects"], result["lines"], result["added"]), (6, 4, 4))
		self.assertEqual([(u["layer"], u["block"]) for u in result["unmapped"]], [("ZT-BED", "QUEEN")])
		qty = {(row.room_area, row.item): row.design_qty for row in boq.items}
		self.assertAlmostEqual(qty[("Living", self.items["floor"])], 105, places=2, msg="10 x 10 ft plus 5%")
		self.assertEqual(qty[("Living", self.items["light"])], 6, "two blocks of the same type are summed")
		self.assertAlmostEqual(qty[("Living", self.items["strip"])], 10, places=2)
		self.assertAlmostEqual(qty[("Bedroom", self.items["floor"])], 126, places=2, msg="feet are read as feet")
		self.assertTrue(all(row.boq_qty == row.design_qty and row.cad_ref for row in boq.items))
		self.assertTrue(boq.cad_file and boq.cad_imported_on)

	def test_reimport_updates_in_place_and_keeps_manual_work(self):
		frappe.set_user(DESIGNER)
		boq = empty_boq(self.project)
		import_cad_export(boq.name, attach(boq, DRAWING_R0, "r0.csv"))
		boq.reload()
		boq.append("items", {"room_area": "Living", "item": self.items["floor"], "design_qty": 5, "rate": 100})
		light = next(row for row in boq.items if row.item == self.items["light"])
		light.boq_qty = 8  # the designer added two lights by hand
		boq.save()

		revised = DRAWING_R0.replace("Living,ZT-STRP,,LED strip,3048,,1,mm\n", "").replace(
			"Living,ZT-FLOR,,Floor,3048,3048", "Living,ZT-FLOR,,Floor,6096,3048")
		revised = revised.replace(",,,2,mm", ",,,3,mm")
		result = import_cad_export(boq.name, attach(boq, revised, "r1.csv"))
		boq.reload()

		self.assertEqual((result["added"], result["updated"], result["removed"]), (0, 2, 1))
		cad_floor = next(r for r in boq.items if r.cad_ref and r.item == self.items["floor"] and r.room_area == "Living")
		self.assertAlmostEqual((cad_floor.design_qty, cad_floor.boq_qty), (210, 210), places=2)
		light = next(row for row in boq.items if row.item == self.items["light"])
		self.assertEqual((light.design_qty, light.boq_qty), (7, 8), "a hand-edited BOQ qty is kept")
		self.assertTrue(any(not row.cad_ref and row.design_qty == 5 for row in boq.items), "manual row kept")
		self.assertFalse(any(row.item == self.items["strip"] for row in boq.items), "removed from drawing")

	def test_guards(self):
		frappe.set_user(DESIGNER)
		boq = empty_boq(self.project)
		other = empty_boq(self.project)
		stray = attach(other, DRAWING_R0, "elsewhere.csv")
		self.assertRaises(frappe.ValidationError, import_cad_export, boq.name, stray)
		self.assertRaises(frappe.ValidationError, import_cad_export, boq.name, attach(boq, "a,b\n1,2", "bad.csv"))
		with self.assertRaises(frappe.ValidationError):
			import_cad_export(boq.name, attach(boq, HEADER + "\nLiving,ZT-FLOR,,Floor,1,1,1,yards", "unit.csv"))
		self.assertRaises(frappe.ValidationError, apply_workflow, boq, "Send for Site Verification")

	def test_mapping_basis_must_match_item_uom(self):
		mapping = frappe.get_doc({"doctype": "GKD CAD Mapping", "cad_layer": "ZT-WRONG", "quantity_basis": "Count",
			"item": self.items["floor"], "conversion_factor": 1})
		self.assertRaises(frappe.ValidationError, mapping.insert)
		duplicate = frappe.get_doc({"doctype": "GKD CAD Mapping", "cad_layer": "zt-flor", "quantity_basis": "Area",
			"item": self.items["floor"], "conversion_factor": 1})
		self.assertRaises(frappe.ValidationError, duplicate.insert)


def empty_boq(project):
	return frappe.get_doc({"doctype": "GKD Project BOQ", "project": project}).insert()


def attach(boq, content, file_name):
	return frappe.get_doc({
		"doctype": "File", "file_name": f"{boq.name}-{file_name}", "content": content, "is_private": 1,
		"attached_to_doctype": boq.doctype, "attached_to_name": boq.name,
	}).insert().file_url


def make_item(code, uom):
	if not frappe.db.exists("Item", code):
		frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": code, "item_group": "Carpentry",
			"stock_uom": uom, "is_stock_item": 0}).insert(ignore_permissions=True)
	return code
