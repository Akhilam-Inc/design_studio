from frappe import _


def get_data():
	return {
		"fieldname": "gkd_project_boq",
		"transactions": [
			{"label": _("Client"), "items": ["Contract"]},
			{"label": _("Contractors"), "items": ["Purchase Order"]},
		],
	}
