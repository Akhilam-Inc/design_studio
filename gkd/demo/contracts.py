"""The signed interior works agreement for the approved Singhania BOQ."""

import frappe
from erpnext.crm.doctype.contract_template.contract_template import get_contract_template

from gkd.demo.people import acting_as
from gkd.demo.projects import SINGHANIA
from gkd.setup.contract_template import TEMPLATE


def create():
	boq = frappe.db.get_value("GKD Project BOQ", {"project_name": SINGHANIA, "workflow_state": "Approved"})
	if not boq or frappe.db.exists("Contract", {"gkd_project_boq": boq}):
		return
	with acting_as("pm_rohan"):
		contract = frappe.get_doc({
			"doctype": "Contract",
			"party_type": "Customer",
			"party_name": frappe.db.get_value("GKD Project BOQ", boq, "customer"),
			"start_date": "2026-11-09",
			"end_date": "2027-01-30",
			"contract_template": TEMPLATE,
			"gkd_project_boq": boq,
			"document_type": "Project",
			"document_name": frappe.db.get_value("GKD Project BOQ", boq, "project"),
			"is_signed": 1,
			"signee": "Aditya Singhania",
			"signed_on": "2026-11-05 18:30:00",
		})
		rendered = get_contract_template(TEMPLATE, contract.as_dict())
		contract.contract_terms = rendered["contract_terms"]
		contract.requires_fulfilment = 1
		contract.set("fulfilment_terms", [
			{"requirement": term.requirement, "fulfilled": int(term.idx == 1)}
			for term in rendered["contract_template"].fulfilment_terms
		])
		contract.insert()
		contract.submit()
