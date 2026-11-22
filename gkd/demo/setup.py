"""Demo data for the Gauri Khan Design Studio presales demo. Safe to run again: it only adds what is missing.

Run with: bench --site SITE execute gkd.demo.setup.create
"""

import frappe

from gkd.demo import boqs, cad, catalog, contracts, dprs, handover, people, projects
from gkd.setup import masters


def create():
	masters.create()
	catalog.create()
	cad.create_mappings()
	people.create()
	projects.create()
	dprs.create()
	boqs.create()
	contracts.create()
	handover.create()
	frappe.clear_cache()
