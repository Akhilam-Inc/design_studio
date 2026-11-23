# Copyright (c) 2026, raaj@akhilaminc.com and Contributors
# See license.txt

# Executed quantities: a submitted daily report adds the quantity done to the approved BOQ line.
# Each test files its report on a day of its own, because records persist across the tests of a class.

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from gkd.gkd_studio.doctype.gkd_project_boq.test_boq_actions import (
	CARPENTER, ELECTRICIAN, approved_boq,
)
from gkd.gkd_studio.doctype.gkd_project_boq.test_gkd_project_boq import (
	DESIGNER, PM, SUPERVISOR, make_employee, make_item, make_project, make_user,
)
from gkd.gkd_studio.execution import get_executable_lines

IGNORE_TEST_RECORD_DEPENDENCIES = ["Project", "Customer", "Company", "Employee", "Item", "Supplier", "User", "Activity Type", "Timesheet"]


class IntegrationTestExecution(IntegrationTestCase):
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
		project = frappe.get_doc("Project", cls.project)
		project.append("gkd_team", {"employee": make_employee("Test Manager", PM), "role_in_project": "Project Manager"})
		project.save(ignore_permissions=True)

	def setUp(self):
		self.boq = approved_boq(self)

	def tearDown(self):
		frappe.set_user("Administrator")

	def line(self, index):
		return self.boq.items[index].name

	def reload_row(self, index):
		return frappe.get_doc("GKD Project BOQ", self.boq.name).items[index]

	def test_supervisor_sees_only_lines_of_a_signed_boq(self):
		frappe.set_user(SUPERVISOR)
		lines = [row for row in get_executable_lines(self.project) if row["boq"] == self.boq.name]
		self.assertEqual(len(lines), 3)
		self.assertEqual((lines[0]["approved_qty"], lines[0]["executed_qty"], lines[0]["remaining_qty"]), (110, 0, 110))

	def test_submit_adds_the_quantity_and_cancel_takes_it_back(self):
		frappe.set_user(SUPERVISOR)
		report = file_report(self, add_days(today(), -10), [(0, 40)])
		report.submit()
		row = self.reload_row(0)
		self.assertEqual((row.executed_qty, round(row.execution_pct, 1), row.actual_qty), (40, 36.4, 0))
		self.assertEqual(report.entries[0].boq_line, "Living · Teak Veneer Panelling")
		self.assertEqual(report.entries[0].boq, self.boq.name)

		frappe.set_user("Administrator")
		report.cancel()
		self.assertEqual(self.reload_row(0).executed_qty, 0)

	def test_work_in_progress_shows_no_variance(self):
		frappe.set_user(SUPERVISOR)
		file_report(self, add_days(today(), -11), [(0, 40)]).submit()
		self.assertEqual(self.reload_row(0).variance_pct, 10, "still the site-measured gap, not -60%")

	def test_overrun_moves_the_variance_and_alerts_the_pm(self):
		frappe.set_user(SUPERVISOR)
		report = file_report(self, add_days(today(), -12), [(1, 43)])
		report.submit()
		row = self.reload_row(1)
		self.assertAlmostEqual(row.variance_pct, 7.5, msg="43 executed against 40 in the BOQ")
		self.assertTrue(frappe.db.exists(
			"Notification Log", {"for_user": PM, "document_name": self.boq.name, "document_type": "GKD Project BOQ"}
		))

	def test_finishing_a_line_sets_the_actual_quantity(self):
		frappe.set_user(SUPERVISOR)
		report = file_report(self, add_days(today(), -13), [(1, 38, True)])
		report.submit()
		row = self.reload_row(1)
		self.assertEqual((row.executed_qty, row.actual_qty), (38, 38))
		self.assertAlmostEqual(row.variance_pct, -5)

		frappe.set_user("Administrator")
		report.cancel()
		self.assertEqual(self.reload_row(1).actual_qty, 0, "cancelling reopens the line")

	def test_entry_rules(self):
		frappe.set_user(SUPERVISOR)
		day = add_days(today(), -14)
		with self.assertRaises(frappe.ValidationError):
			file_report(self, day, [(0, 0)])
		with self.assertRaises(frappe.ValidationError):
			file_report(self, day, [(0, 5), (0, 6)])
		with self.assertRaises(frappe.ValidationError):
			file_report(self, day, [("missing", 5)])

		other = frappe.get_doc({"doctype": "Project", "project_name": "GKD Test Other Site", "company": frappe.db.get_value("Project", self.project, "company")}).insert(ignore_permissions=True).name
		report = file_report(self, day, [(0, 5)], project=None, insert=False)
		report.entries[0].project = other
		self.assertRaises(frappe.ValidationError, report.insert)

	def test_a_boq_not_yet_approved_takes_no_work(self):
		draft_boq = approved_boq(self, stop_before_approval=True)
		frappe.set_user(SUPERVISOR)
		report = file_report(self, add_days(today(), -15), [(0, 5)], insert=False)
		report.entries[0].boq_item = draft_boq.items[0].name
		self.assertRaises(frappe.ValidationError, report.insert)


def file_report(test, day, lines, project=None, insert=True):
	"""lines: (BOQ row index or a literal row ID, quantity, finished?)"""
	entries = []
	for line in lines:
		index, qty, *finished = line
		row = test.boq.items[index].name if isinstance(index, int) else index
		entries.append({
			"project": project or test.project, "activity_type": "Site Supervision", "hours": 2,
			"work_done": "Tiling", "boq_item": row, "qty_done": qty, "item_finished": int(bool(finished and finished[0])),
		})
	doc = frappe.get_doc({
		"doctype": "GKD Daily Progress Report", "employee": test.supervisor, "report_date": day,
		"check_in_time": "09:30:00", "entries": entries,
	})
	return doc.insert() if insert else doc
