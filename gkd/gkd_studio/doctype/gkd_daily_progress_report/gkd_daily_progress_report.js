// Copyright (c) 2026, raaj@akhilaminc.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("GKD Daily Progress Report", {
	async onload(frm) {
		if (!frm.is_new()) return;
		if (!frm.doc.check_in_time) frm.set_value("check_in_time", frappe.datetime.now_time());
		if (!frm.doc.employee) {
			const employee = await frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name");
			if (employee?.message?.name) frm.set_value("employee", employee.message.name);
		}
	},

	refresh(frm) {
		if (frm.doc.timesheet) {
			frm.add_custom_button(__("Timesheet"), () => frappe.set_route("Form", "Timesheet", frm.doc.timesheet), __("View"));
		}
	},
});
