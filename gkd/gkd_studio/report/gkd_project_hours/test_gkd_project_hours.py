import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime, today

from gkd.gkd_studio.doctype.gkd_project_boq.test_gkd_project_boq import make_employee, make_project, make_user
from gkd.gkd_studio.report.gkd_project_hours.gkd_project_hours import execute
from gkd.setup.masters import COMPANY

PM = "gkd.test.pm@example.com"


class TestGKDProjectHours(IntegrationTestCase):
	def test_hours_are_summed_by_project_employee_and_activity(self):
		make_user(PM, "GKD Project Manager")
		employee = make_employee("Test Designer", None)
		project = make_project(None)
		make_timesheet(employee, project, [("Site Visit", 2), ("Site Visit", 1.5), ("Design Work", 3)])

		frappe.set_user(PM)
		_columns, rows, _msg, chart, summary = execute({"from_date": today(), "to_date": today(), "project": project})
		frappe.set_user("Administrator")

		hours = {row.activity_type: row.hours for row in rows}
		self.assertEqual(hours, {"Site Visit": 3.5, "Design Work": 3})
		self.assertEqual(summary[0]["value"], 6.5)
		self.assertEqual(chart["data"]["datasets"][0]["values"], [6.5])


def make_timesheet(employee, project, logs):
	start = now_datetime().replace(hour=9, minute=0, second=0, microsecond=0)
	time_logs = []
	for activity, hours in logs:
		time_logs.append({
			"activity_type": activity, "project": project, "hours": hours,
			"from_time": start, "to_time": add_to_date(start, hours=hours),
		})
		start = add_to_date(start, hours=hours)
	ts = frappe.get_doc({"doctype": "Timesheet", "company": COMPANY, "employee": employee, "time_logs": time_logs})
	ts.insert(ignore_permissions=True)
	ts.submit()
	return ts
