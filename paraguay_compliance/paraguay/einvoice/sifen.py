"""SIFEN / FacturaSend integration hooks."""

import frappe
from frappe.integrations.utils import create_request_log, make_post_request
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
