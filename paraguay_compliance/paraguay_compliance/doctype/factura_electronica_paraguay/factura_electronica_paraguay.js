frappe.ui.form.on("Factura Electronica Paraguay", {
	onload(frm) {
		if (!frm.doc.naming_series_doctype) {
			frm.set_value("naming_series_doctype", "Sales Invoice");
		}
	},

	refresh(frm) {
		frm.add_custom_button("FacturaSend", () => {
			frappe.confirm(
				__("This will replace all current mapping rows with the FacturaSend starter template. Continue?"),
				() => {
					apply_facturasend_template(frm);
				}
			);
		});

		frm.add_custom_button(__("Preview JSON"), () => {
			run_test_payload(frm);
		});

		if (!frm.doc.naming_series_options && frm.doc.naming_series_doctype) {
			load_core_naming_series(frm);
		}
	},

	generate_test_payload(frm) {
		run_test_payload(frm);
	},

	pull_naming_series(frm) {
		load_core_naming_series(frm, true);
	},
});

function run_test_payload(frm) {
	if (!frm.doc.sales_invoice_for_test) {
		frappe.msgprint(__("Select a Sales Invoice in the Testing tab first."));
		return;
	}

	frappe.call({
		method: "paraguay_compliance.paraguay_compliance.doctype.factura_electronica_paraguay.factura_electronica_paraguay.generate_test_payload",
		args: {
			sales_invoice: frm.doc.sales_invoice_for_test,
		},
		freeze: true,
		freeze_message: __("Generating test payload..."),
		callback: (r) => {
			if (!r.message) return;
			frm.set_value("test_payload_json", r.message.payload_json || "{}");
			if (r.message.errors && r.message.errors.length) {
				frappe.msgprint({
					title: __("Missing Required Mappings"),
					indicator: "orange",
					message: `<pre>${r.message.errors.join("\n")}</pre>`,
				});
			}
		},
	});
}

function load_core_naming_series(frm, notify = false) {
	frappe.call({
		method: "paraguay_compliance.paraguay_compliance.doctype.factura_electronica_paraguay.factura_electronica_paraguay.get_core_naming_series_options",
		args: {
			doctype: frm.doc.naming_series_doctype || "Sales Invoice",
		},
		callback: (r) => {
			const value = (r.message || "").trim();
			frm.set_value("naming_series_options", value);
			if (notify) {
				frappe.show_alert({
					message: __("Naming series loaded from Document Naming Settings"),
					indicator: "green",
				});
			}
		},
	});
}

function apply_facturasend_template(frm) {
	const rows = get_facturasend_mapping_rows();

	frm.clear_table("mapping_rows");
	rows.forEach((row) => {
		frm.add_child("mapping_rows", row);
	});

	frm.refresh_field("mapping_rows");
	frm.dirty();
	frappe.show_alert({
		message: __("FacturaSend mapping template loaded"),
		indicator: "green",
	});
}

function get_facturasend_mapping_rows() {
	return [
		{ target_path: "tipoDocumento", source_mode: "Static", static_value: "1", target_data_type: "Int", required: 1 },
		{ target_path: "establecimiento", source_mode: "Static", static_value: "1", target_data_type: "Int", required: 1 },
		{ target_path: "punto", source_mode: "Static", static_value: "001", target_data_type: "String", required: 1 },
		{ target_path: "numero", source_mode: "DocField", source_doctype: "Sales Invoice", source_fieldname: "name", target_data_type: "String", required: 1 },
		{ target_path: "descripcion", source_mode: "DocField", source_doctype: "Sales Invoice", source_fieldname: "remarks", target_data_type: "String" },
		{ target_path: "observacion", source_mode: "DocField", source_doctype: "Sales Invoice", source_fieldname: "remarks", target_data_type: "String" },
		{ target_path: "fecha", source_mode: "DocField", source_doctype: "Sales Invoice", source_fieldname: "posting_date", target_data_type: "Date", transformer: "Date ISO", required: 1 },
		{ target_path: "tipoEmision", source_mode: "Static", static_value: "1", target_data_type: "Int", required: 1 },
		{ target_path: "tipoTransaccion", source_mode: "Static", static_value: "1", target_data_type: "Int", required: 1 },
		{ target_path: "tipoImpuesto", source_mode: "Static", static_value: "1", target_data_type: "Int", required: 1 },
		{ target_path: "moneda", source_mode: "DocField", source_doctype: "Sales Invoice", source_fieldname: "currency", target_data_type: "String", required: 1 },

		{ target_path: "cliente.contribuyente", source_mode: "Static", static_value: "1", target_data_type: "Check", required: 1 },
		{ target_path: "cliente.ruc", source_mode: "Expression", expression: "customer.tax_id", target_data_type: "String", required: 1 },
		{ target_path: "cliente.razonSocial", source_mode: "DocField", source_doctype: "Sales Invoice", source_fieldname: "customer_name", target_data_type: "String", required: 1 },
		{ target_path: "cliente.nombreFantasia", source_mode: "Expression", expression: "customer.customer_name", target_data_type: "String" },
		{ target_path: "cliente.tipoOperacion", source_mode: "Static", static_value: "1", target_data_type: "Int" },
		{ target_path: "cliente.direccion", source_mode: "Expression", expression: "billing_address.address_line1", target_data_type: "String" },
		{ target_path: "cliente.numeroCasa", source_mode: "Expression", expression: "billing_address.address_line2", target_data_type: "String" },
		{ target_path: "cliente.departamento", source_mode: "Expression", expression: "billing_address.pyg_departamento_code", target_data_type: "Int" },
		{ target_path: "cliente.departamentoDescripcion", source_mode: "Expression", expression: "billing_address.pyg_departamento", target_data_type: "String" },
		{ target_path: "cliente.distrito", source_mode: "Expression", expression: "billing_address.pyg_distrito_code", target_data_type: "Int" },
		{ target_path: "cliente.distritoDescripcion", source_mode: "Expression", expression: "billing_address.pyg_distrito", target_data_type: "String" },
		{ target_path: "cliente.ciudad", source_mode: "Expression", expression: "billing_address.pyg_ciudad_code", target_data_type: "Int" },
		{ target_path: "cliente.ciudadDescripcion", source_mode: "Expression", expression: "billing_address.city", target_data_type: "String" },
		{ target_path: "cliente.pais", source_mode: "Expression", expression: "billing_address.country_code", target_data_type: "String", default_value: "PRY" },
		{ target_path: "cliente.paisDescripcion", source_mode: "Expression", expression: "billing_address.country", target_data_type: "String", default_value: "Paraguay" },
		{ target_path: "cliente.tipoContribuyente", source_mode: "Expression", expression: "customer.pyg_tipo_contribuyente", target_data_type: "Int" },
		{ target_path: "cliente.documentoTipo", source_mode: "Expression", expression: "customer.pyg_documento_tipo", target_data_type: "Int" },
		{ target_path: "cliente.documentoNumero", source_mode: "Expression", expression: "customer.pyg_documento_numero", target_data_type: "String" },
		{ target_path: "cliente.telefono", source_mode: "Expression", expression: "customer.phone", target_data_type: "String" },
		{ target_path: "cliente.celular", source_mode: "Expression", expression: "customer.mobile_no", target_data_type: "String" },
		{ target_path: "cliente.email", source_mode: "Expression", expression: "customer.email_id", target_data_type: "String" },
		{ target_path: "cliente.codigo", source_mode: "DocField", source_doctype: "Sales Invoice", source_fieldname: "customer", target_data_type: "String" },

		{ target_path: "usuario.documentoTipo", source_mode: "Expression", expression: "sales_person.pyg_documento_tipo", target_data_type: "Int" },
		{ target_path: "usuario.documentoNumero", source_mode: "Expression", expression: "sales_person.pyg_documento_numero", target_data_type: "String" },
		{ target_path: "usuario.nombre", source_mode: "Expression", expression: "sales_person.full_name", target_data_type: "String" },
		{ target_path: "usuario.cargo", source_mode: "Expression", expression: "sales_person.designation", target_data_type: "String" },

		{ target_path: "factura.presencia", source_mode: "Static", static_value: "1", target_data_type: "Int" },

		{ target_path: "condicion.tipo", source_mode: "Expression", expression: "invoice_condition_type", target_data_type: "Int", default_value: "1" },
		{ target_path: "condicion.credito.tipo", source_mode: "Expression", expression: "credit_info.tipo", target_data_type: "Int" },
		{ target_path: "condicion.credito.plazo", source_mode: "Expression", expression: "credit_info.plazo", target_data_type: "String" },
		{ target_path: "condicion.credito.cuotas", source_mode: "Expression", expression: "credit_info.cuotas", target_data_type: "Int" },
		{ target_path: "condicion.credito.montoEntrega", source_mode: "Expression", expression: "credit_info.monto_entrega", target_data_type: "Currency" },

		{ is_loop: 1, loop_doctype: "Sales Invoice Payment", loop_table_fieldname: "payments", loop_alias: "payment", loop_target_path: "condicion.entregas[]", target_path: "condicion.entregas[]", source_mode: "Static", static_value: "[]", target_data_type: "JSON" },
		{ target_path: "condicion.entregas[].tipo", source_mode: "Expression", expression: "payment.tipo_pago_facturasend", target_data_type: "Int" },
		{ target_path: "condicion.entregas[].monto", source_mode: "Expression", expression: "payment.amount", target_data_type: "Currency" },
		{ target_path: "condicion.entregas[].moneda", source_mode: "DocField", source_doctype: "Sales Invoice", source_fieldname: "currency", target_data_type: "String" },
		{ target_path: "condicion.entregas[].monedaDescripcion", source_mode: "Expression", expression: "invoice_currency_description", target_data_type: "String" },
		{ target_path: "condicion.entregas[].cambio", source_mode: "DocField", source_doctype: "Sales Invoice", source_fieldname: "conversion_rate", target_data_type: "Float" },
		{ target_path: "condicion.entregas[].infoTarjeta.numero", source_mode: "Expression", expression: "payment.pyg_card_last_digits", target_data_type: "Int" },
		{ target_path: "condicion.entregas[].infoTarjeta.tipo", source_mode: "Expression", expression: "payment.pyg_card_type_code", target_data_type: "Int" },
		{ target_path: "condicion.entregas[].infoTarjeta.tipoDescripcion", source_mode: "Expression", expression: "payment.pyg_card_type", target_data_type: "String" },
		{ target_path: "condicion.entregas[].infoTarjeta.titular", source_mode: "Expression", expression: "payment.pyg_card_holder", target_data_type: "String" },
		{ target_path: "condicion.entregas[].infoTarjeta.ruc", source_mode: "Expression", expression: "payment.pyg_card_holder_ruc", target_data_type: "String" },
		{ target_path: "condicion.entregas[].infoTarjeta.razonSocial", source_mode: "Expression", expression: "payment.pyg_card_holder_name", target_data_type: "String" },
		{ target_path: "condicion.entregas[].infoTarjeta.medioPago", source_mode: "Expression", expression: "payment.pyg_card_payment_media", target_data_type: "Int" },
		{ target_path: "condicion.entregas[].infoTarjeta.codigoAutorizacion", source_mode: "Expression", expression: "payment.reference_no", target_data_type: "String" },
		{ target_path: "condicion.entregas[].infoCheque.numeroCheque", source_mode: "Expression", expression: "payment.reference_no", target_data_type: "String" },
		{ target_path: "condicion.entregas[].infoCheque.banco", source_mode: "Expression", expression: "payment.mode_of_payment", target_data_type: "String" },

		{ is_loop: 1, loop_doctype: "Payment Schedule", loop_table_fieldname: "payment_schedule", loop_alias: "cuota", loop_target_path: "condicion.credito.infoCuotas[]", target_path: "condicion.credito.infoCuotas[]", source_mode: "Static", static_value: "[]", target_data_type: "JSON" },
		{ target_path: "condicion.credito.infoCuotas[].moneda", source_mode: "DocField", source_doctype: "Sales Invoice", source_fieldname: "currency", target_data_type: "String" },
		{ target_path: "condicion.credito.infoCuotas[].monto", source_mode: "Expression", expression: "cuota.payment_amount", target_data_type: "Currency" },
		{ target_path: "condicion.credito.infoCuotas[].vencimiento", source_mode: "Expression", expression: "cuota.due_date", target_data_type: "Date" },

		{ is_loop: 1, loop_doctype: "Sales Invoice Item", loop_table_fieldname: "items", loop_alias: "item", loop_target_path: "items[]", target_path: "items[]", source_mode: "Static", static_value: "[]", target_data_type: "JSON", required: 1 },
		{ target_path: "items[].codigo", source_mode: "Expression", expression: "item.item_code", target_data_type: "String", required: 1 },
		{ target_path: "items[].descripcion", source_mode: "Expression", expression: "item.description", target_data_type: "String", required: 1 },
		{ target_path: "items[].observacion", source_mode: "Expression", expression: "item.pyg_observacion", target_data_type: "String" },
		{ target_path: "items[].ncm", source_mode: "Expression", expression: "item.pyg_ncm", target_data_type: "String" },
		{ target_path: "items[].unidadMedida", source_mode: "Expression", expression: "item.pyg_unidad_medida_code", target_data_type: "Int" },
		{ target_path: "items[].cantidad", source_mode: "Expression", expression: "item.qty", target_data_type: "Float", required: 1 },
		{ target_path: "items[].precioUnitario", source_mode: "Expression", expression: "item.rate", target_data_type: "Currency", required: 1 },
		{ target_path: "items[].cambio", source_mode: "DocField", source_doctype: "Sales Invoice", source_fieldname: "conversion_rate", target_data_type: "Float" },
		{ target_path: "items[].ivaTipo", source_mode: "Expression", expression: "item.pyg_iva_tipo", target_data_type: "Int" },
		{ target_path: "items[].ivaBase", source_mode: "Expression", expression: "item.pyg_iva_base", target_data_type: "Int", default_value: "100" },
		{ target_path: "items[].iva", source_mode: "Expression", expression: "item.pyg_iva", target_data_type: "Int" },
		{ target_path: "items[].lote", source_mode: "Expression", expression: "item.batch_no", target_data_type: "String" },
		{ target_path: "items[].vencimiento", source_mode: "Expression", expression: "item.pyg_batch_expiry", target_data_type: "Date" },
		{ target_path: "items[].numeroSerie", source_mode: "Expression", expression: "item.serial_no", target_data_type: "String" },
		{ target_path: "items[].numeroPedido", source_mode: "Expression", expression: "item.sales_order", target_data_type: "String" },
		{ target_path: "items[].numeroSeguimiento", source_mode: "Expression", expression: "item.delivery_note", target_data_type: "String" }
	];
}
