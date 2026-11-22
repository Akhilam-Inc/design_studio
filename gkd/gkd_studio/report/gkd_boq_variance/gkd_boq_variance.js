// Copyright (c) 2026, raaj@akhilaminc.com and contributors
// For license information, please see license.txt

frappe.query_reports["GKD BOQ Variance"] = {
	filters: [
		{ fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project" },
		{
			fieldname: "workflow_state",
			label: __("Stage"),
			fieldtype: "Select",
			options: [
				"",
				"Draft",
				"Pending Site Verification",
				"Site Verified",
				"Pending Customer Approval",
				"Approved",
				"Handed Over",
			],
		},
		{ fieldname: "trade", label: __("Trade"), fieldtype: "Link", options: "GKD Trade" },
		{ fieldname: "only_above_threshold", label: __("Only Over Threshold"), fieldtype: "Check" },
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data?.status) {
			const color = data.status === __("Over Threshold") ? "red" : "green";
			value = `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
};
