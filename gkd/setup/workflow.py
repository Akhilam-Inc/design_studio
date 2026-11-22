"""BOQ approval workflow and the assignment rule that sends BOQs to the site supervisor."""

import frappe

DOCTYPE = "GKD Project BOQ"
WORKFLOW = "GKD BOQ Approval"
ASSIGNMENT_RULE = "GKD BOQ to Site Supervisor"

PM = "GKD Project Manager"
DESIGNER = "GKD Designer"
SUPERVISOR = "GKD Site Supervisor"

# (state, docstatus, role allowed to edit, indicator style)
STATES = [
	("Draft", 0, DESIGNER, ""),
	("Draft", 0, PM, ""),
	("Pending Site Verification", 0, SUPERVISOR, "Warning"),
	("Site Verified", 0, PM, "Info"),
	("Pending Customer Approval", 0, PM, "Warning"),
	("Approved", 1, PM, "Success"),
	("Handed Over", 1, PM, "Primary"),
]

# (from state, action, to state, allowed role)
# The dual-approval gate is in GKDProjectBOQ.validate_approval_gates. A workflow condition would only
# hide the button, and the user would not know why.
TRANSITIONS = [
	("Draft", "Send for Site Verification", "Pending Site Verification", DESIGNER),
	("Draft", "Send for Site Verification", "Pending Site Verification", PM),
	("Pending Site Verification", "Verify", "Site Verified", SUPERVISOR),
	("Pending Site Verification", "Send Back", "Draft", SUPERVISOR),
	("Site Verified", "Send to Customer", "Pending Customer Approval", PM),
	("Site Verified", "Send Back", "Draft", PM),
	("Pending Customer Approval", "Approve", "Approved", PM),
	("Pending Customer Approval", "Send Back", "Draft", PM),
	("Approved", "Hand Over", "Handed Over", PM),
]


def create():
	ensure_masters()
	upsert_workflow()
	upsert_assignment_rule()


def ensure_masters():
	for state, _docstatus, _role, style in STATES:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": style}).insert(
				ignore_permissions=True
			)
	for action in {row[1] for row in TRANSITIONS}:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(
				ignore_permissions=True
			)


def upsert_workflow():
	wf = frappe.get_doc("Workflow", WORKFLOW) if frappe.db.exists("Workflow", WORKFLOW) else frappe.new_doc("Workflow")
	wf.update({
		"workflow_name": WORKFLOW,
		"document_type": DOCTYPE,
		"workflow_state_field": "workflow_state",
		"is_active": 1,
		"send_email_alert": 0,
	})
	wf.set("states", [
		{"state": state, "doc_status": str(docstatus), "allow_edit": role} for state, docstatus, role, _ in STATES
	])
	wf.set("transitions", [
		{"state": src, "action": action, "next_state": dst, "allowed": role, "allow_self_approval": 1}
		for src, action, dst, role in TRANSITIONS
	])
	wf.save(ignore_permissions=True)


def upsert_assignment_rule():
	name = ASSIGNMENT_RULE
	rule = frappe.get_doc("Assignment Rule", name) if frappe.db.exists("Assignment Rule", name) else None
	if not rule:
		rule = frappe.new_doc("Assignment Rule")
		rule.name = name
	rule.update({
		"document_type": DOCTYPE,
		"description": "BOQ is ready for a site visit. Verify the quantities at site.",
		"priority": 1,
		"rule": "Based on Field",
		"field": "site_supervisor_user",
		"assign_condition": 'workflow_state == "Pending Site Verification"',
		"unassign_condition": 'workflow_state == "Draft"',
		# Frappe reopens a closed ToDo on any save where this is false, so it must hold for every later state.
		"close_condition": 'workflow_state in ("Site Verified", "Pending Customer Approval", "Approved", "Handed Over")',
	})
	rule.set("assignment_days", [
		{"day": day} for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
	])
	rule.save(ignore_permissions=True)
