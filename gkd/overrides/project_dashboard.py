"""Show a project's BOQs in its Connections tab."""

from frappe import _


def get_data(data):
	data["transactions"].append({"label": _("Design Studio"), "items": ["GKD Project BOQ"]})
	return data
