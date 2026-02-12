"""SIFEN / FacturaSend integration hooks."""

from typing import Any

import frappe
from frappe.integrations.utils import create_request_log, make_get_request, make_post_request
from frappe.utils import cint

from paraguay_compliance.paraguay_compliance.doctype.factura_electronica_paraguay.factura_electronica_paraguay import (
	build_payload_from_sales_invoice,
)


def send_sales_invoice_to_facturasend(doc, method=None):
	"""Before submit hook for Sales Invoice.

	Build payload from mapping config and send to configured REST endpoint.
	Blocks submission if mapping or API call fails.
	"""
	settings = frappe.get_single("Factura Electronica Paraguay")
	payload, errors = build_payload_from_sales_invoice(doc)

	if cint(settings.test_mode):
		payload_json = frappe.as_json(payload, indent=2)
		if errors:
			frappe.msgprint(
				title="Factura Electronica Paraguay (Test Mode)",
				indicator="orange",
				message=(
					"<p>Payload generated with missing required mappings:</p>"
					f"<pre>{frappe.as_json(errors, indent=2)}</pre>"
					f"<pre>{payload_json}</pre>"
				),
			)
		else:
			frappe.msgprint(
				title="Factura Electronica Paraguay (Test Mode)",
				indicator="blue",
				message=f"<p>Payload preview (API call skipped):</p><pre>{payload_json}</pre>",
			)
		return

	if not settings.tenent_url:
		frappe.throw("Factura Electronica Paraguay: Tenent URL is required when Test Mode is disabled.")

	if not settings.api_key:
		frappe.throw("Factura Electronica Paraguay: API Key is required when Test Mode is disabled.")

	if errors:
		frappe.throw(
			"Factura Electronica Paraguay payload validation failed:\n" + "\n".join(f"- {err}" for err in errors)
		)

	request_body = [payload]
	headers = {
		"Authorization": f"Bearer {settings.api_key}",
		"Content-Type": "application/json",
	}

	try:
		response = make_post_request(settings.tenent_url, headers=headers, json=request_body)
		_apply_response_fields(doc, response)
		create_request_log(
			data=request_body,
			service_name="FacturaSend",
			request_headers=headers,
			output=response,
			reference_doctype=doc.doctype,
			reference_docname=doc.name,
			is_remote_request=1,
		)
	except Exception:
		create_request_log(
			data=request_body,
			service_name="FacturaSend",
			request_headers=headers,
			error=frappe.get_traceback(),
			reference_doctype=doc.doctype,
			reference_docname=doc.name,
			is_remote_request=1,
		)
		raise


def _apply_response_fields(doc, response: Any):
	"""Store CDC and Estado from provider response on Sales Invoice."""
	cdc = _find_value(response, {"cdc"})
	estado = _find_value(response, {"estado", "status", "estado_de", "estadoDocumento"})

	if doc.meta.get_field("pyg_cdc") and cdc is not None:
		doc.pyg_cdc = str(cdc)

	if doc.meta.get_field("pyg_estado") and estado is not None:
		doc.pyg_estado = str(estado)


def _find_value(node: Any, keys: set[str]):
	"""Find first matching key recursively in dict/list payloads."""
	if isinstance(node, dict):
		for key, value in node.items():
			if str(key).lower() in {k.lower() for k in keys}:
				return value
		for value in node.values():
			found = _find_value(value, keys)
			if found is not None:
				return found
	elif isinstance(node, list):
		for value in node:
			found = _find_value(value, keys)
			if found is not None:
				return found
	return None


@frappe.whitelist()
def check_sales_invoice_status(sales_invoice: str):
	"""Check DE status by CDC and update Sales Invoice estado field."""
	if not sales_invoice:
		frappe.throw("Sales Invoice is required.")

	doc = frappe.get_doc("Sales Invoice", sales_invoice)
	if not doc.get("pyg_cdc"):
		frappe.throw("Sales Invoice has no CDC. Submit to FacturaSend first.")

	settings = frappe.get_single("Factura Electronica Paraguay")
	if not settings.check_status_url:
		frappe.throw("Factura Electronica Paraguay: Check Status URL is required.")
	if not settings.api_key:
		frappe.throw("Factura Electronica Paraguay: API Key is required.")

	url = _build_status_url(settings.check_status_url, doc.pyg_cdc)
	headers = {"Authorization": f"Bearer {settings.api_key}"}

	try:
		response = make_get_request(url, headers=headers)
		create_request_log(
			data={"sales_invoice": doc.name, "cdc": doc.pyg_cdc},
			service_name="FacturaSend Status Check",
			request_headers=headers,
			output=response,
			reference_doctype=doc.doctype,
			reference_docname=doc.name,
			is_remote_request=1,
		)
	except Exception:
		create_request_log(
			data={"sales_invoice": doc.name, "cdc": doc.pyg_cdc},
			service_name="FacturaSend Status Check",
			request_headers=headers,
			error=frappe.get_traceback(),
			reference_doctype=doc.doctype,
			reference_docname=doc.name,
			is_remote_request=1,
		)
		raise

	situacion = _find_value(response, {"situacion", "estado", "status"})
	if situacion is not None and doc.meta.get_field("pyg_estado"):
		doc.db_set("pyg_estado", str(situacion), update_modified=False)

	is_approved = str(situacion) in {"2", "3"}
	return {
		"sales_invoice": doc.name,
		"cdc": doc.pyg_cdc,
		"situacion": situacion,
		"is_approved": is_approved,
		"response": response,
	}


def _build_status_url(base_url: str, cdc: str) -> str:
	base_url = (base_url or "").strip()
	if "{cdc}" in base_url:
		return base_url.replace("{cdc}", cdc)
	if base_url.endswith("/"):
		return f"{base_url}{cdc}"
	return f"{base_url}/{cdc}"
