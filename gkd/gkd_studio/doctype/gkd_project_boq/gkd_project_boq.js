// Copyright (c) 2026, raaj@akhilaminc.com and contributors
// For license information, please see license.txt

const BOQ_ACTIONS = "gkd.gkd_studio.boq_actions";
const CAD_IMPORT = "gkd.gkd_studio.cad_import.import_cad_export";
const CLIENT_PRINT_FORMAT = "GKD BOQ for Client";

frappe.ui.form.on("GKD Project BOQ", {
	async onload(frm) {
		frm.gkd_threshold =
			(await frappe.db.get_single_value("GKD Settings", "variance_threshold_pct")) || 5;
		gkd_boq.paint_variance(frm);
	},

	refresh(frm) {
		gkd_boq.add_buttons(frm);
		gkd_boq.paint_variance(frm);
	},

	items_remove(frm) {
		gkd_boq.calculate(frm);
	},
});

frappe.ui.form.on("GKD BOQ Item", {
	design_qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		// A new row starts from the designed quantity, as on the server.
		if (!row.boq_qty) frappe.model.set_value(cdt, cdn, "boq_qty", row.design_qty);
		gkd_boq.calculate(frm);
	},
	boq_qty: (frm) => gkd_boq.calculate(frm),
	site_verified_qty: (frm) => gkd_boq.calculate(frm),
	actual_qty: (frm) => gkd_boq.calculate(frm),
	rate: (frm) => gkd_boq.calculate(frm),
});

const gkd_boq = {
	add_buttons(frm) {
		if (frm.is_new()) return;
		const state = frm.doc.workflow_state;

		if (!state || state === "Draft") {
			frm.add_custom_button(__("Import from CAD"), () => gkd_boq.import_from_cad(frm));
		}
		if (["Site Verified", "Pending Customer Approval", "Approved"].includes(state)) {
			frm.add_custom_button(__("Print for Client"), () => gkd_boq.print_for_client(frm));
		}
		if (state === "Approved") {
			frm.add_custom_button(
				__("Contract"),
				() => frappe.model.open_mapped_doc({ method: `${BOQ_ACTIONS}.make_contract`, frm }),
				__("Create")
			);
			frm.add_custom_button(
				__("Contractor Orders"),
				() => gkd_boq.create_contractor_orders(frm),
				__("Create")
			);
		}
	},

	import_from_cad(frm) {
		new frappe.ui.FileUploader({
			doctype: frm.doctype,
			docname: frm.doc.name,
			restrictions: { allowed_file_types: [".csv"] },
			make_attachments_public: false,
			on_success: (file) =>
				frappe
					.xcall(CAD_IMPORT, { boq: frm.doc.name, file_url: file.file_url })
					.then((result) => {
						frm.reload_doc();
						gkd_boq.show_import_result(result);
					}),
		});
	},

	show_import_result(result) {
		const summary = __(
			"{0} CAD objects became {1} BOQ lines: {2} added, {3} updated, {4} removed.",
			[result.objects, result.lines, result.added, result.updated, result.removed]
		);
		let unmapped = "";
		if (result.unmapped.length) {
			const rows = result.unmapped
				.map((u) => {
					const add = `<a href="#" class="gkd-add-mapping" data-layer="${frappe.utils.escape_html(u.layer)}"
						data-block="${frappe.utils.escape_html(u.block)}">${__("Add Mapping")}</a>`;
					return `<tr><td>${frappe.utils.escape_html(u.layer)}</td><td>${frappe.utils.escape_html(u.block)}</td>
						<td>${frappe.utils.escape_html(u.description)}</td><td>${u.objects}</td><td>${add}</td></tr>`;
				})
				.join("");
			unmapped = `<p class="text-warning">${__("These objects have no mapping, so they are not in the BOQ:")}</p>
				<table class="table table-bordered"><thead><tr><th>${__("Layer")}</th><th>${__("Block")}</th>
				<th>${__("Description")}</th><th>${__("Objects")}</th><th></th></tr></thead><tbody>${rows}</tbody></table>`;
		}
		const dialog = frappe.msgprint({
			title: __("CAD Import"),
			message: `<p>${summary}</p>${unmapped}`,
			indicator: result.unmapped.length ? "orange" : "green",
			wide: true,
		});
		dialog.$wrapper.on("click", ".gkd-add-mapping", (event) => {
			event.preventDefault();
			const { layer, block } = event.currentTarget.dataset;
			dialog.hide();
			frappe.new_doc("GKD CAD Mapping", { cad_layer: layer, cad_block: block });
		});
	},

	print_for_client(frm) {
		const url = frappe.urllib.get_full_url(
			`/printview?doctype=${encodeURIComponent(frm.doctype)}` +
				`&name=${encodeURIComponent(frm.doc.name)}` +
				`&format=${encodeURIComponent(CLIENT_PRINT_FORMAT)}&no_letterhead=0`
		);
		window.open(url, "_blank");
	},

	create_contractor_orders(frm) {
		const contractors = new Set(frm.doc.items.map((row) => row.contractor).filter(Boolean));
		frappe.confirm(
			__(
				"Create {0} draft contractor orders from this BOQ and mark it Handed Over?",
				[contractors.size]
			),
			() =>
				frappe
					.xcall(`${BOQ_ACTIONS}.create_contractor_orders`, { boq: frm.doc.name })
					.then((orders) => {
						const links = orders
							.map((name) => frappe.utils.get_form_link("Purchase Order", name, true))
							.join(", ");
						frappe.msgprint({
							title: __("Contractor Orders Created"),
							message: __("Draft orders: {0}. Review and submit them.", [links]),
							indicator: "green",
						});
						frm.reload_doc();
					})
		);
	},

	calculate(frm) {
		let total_boq = 0;
		let total_approved = 0;
		let variance_value = 0;
		for (const row of frm.doc.items || []) {
			const approved = flt(row.site_verified_qty) || flt(row.boq_qty);
			const latest = flt(row.actual_qty) || approved;
			row.amount = flt(row.boq_qty) * flt(row.rate);
			row.approved_qty = approved;
			row.approved_amount = approved * flt(row.rate);
			row.variance_pct = row.boq_qty ? ((latest - row.boq_qty) / row.boq_qty) * 100 : 0;
			total_boq += row.amount;
			total_approved += row.approved_amount;
			variance_value += (latest - flt(row.boq_qty)) * flt(row.rate);
		}
		frm.doc.total_boq_amount = total_boq;
		frm.doc.total_site_amount = total_approved;
		frm.doc.variance_value = variance_value;
		frm.refresh_fields(["items", "total_boq_amount", "total_site_amount", "variance_value"]);
		gkd_boq.paint_variance(frm);
	},

	paint_variance(frm) {
		// Runs after the grid renders, because Percent fields take no custom formatter.
		setTimeout(() => {
			const threshold = flt(frm.gkd_threshold || 5);
			let flagged = 0;
			for (const grid_row of frm.fields_dict.items?.grid?.grid_rows || []) {
				const level = gkd_boq.variance_level(grid_row.doc.variance_pct, threshold);
				if (level === "over") flagged += 1;
				const cell = grid_row.wrapper.find('[data-fieldname="variance_pct"]');
				cell.css({
					color: { over: "var(--red-600)", near: "var(--orange-600)" }[level] || "",
					"font-weight": level ? "600" : "",
				});
			}
			gkd_boq.show_summary(frm, flagged, threshold);
		}, 200);
	},

	variance_level(value, threshold) {
		const size = Math.abs(flt(value));
		if (size > threshold) return "over";
		if (size > threshold / 2) return "near";
		return "";
	},

	show_summary(frm, flagged, threshold) {
		frm.set_intro("");
		if (!flagged) return;
		frm.set_intro(
			__("{0} rows differ from the BOQ quantity by more than {1}%. Value at stake: {2}.", [
				flagged,
				threshold,
				format_currency(frm.doc.variance_value),
			]),
			"orange"
		);
	},
};
