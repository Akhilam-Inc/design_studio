"""Supervisors report from site through DPRs. Each submitted DPR makes their timesheet, as in real use."""

import frappe
from frappe.utils import add_days, getdate

from gkd.demo.people import acting_as, employee
from gkd.demo.projects import (
	DAY_PLANS, SAFFRON, SINGHANIA, SITE_REPORTERS, TIMESHEET_START, blocks_for, project_id,
)

# Site progress on supervision days: (progress on the first day, points gained per working day).
PROGRESS = {SINGHANIA: (18, 0.8)}

# (supervisor, date, project): (blocker category, what is blocked)
BLOCKERS = {
	("sup_vikram", "2026-11-12", SINGHANIA): ("Material Delay",
		"Statuario lot rejected at site for heavy veining. Replacement lot expected on 19 Nov. Living floor on hold."),
	("sup_suresh", "2026-11-17", SAFFRON): ("Client Decision",
		"Client has not confirmed the bar counter finish. Carpentry shop drawings are on hold."),
}


def create():
	for key in SITE_REPORTERS:
		create_reports(key)


def create_reports(key):
	emp, plan = employee(key), DAY_PLANS[key]
	day, today, index = getdate(TIMESHEET_START), getdate(), 0
	while day <= today:
		if day.weekday() != 6:
			if not frappe.db.exists("GKD Daily Progress Report", {"employee": emp, "report_date": day, "docstatus": 1}):
				file_report(key, emp, day, blocks_for(plan[index % len(plan)], day, today), index)
			index += 1
		day = add_days(day, 1)


def file_report(key, emp, day, blocks, index):
	entries = [entry(key, day, index, *block) for block in blocks]
	mark_blocker(key, day, entries)
	with acting_as(key):
		report = frappe.get_doc({
			"doctype": "GKD Daily Progress Report",
			"employee": emp,
			"report_date": day,
			"check_in_time": "09:30:00",
			# Today's report is filed at lunch, before check-out.
			"check_out_time": None if day == getdate() else "18:00:00" if day.weekday() != 5 else "13:30:00",
			"entries": entries,
		})
		report.insert()
		report.submit()


def entry(key, day, index, project, activity, hours, note):
	row = {"project": project_id(project), "activity_type": activity, "hours": hours, "work_done": note}
	if activity == "Site Supervision" and project in PROGRESS:
		start, per_day = PROGRESS[project]
		row["progress_pct"] = round(start + per_day * index)
	return row


def mark_blocker(key, day, entries):
	"""A blocker belongs to one line of the report: the first one for its project."""
	for (who, date, project), (category, comments) in BLOCKERS.items():
		if (who, date) != (key, str(day)):
			continue
		row = next(row for row in entries if row["project"] == project_id(project))
		row.update({"has_blocker": 1, "blocker_category": category, "comments": comments})
