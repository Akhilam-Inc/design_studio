# Copyright (c) 2026, raaj@akhilaminc.com and Contributors
# See license.txt

# Records persist across the tests of a class, so each test files its report on a day of its own.

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from gkd.gkd_studio.doctype.gkd_project_boq.test_gkd_project_boq import (
	PM, SUPERVISOR, make_employee, make_project, make_user,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["Project", "Customer", "Company", "Employee", "User", "Activity Type", "Timesheet"]


class IntegrationTestGKDDailyProgressReport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_user(SUPERVISOR, "GKD Site Supervisor")
		make_user(PM, "GKD Project Manager")
		cls.supervisor = make_employee("Test Supervisor", SUPERVISOR)
		cls.project = make_project(cls.supervisor)
		project = frappe.get_doc("Project", cls.project)
		project.append("gkd_team", {"employee": make_employee("Test Manager", PM), "role_in_project": "Project Manager"})
		project.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_submit_logs_timesheet_and_updates_project(self):
		frappe.set_user(SUPERVISOR)
		report = make_report(self, [("Site Supervision", 5, "Gypsum framing in living room"), ("Site Visit", 2, "Survey")],
			day=today())
		report.submit()

		timesheet = frappe.get_doc("Timesheet", report.timesheet)
		self.assertEqual((timesheet.docstatus, timesheet.employee, timesheet.total_hours), (1, self.supervisor, 7))
		self.assertEqual(str(timesheet.time_logs[1].from_time), f"{today()} 14:30:00", "logs follow on from check-in")
		self.assertIn("Survey", frappe.db.get_value("Project", self.project, "gkd_last_update"))

	def test_blocker_alerts_the_project_manager(self):
		frappe.set_user(SUPERVISOR)
		report = make_report(self, [("Site Supervision", 4, "Flooring")], blocker=("Material Delay", "Marble lot rejected"),
			day=add_days(today(), -1))
		report.submit()
		self.assertTrue(report.has_blockers)
		self.assertTrue(frappe.db.exists("Notification Log", {"for_user": PM, "document_name": report.name}))

	def test_one_report_per_day_and_cancel_reverses_timesheet(self):
		frappe.set_user(SUPERVISOR)
		day = add_days(today(), -2)
		report = make_report(self, [("Site Supervision", 4, "Flooring")], day=day)
		report.submit()
		with self.assertRaises(frappe.ValidationError):
			make_report(self, [("Site Visit", 1, "Again")], day=day)

		frappe.set_user("Administrator")
		report.cancel()
		self.assertEqual(frappe.db.get_value("Timesheet", report.timesheet, "docstatus"), 2)


	def test_staff_file_only_their_own_report(self):
		other = make_employee("Other Supervisor", None)
		frappe.set_user(SUPERVISOR)
		report = frappe.get_doc({"doctype": "GKD Daily Progress Report", "employee": other,
			"report_date": add_days(today(), -3), "check_in_time": "09:30:00"})
		self.assertRaises(frappe.PermissionError, report.insert)

	def test_check_in_first_then_work_before_submit(self):
		frappe.set_user(SUPERVISOR)
		report = make_report(self, [], day=add_days(today(), -4))
		self.assertEqual(report.docstatus, 0, "a check-in alone can be saved")
		self.assertRaises(frappe.ValidationError, report.submit)


def make_report(test, rows, day, blocker=None):
	entries = [{"project": test.project, "activity_type": activity, "hours": hours, "work_done": note}
		for activity, hours, note in rows]
	if blocker and entries:
		entries[0].update({"has_blocker": 1, "blocker_category": blocker[0], "comments": blocker[1]})
	return frappe.get_doc({
		"doctype": "GKD Daily Progress Report",
		"employee": test.supervisor,
		"report_date": day,
		"check_in_time": "09:30:00",
		"entries": entries,
	}).insert()
