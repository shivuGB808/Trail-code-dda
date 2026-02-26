import frappe

# www/awaas_details.py


def get_context(context):
	name = frappe.form_dict.get("name")

	if not name:
		frappe.throw("Application number missing")

	context.record = frappe.get_doc("Awaas_registration_fee", name)
