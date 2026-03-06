import frappe


def execute():
	doctype = "Paraguay Compliance Settings"
	if not frappe.db.exists("DocType", doctype):
		return

	_single_field_map = {
		"tipo_contribuyente": "taxpayer_type",
		"domicilio_emision": "issuance_address",
		"regimen_facturacion": "billing_regime",
		"api_ambiente": "api_environment",
		"umbral_retencion": "withholding_threshold",
	}

	for old_field, new_field in _single_field_map.items():
		old_value = frappe.db.get_single_value(doctype, old_field)
		new_value = frappe.db.get_single_value(doctype, new_field)
		if old_value and not new_value:
			frappe.db.set_single_value(doctype, new_field, old_value)

	# Preserve child rows linked from renamed table fields in single settings.
	frappe.db.sql(
		"""
		update `tabParaguay Timbrado`
		set parentfield='timbrado_entries'
		where parenttype='Paraguay Compliance Settings' and parentfield='timbrados'
		"""
	)
	frappe.db.sql(
		"""
		update `tabParaguay IVA Mapping`
		set parentfield='vat_mapping'
		where parenttype='Paraguay Compliance Settings' and parentfield='iva_mapping'
		"""
	)

	_copy_child_column("Paraguay Timbrado", "tipo_comprobante", "voucher_type")
	_copy_child_column("Paraguay Timbrado", "numero_timbrado", "timbrado_number")
	_copy_child_column("Paraguay Timbrado", "fecha_inicio_vigencia", "valid_from")
	_copy_child_column("Paraguay Timbrado", "fecha_vencimiento", "valid_until")
	_copy_child_column("Paraguay Timbrado", "establecimiento", "establishment")
	_copy_child_column("Paraguay Timbrado", "punto_expedicion", "expedition_point")
	_copy_child_column("Paraguay Timbrado", "proximo_numero", "next_number")
	_copy_child_column("Paraguay Timbrado", "activo", "is_active")

	_copy_child_column("Paraguay IVA Mapping", "gobierno_rate", "government_rate")
	_copy_child_column("Paraguay IVA Mapping", "descripcion", "description")


def _copy_child_column(doctype: str, old_field: str, new_field: str):
	if not frappe.db.has_column(doctype, old_field):
		return
	if not frappe.db.has_column(doctype, new_field):
		return

	frappe.db.sql(
		f"""
		update `tab{doctype}`
		set `{new_field}`=`{old_field}`
		where `{old_field}` is not null
		"""
	)
