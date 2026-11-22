import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from gkd.gkd_studio.boq_actions import create_contractor_orders, make_contract
from gkd.gkd_studio.doctype.gkd_project_boq.test_gkd_project_boq import (
	DESIGNER, PM, SUPERVISOR, make_employee, make_item, make_project, make_user,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Project", "Customer", "Company", "Employee", "Item", "Supplier", "User"]

CARPENTER = "GKD Test Carpentry Co"
ELECTRICIAN = "GKD Test Electricals"


class TestBOQActions(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_user(DESIGNER, "GKD Designer")
		make_user(SUPERVISOR, "GKD Site Supervisor")
		make_user(PM, "GKD Project Manager")
		cls.supervisor = make_employee("Test Supervisor", SUPERVISOR)
		cls.project = make_project(cls.supervisor)
		cls.item = make_item()
		for name in (CARPENTER, ELECTRICIAN):
			if not frappe.db.exists("Supplier", name):
				frappe.get_doc({"doctype": "Supplier", "supplier_name": name, "supplier_type": "Company",
					"supplier_group": "Contractor"}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_contractor_orders_split_by_contractor_at_approved_qty(self):
		boq = approved_boq(self)
		frappe.set_user(PM)
		orders = create_contractor_orders(boq.name)

		self.assertEqual(len(orders), 2, "one order per contractor")
		carpentry = frappe.get_doc("Purchase Order", {"supplier": CARPENTER, "gkd_project_boq": boq.name})
		self.assertEqual(carpentry.docstatus, 0, "orders are drafts for the PM to review")
		self.assertEqual([row.qty for row in carpentry.items], [110, 40], "site verified qty, else BOQ qty")
		self.assertEqual(carpentry.items[0].gkd_room_area, "Living")
		self.assertEqual(frappe.db.get_value("GKD Project BOQ", boq.name, "workflow_state"), "Handed Over")

		self.assertRaises(frappe.ValidationError, create_contractor_orders, boq.name)

	def test_orders_need_an_approved_boq_and_a_manager(self):
		boq = approved_boq(self, stop_before_approval=True)
		frappe.set_user(PM)
		self.assertRaises(frappe.ValidationError, create_contractor_orders, boq.name)

		frappe.set_user("Administrator")
		boq = approved_boq(self)
		frappe.set_user(DESIGNER)
		self.assertRaises(frappe.PermissionError, create_contractor_orders, boq.name)
		self.assertFalse(frappe.db.exists("Purchase Order", {"gkd_project_boq": boq.name}))

	def test_make_contract_prefills_client_boq_and_terms(self):
		boq = approved_boq(self)
		frappe.set_user(PM)
		contract = make_contract(boq.name)
		self.assertEqual((contract.party_type, contract.party_name), ("Customer", boq.customer))
		self.assertEqual(contract.gkd_project_boq, boq.name)
		self.assertIn(boq.name, contract.contract_terms)
		self.assertEqual(len(contract.fulfilment_terms), 4, "one row per payment milestone")

	def test_actual_qty_after_approval_updates_variance(self):
		boq = approved_boq(self)
		boq.items[1].actual_qty = 44
		boq.save()
		self.assertAlmostEqual(boq.items[1].variance_pct, 10)
		self.assertEqual(boq.variance_value, 10 * 250 + 4 * 1200)


def approved_boq(test, stop_before_approval=False):
	"""A BOQ taken through the workflow: one row measured at site, one not."""
	boq = frappe.get_doc({
		"doctype": "GKD Project BOQ",
		"project": test.project,
		"items": [
			{"room_area": "Living", "item": test.item, "design_qty": 100, "rate": 250, "contractor": CARPENTER},
			{"room_area": "Bedroom", "item": test.item, "design_qty": 40, "rate": 1200, "contractor": CARPENTER},
			{"room_area": "Living", "item": test.item, "design_qty": 30, "rate": 1650, "contractor": ELECTRICIAN},
		],
	}).insert()
	boq = apply_workflow(boq, "Send for Site Verification")
	boq.update({"visit_date": today(), "verified_by": test.supervisor})
	boq.items[0].site_verified_qty = 110
	boq.save()
	boq = apply_workflow(boq, "Verify")
	boq = apply_workflow(boq, "Send to Customer")
	if stop_before_approval:
		return boq
	boq.update({"customer_approved": 1, "approved_by_name": "Mrs. Rao", "approval_date": today(),
		"signed_copy": "/private/files/signed-boq.pdf"})
	boq.save()
	return apply_workflow(boq, "Approve")
