# Copyright (c) 2026, INDOPAR and contributors
# For license information, please see license.txt

import json
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, get_datetime


class FacturaElectronicaParaguay(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		check_status_url: DF.Data | None
		naming_series_doctype: DF.Link | None
		naming_series_options: DF.Text | None
		sales_invoice_for_test: DF.Link | None
		pull_naming_series: DF.Button | None
		start_date: DF.Date | None
		tenent_url: DF.Data | None
		test_mode: DF.Check
		test_payload_json: DF.Code | None
		timbrado: DF.Int
	# end: auto-generated types

	def validate(self):
		if not self.naming_series_doctype:
			self.naming_series_doctype = "Sales Invoice"

		# Keep core naming series in sync when options are changed in this settings page.
		if self.has_value_changed("naming_series_options") or self.has_value_changed("naming_series_doctype"):
			if self.naming_series_options:
				_update_core_naming_series(self.naming_series_doctype, self.naming_series_options)


@frappe.whitelist()
def generate_test_payload(sales_invoice: str):
	"""Generate payload from current mapping config for a Sales Invoice."""
	if not sales_invoice:
		frappe.throw("Sales Invoice is required.")

	payload, errors = build_payload_from_sales_invoice(sales_invoice)
	payload_json = frappe.as_json(payload, indent=2)
	settings = frappe.get_single("Factura Electronica Paraguay")

	# Persist latest test output for visibility in the single doctype.
	settings.db_set("sales_invoice_for_test", sales_invoice, update_modified=False)
	settings.db_set("test_payload_json", payload_json, update_modified=False)

	return {"payload": payload, "payload_json": payload_json, "errors": errors}


def build_payload_from_sales_invoice(sales_invoice: str | Document) -> tuple[dict[str, Any], list[str]]:
	"""Build mapped payload for a Sales Invoice using current settings."""
	settings = frappe.get_single("Factura Electronica Paraguay")
	invoice = sales_invoice if isinstance(sales_invoice, Document) else frappe.get_doc("Sales Invoice", sales_invoice)
	return _build_payload(settings, invoice)


@frappe.whitelist()
def get_core_naming_series_options(doctype: str = "Sales Invoice"):
	dns = frappe.get_single("Document Naming Settings")
	return dns.get_options(doctype) or ""


@frappe.whitelist()
def sync_core_naming_series_options(doctype: str, naming_series_options: str):
	if not doctype:
		frappe.throw("DocType is required.")
	if not naming_series_options:
		frappe.throw("Naming series options are required.")

	_update_core_naming_series(doctype, naming_series_options)
	return {"ok": True}


def _update_core_naming_series(doctype: str, naming_series_options: str):
	dns = frappe.get_single("Document Naming Settings")
	dns.transaction_type = doctype
	dns.naming_series_options = naming_series_options
	dns.validate_set_series()
	dns.check_duplicate()
	dns.set_series_options_in_meta(doctype, naming_series_options)


def _build_payload(settings: Document, invoice: Document) -> tuple[dict[str, Any], list[str]]:
	payload: dict[str, Any] = {}
	errors: list[str] = []
	rows = [r for r in settings.get("mapping_rows", []) if cint(r.enabled)]
	base_context = _get_context(invoice)

	# Non-loop rows are mapped directly to target paths.
	for row in rows:
		target_path = (row.target_path or "").strip()
		if cint(row.is_loop) or not target_path or "[]" in target_path:
			continue
		value = _resolve_value(row, invoice, base_context)
		if _is_empty(value):
			if cint(row.required):
				errors.append(f"Missing required value for path: {target_path}")
			continue
		_set_path(payload, target_path, value)

	# Loop rows define how arrays are built from invoice child tables.
	for loop_def in [r for r in rows if cint(r.is_loop) and (r.loop_target_path or "").strip()]:
		loop_target_path = loop_def.loop_target_path.strip()
		table_field = (loop_def.loop_table_fieldname or "").strip()
		if not table_field:
			continue

		loop_rows = invoice.get(table_field) or []
		loop_alias = (loop_def.loop_alias or "row").strip()
		children = [
			r
			for r in rows
			if not cint(r.is_loop)
			and (r.target_path or "").startswith(f"{loop_target_path}.")
		]

		result_rows: list[dict[str, Any]] = []
		for index, loop_row in enumerate(loop_rows, start=1):
			ctx = dict(base_context)
			ctx[loop_alias] = loop_row
			result_item: dict[str, Any] = {}

			for child in children:
				full_target = child.target_path.strip()
				relative_target = full_target[len(loop_target_path) + 1 :]
				value = _resolve_value(child, invoice, ctx)
				if _is_empty(value):
					if cint(child.required):
						errors.append(f"Missing required value for path: {full_target} (row {index})")
					continue
				_set_path(result_item, relative_target, value)

			result_rows.append(result_item)

		_set_path(payload, loop_target_path.replace("[]", ""), result_rows)

	return payload, errors


def _get_context(invoice: Document) -> dict[str, Any]:
	customer = frappe.get_doc("Customer", invoice.customer) if invoice.customer else None
	billing_address = (
		frappe.get_doc("Address", invoice.customer_address)
		if invoice.customer_address and frappe.db.exists("Address", invoice.customer_address)
		else None
	)
	shipping_address = (
		frappe.get_doc("Address", invoice.shipping_address_name)
		if invoice.shipping_address_name and frappe.db.exists("Address", invoice.shipping_address_name)
		else None
	)
	sales_person = None
	if invoice.get("sales_team"):
		sales_person_name = invoice.sales_team[0].sales_person
		if sales_person_name and frappe.db.exists("Sales Person", sales_person_name):
			sales_person = frappe.get_doc("Sales Person", sales_person_name)

	currency_description = invoice.currency
	if invoice.currency and frappe.db.exists("Currency", invoice.currency):
		currency_description = frappe.db.get_value("Currency", invoice.currency, "currency_name") or invoice.currency

	return {
		"invoice": invoice,
		"customer": customer,
		"billing_address": billing_address,
		"shipping_address": shipping_address,
		"sales_person": sales_person,
		"invoice_condition_type": 2 if invoice.get("is_pos") else 1,
		"invoice_currency_description": currency_description,
		"credit_info": {
			"tipo": 1,
			"plazo": "",
			"cuotas": len(invoice.get("payment_schedule") or []),
			"monto_entrega": 0,
		},
	}


def _resolve_value(row: Document, invoice: Document, context: dict[str, Any]) -> Any:
	mode = (row.source_mode or "DocField").strip()
	value = None

	if mode == "Static":
		value = row.static_value
	elif mode == "Expression":
		value = _resolve_expression((row.expression or "").strip(), context)
	else:
		doctype = (row.source_doctype or "").strip()
		fieldname = (row.source_fieldname or "").strip()
		docname = (row.source_docname or "").strip()
		if fieldname:
			if doctype in ("", "Sales Invoice"):
				value = invoice.get(fieldname)
			elif doctype and docname and frappe.db.exists(doctype, docname):
				value = frappe.db.get_value(doctype, docname, fieldname)

	if _is_empty(value) and not _is_empty(row.default_value):
		value = row.default_value

	value = _cast_value(value, (row.target_data_type or "String").strip())
	value = _apply_transformer(value, (row.transformer or "None").strip())
	return value


def _resolve_expression(expression: str, context: dict[str, Any]) -> Any:
	if not expression:
		return None
	parts = expression.split(".")
	root_key = parts[0]
	current = context.get(root_key)
	if current is None and root_key == "invoice":
		current = context.get("invoice")
	if current is None:
		return None
	for part in parts[1:]:
		if current is None:
			return None
		if isinstance(current, dict):
			current = current.get(part)
		else:
			current = getattr(current, part, None)
	return current


def _cast_value(value: Any, target_type: str) -> Any:
	if _is_empty(value):
		return value
	if target_type == "Int":
		return cint(value)
	if target_type in ("Float", "Currency"):
		return flt(value)
	if target_type == "Check":
		return 1 if cint(value) else 0
	if target_type == "Date":
		return str(getdate(value))
	if target_type == "Datetime":
		return get_datetime(value).isoformat()
	if target_type == "JSON":
		if isinstance(value, str):
			try:
				return json.loads(value)
			except Exception:
				return value
	return value


def _apply_transformer(value: Any, transformer: str) -> Any:
	if _is_empty(value):
		return value
	if transformer == "Uppercase":
		return str(value).upper()
	if transformer == "Lowercase":
		return str(value).lower()
	if transformer == "Strip":
		return str(value).strip()
	if transformer == "Round 2":
		return round(flt(value), 2)
	if transformer == "Date ISO":
		return str(getdate(value))
	if transformer == "Datetime ISO":
		return get_datetime(value).isoformat()
	return value


def _set_path(target: dict[str, Any], path: str, value: Any):
	parts = [p for p in path.split(".") if p]
	current = target
	for part in parts[:-1]:
		current = current.setdefault(part, {})
	current[parts[-1]] = value


def _is_empty(value: Any) -> bool:
	return value in (None, "")
