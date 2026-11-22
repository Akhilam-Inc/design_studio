# Copyright (c) 2026, raaj@akhilaminc.com and Contributors
# See license.txt

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from gkd.setup.masters import COMPANY
from gkd.setup.roles import ROLE_PROFILES

# Every fixture below is built in the test and rolled back, so no generic test records are needed.
IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Project", "Customer", "Company", "Employee", "Item", "Supplier", "UOM", "GKD Trade", "User",
	"Workflow State",
]

DESIGNER = "gkd.test.designer@example.com"
SUPERVISOR = "gkd.test.supervisor@example.com"
PM = "gkd.test.pm@example.com"


class IntegrationTestGKDProjectBOQ(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_user(DESIGNER, "GKD Designer")
		make_user(SUPERVISOR, "GKD Site Supervisor")
		make_user(PM, "GKD Project Manager")
		cls.supervisor = make_employee("Test Supervisor", SUPERVISOR)
		cls.project = make_project(cls.supervisor)
		cls.item = make_item()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_totals_and_site_variance(self):
		boq = make_boq(self.project, self.item)
		self.assertEqual(boq.items[0].boq_qty, 100, "BOQ qty defaults to design qty")
		self.assertEqual(boq.total_boq_amount, 100 * 250 + 40 * 1200)

		boq.items[0].site_verified_qty = 110
		boq.save()
		self.assertEqual(boq.variance_value, 10 * 250)

	def test_supervisor_is_fetched_and_assigned(self):
		frappe.set_user(DESIGNER)
		boq = make_boq(self.project, self.item)
		self.assertEqual(boq.site_supervisor_user, SUPERVISOR)

		boq = apply_workflow(boq, "Send for Site Verification")
		self.assertEqual(boq.workflow_state, "Pending Site Verification")
		self.assertTrue(
			frappe.db.exists("ToDo", {"reference_name": boq.name, "allocated_to": SUPERVISOR, "status": "Open"})
		)

	def test_full_approval_flow_as_each_role(self):
		frappe.set_user(DESIGNER)
		boq = apply_workflow(make_boq(self.project, self.item), "Send for Site Verification")

		frappe.set_user(SUPERVISOR)
		boq = frappe.get_doc("GKD Project BOQ", boq.name)
		self.assertRaises(frappe.ValidationError, apply_workflow, boq, "Verify")
		boq.reload()
		boq.update({"visit_date": today(), "verified_by": self.supervisor})
		boq.items[0].site_verified_qty = 104
		boq.save()
		boq = apply_workflow(boq, "Verify")
		self.assertEqual(boq.workflow_state, "Site Verified")

		frappe.set_user(PM)
		boq = apply_workflow(frappe.get_doc("GKD Project BOQ", boq.name), "Send to Customer")
		# The dual-approval gate: no customer sign-off, no approval.
		self.assertRaises(frappe.ValidationError, apply_workflow, boq, "Approve")
		boq.reload()
		boq.update({"customer_approved": 1, "approved_by_name": "Mr. Mehta", "approval_date": today()})
		boq.save()
		# Ticking the box is not enough: the client's signed copy must be on file.
		self.assertRaises(frappe.ValidationError, apply_workflow, boq, "Approve")
		boq.reload()
		boq.signed_copy = "/private/files/signed-boq.pdf"
		boq.save()
		boq = apply_workflow(boq, "Approve")
		self.assertEqual((boq.workflow_state, boq.docstatus), ("Approved", 1))

		self.assertFalse(
			frappe.db.exists("ToDo", {"reference_name": boq.name, "status": "Open"}),
			"the supervisor's task stays closed after the BOQ moves past site verification",
		)
		# Handing over needs contractor orders, so the bare workflow action is refused.
		self.assertRaises(frappe.ValidationError, apply_workflow, boq, "Hand Over")

	def test_designer_cannot_verify_or_approve(self):
		frappe.set_user(DESIGNER)
		boq = apply_workflow(make_boq(self.project, self.item), "Send for Site Verification")
		boq.update({"visit_date": today(), "verified_by": self.supervisor})
		self.assertRaises(frappe.ValidationError, apply_workflow, boq, "Verify")

	def test_contract_prints_boq_annexure(self):
		boq = make_boq(self.project, self.item)
		frappe.set_user(PM)
		contract = frappe.get_doc({
			"doctype": "Contract",
			"party_type": "Customer",
			"party_name": self.project_customer(),
			"start_date": today(),
			"contract_template": "GKD Interior Works Agreement",
			"gkd_project_boq": boq.name,
			"contract_terms": "<p>Terms</p>",
		}).insert()
		html = frappe.get_print("Contract", contract.name, print_format="GKD Contract")
		self.assertIn("Annexure A", html)
		self.assertIn(boq.name, html)
		self.assertIn("&lt;b&gt;Living&lt;/b&gt;", html, "room names are escaped")

	def project_customer(self):
		return frappe.db.get_value("Project", self.project, "customer")


def make_boq(project, item):
	return frappe.get_doc({
		"doctype": "GKD Project BOQ",
		"project": project,
		"items": [
			{"room_area": "<b>Living</b>", "item": item, "design_qty": 100, "rate": 250, "trade": "Carpentry"},
			{"room_area": "Master Bedroom", "item": item, "design_qty": 40, "boq_qty": 40, "rate": 1200},
		],
	}).insert()


def make_user(email, gkd_role):
	"""A user with the same roles as the GKD role profile, so tests see what real users see."""
	if frappe.db.exists("User", email):
		return
	user = frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
	user.insert(ignore_permissions=True)
	user.add_roles(gkd_role, *ROLE_PROFILES[gkd_role])


def make_employee(name, user):
	return frappe.get_doc({
		"doctype": "Employee",
		"first_name": name,
		"gender": "Female",
		"date_of_birth": "1990-01-01",
		"date_of_joining": "2024-01-01",
		"company": COMPANY,
		"user_id": user,
		"create_user_permission": 0,
	}).insert(ignore_permissions=True).name


def make_project(supervisor):
	customer = frappe.get_doc({
		"doctype": "Customer", "customer_name": "GKD Test Client", "customer_type": "Individual",
	}).insert(ignore_permissions=True, ignore_if_duplicate=True)
	return frappe.get_doc({
		"doctype": "Project",
		"project_name": "GKD Test Residence",
		"company": COMPANY,
		"customer": customer.name,
		"gkd_site_type": "Residential",
		"gkd_site_supervisor": supervisor,
	}).insert(ignore_permissions=True).name


def make_item():
	code = "GKD-TEST-VENEER"
	if not frappe.db.exists("Item", code):
		frappe.get_doc({
			"doctype": "Item", "item_code": code, "item_name": "Teak Veneer Panelling", "item_group": "Carpentry",
			"stock_uom": "Square Foot", "is_stock_item": 0,
		}).insert(ignore_permissions=True)
	return code
