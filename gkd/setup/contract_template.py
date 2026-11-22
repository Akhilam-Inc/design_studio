"""The studio's standard interior works agreement.

ERPNext renders these terms in a sandbox with only the Contract's own fields, so the BOQ table and
the contract value come from the "GKD Contract" print format, not from here.
"""

import frappe

TEMPLATE = "GKD Interior Works Agreement"

MILESTONES = [
	"Booking advance on signing this agreement: 40%",
	"Completion of civil, electrical and false ceiling works: 30%",
	"Completion of carpentry, finishes and installation: 25%",
	"Final handover and snag closure: 5%",
]

TERMS = """
<h4>Interior Works Agreement</h4>
<p>This agreement is between <b>Gauri Khan Design Studio</b> ("the Studio") and
<b>{{ party_name }}</b> ("the Client").</p>

<p><b>1. Scope.</b> The Studio will carry out the interior works listed in Project BOQ
<b>{{ gkd_project_boq }}</b>. The BOQ was verified at site and approved by the Client. It is attached
as Annexure A. Work outside the BOQ is a variation and needs a written change order.</p>

<p><b>2. Period.</b> Work starts on {{ start_date }}{% if end_date %} and is planned to finish on
{{ end_date }}{% endif %}. Delays caused by site access, Client changes or Client-supplied material
extend this period.</p>

<p><b>3. Contract value.</b> The contract value is the total of Annexure A. Quantities are re-measured
at site. Final billing follows the executed quantity at the BOQ rate.</p>

<p><b>4. Payment milestones.</b></p>
<ol>
MILESTONE_ITEMS</ol>

<p><b>5. Contractors.</b> The Studio appoints contractors only for scope in the approved BOQ.</p>

<p><b>6. Warranty.</b> The Studio corrects defects in workmanship reported within 12 months of handover.</p>
"""


def create():
	terms = TERMS.replace("MILESTONE_ITEMS", "".join(f"<li>{m}</li>\n" for m in MILESTONES))
	doc = frappe.get_doc("Contract Template", TEMPLATE) if frappe.db.exists("Contract Template", TEMPLATE) else None
	if not doc:
		doc = frappe.new_doc("Contract Template")
		doc.title = TEMPLATE
	doc.contract_terms = terms
	doc.requires_fulfilment = 1
	doc.set("fulfilment_terms", [{"requirement": milestone} for milestone in MILESTONES])
	doc.save(ignore_permissions=True)
