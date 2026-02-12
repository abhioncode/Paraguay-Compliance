def run_setup(*args, **kwargs):
	import frappe

	# ERPNext warehouse bootstrap can fail on fresh sites if Transit type is absent.
	if not frappe.db.exists("Warehouse Type", "Transit"):
		doc = frappe.new_doc("Warehouse Type")
		doc.name = "Transit"
		doc.insert(ignore_permissions=True)
