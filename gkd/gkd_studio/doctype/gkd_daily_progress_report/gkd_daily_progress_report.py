# Copyright (c) 2026, raaj@akhilaminc.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.model.document import Document
from frappe.utils import add_to_date, flt, get_datetime, now_datetime

from gkd.gkd_studio.execution import post_quantities, validate_entries

# Roles that may file or correct a report on behalf of someone else.
MANAGER_ROLES = {"GKD Project Manager", "GKD Principal Designer", "System Manager"}


class GKDDailyProgressReport(Document):
	def validate(self):
		self.validate_reporter()
		self.total_hours = sum(flt(row.hours) for row in self.entries)
		self.has_blockers = int(any(row.has_blocker for row in self.entries))
		self.validate_one_report_per_day()
		validate_entries(self)

	def before_submit(self):
		# A draft may hold only the check-in. The day's work must be in before it is submitted.
		if not self.entries:
			frappe.throw(_("Add the work done today before you submit the report."), title=_("No Work Logged"))

	def validate_reporter(self):
		"""Staff file their own report. The hours become their timesheet, so no one may file for someone else."""
		if MANAGER_ROLES.intersection(frappe.get_roles()):
			return
		if frappe.db.get_value("Employee", self.employee, "user_id") != frappe.session.user:
			frappe.throw(
				_("You can file a progress report for yourself only."), frappe.PermissionError,
				title=_("Not Your Report"),
			)

	def on_submit(self):
		self.db_set("timesheet", self.make_timesheet())
		self.update_projects()
		post_quantities(self, 1)
		self.notify_blockers()

	def on_cancel(self):
		post_quantities(self, -1)
		if self.timesheet and frappe.db.get_value("Timesheet", self.timesheet, "docstatus") == 1:
			timesheet = frappe.get_doc("Timesheet", self.timesheet)
			timesheet.flags.ignore_permissions = True
			timesheet.cancel()

	def validate_one_report_per_day(self):
		duplicate = frappe.db.exists(
			"GKD Daily Progress Report",
			{"employee": self.employee, "report_date": self.report_date, "docstatus": 1, "name": ["!=", self.name]},
		)
		if duplicate:
			frappe.throw(
				_("{0} already filed {1} for {2}. Amend that report instead.").format(
					self.employee_name, frappe.bold(duplicate), frappe.format(self.report_date, "Date")
				),
				title=_("Report Already Filed"),
			)

	def make_timesheet(self) -> str:
		"""Log the reported hours as one timesheet, so the manager dashboard and hours report see them."""
		start = get_datetime(f"{self.report_date} {self.check_in_time}")
		logs = []
		for row in self.entries:
			end = add_to_date(start, hours=flt(row.hours))
			logs.append({
				"activity_type": row.activity_type, "project": row.project, "hours": row.hours,
				"from_time": start, "to_time": end, "description": row.work_done,
			})
			start = end
		timesheet = frappe.get_doc({
			"doctype": "Timesheet", "company": self.company, "employee": self.employee, "time_logs": logs,
			"note": _("From Daily Progress Report {0}").format(self.name),
		})
		# The timesheet is a by-product of a report the user was allowed to submit.
		timesheet.flags.ignore_permissions = True
		timesheet.insert()
		timesheet.submit()
		return timesheet.name

	def update_projects(self):
		latest = {}
		for row in self.entries:
			latest[row.project] = row.work_done
		for project, work_done in latest.items():
			frappe.db.set_value("Project", project, {
				"gkd_last_update": f"{self.employee_name}: {work_done}",
				"gkd_last_update_on": now_datetime(),
			})

	def notify_blockers(self):
		"""One alert per project to its project managers, listing every blocker reported there today."""
		for project, rows in self.blockers_by_project().items():
			recipients = project_manager_users(project)
			if not recipients:
				continue
			categories = ", ".join(dict.fromkeys(_(row.blocker_category) for row in rows))
			enqueue_create_notification(recipients, {
				"type": "Alert",
				"document_type": self.doctype,
				"document_name": self.name,
				"from_user": frappe.session.user,
				"subject": _("Blocker at {0}: {1}").format(
					frappe.db.get_value("Project", project, "project_name"), categories
				),
				"email_content": "<br>".join(frappe.utils.escape_html(row.comments or row.work_done) for row in rows),
			})

	def blockers_by_project(self) -> dict:
		grouped = {}
		for row in self.entries:
			if row.has_blocker:
				grouped.setdefault(row.project, []).append(row)
		return grouped


def project_manager_users(project: str) -> list[str]:
	"""Logins of the project managers in the project's team."""
	employees = frappe.get_all(
		"GKD Project Team",
		filters={"parent": project, "parenttype": "Project", "role_in_project": "Project Manager"},
		pluck="employee",
	)
	if not employees:
		return []
	return frappe.get_all("Employee", filters={"name": ["in", employees], "user_id": ["is", "set"]}, pluck="user_id")
