frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;
		if (!frm.doc.pyg_cdc) return;

		frm.add_custom_button(__("Check DE Status"), () => {
			frappe.call({
				method: "paraguay_compliance.paraguay.einvoice.sifen.check_sales_invoice_status",
				args: { sales_invoice: frm.doc.name },
				freeze: true,
				freeze_message: __("Checking status from FacturaSend..."),
				callback: (r) => {
					if (!r.message) return;
					frm.reload_doc();
					if (r.message.is_approved) {
						frappe.show_alert({
							message: __("Government status indicates approval."),
							indicator: "green",
						});
					} else {
						frappe.msgprint({
							title: __("Current DE Status"),
							indicator: "orange",
							message: __("Status returned: {0}", [r.message.situacion || "N/A"]),
						});
					}
				},
			});
		});
	},
});
