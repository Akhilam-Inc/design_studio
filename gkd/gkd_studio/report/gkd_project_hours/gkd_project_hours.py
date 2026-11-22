# Copyright (c) 2026, raaj@akhilaminc.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters: dict | None = None):
	report = ProjectHoursReport(frappe._dict(filters or {}))
	rows = report.get_rows()
	return report.get_columns(), rows, None, report.get_chart(rows), report.get_summary(rows)


class ProjectHoursReport:
	"""Hours logged on submitted timesheets, by project, employee and activity."""

	def __init__(self, filters):
		self.filters = filters

	def get_rows(self):
		totals = {}
		for log in self.get_time_logs():
			key = (log.project, log.employee, log.activity_type)
			row = totals.setdefault(key, frappe._dict(log, hours=0))
			row.hours += flt(log.hours)
		return sorted(totals.values(), key=lambda row: (row.project or "", row.employee or ""))

	def get_time_logs(self):
		# get_list applies the user's permissions on Timesheet. It cannot sum child fields, so we sum in get_rows.
		return frappe.get_list(
			"Timesheet",
			filters=self.get_filters(),
			fields=[
				"time_logs.project as project",
				"time_logs.project_name as project_name",
				"employee",
				"employee_name",
				"time_logs.activity_type as activity_type",
				"time_logs.hours as hours",
			],
		)

	def get_filters(self):
		filters = [["docstatus", "=", 1]]
		if self.filters.from_date:
			filters.append(["Timesheet Detail", "from_time", ">=", self.filters.from_date])
		if self.filters.to_date:
			filters.append(["Timesheet Detail", "from_time", "<", frappe.utils.add_days(self.filters.to_date, 1)])
		for field in ("project", "activity_type"):
			if self.filters.get(field):
				filters.append(["Timesheet Detail", field, "=", self.filters.get(field)])
		if self.filters.employee:
			filters.append(["employee", "=", self.filters.employee])
		return filters

	def get_columns(self):
		return [
			{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 160},
			{"label": _("Project Name"), "fieldname": "project_name", "fieldtype": "Data", "width": 200},
			{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 140},
			{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
			{"label": _("Activity Type"), "fieldname": "activity_type", "fieldtype": "Link", "options": "Activity Type",
				"width": 150},
			{"label": _("Hours"), "fieldname": "hours", "fieldtype": "Float", "precision": 2, "width": 100},
		]

	def get_chart(self, rows):
		hours_by_project = {}
		for row in rows:
			label = row.project_name or row.project or _("No Project")
			hours_by_project[label] = hours_by_project.get(label, 0) + flt(row.hours)
		return {
			"data": {
				"labels": list(hours_by_project),
				"datasets": [{"name": _("Hours"), "values": list(hours_by_project.values())}],
			},
			"type": "bar",
			"fieldtype": "Float",
		}

	def get_summary(self, rows):
		return [
			{"label": _("Total Hours"), "value": sum(flt(row.hours) for row in rows), "datatype": "Float",
				"indicator": "Blue"},
			{"label": _("Projects"), "value": len({row.project for row in rows if row.project}), "datatype": "Int"},
			{"label": _("People"), "value": len({row.employee for row in rows}), "datatype": "Int"},
		]
