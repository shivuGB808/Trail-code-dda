import base64
import json

import frappe


def get_context(context):
	encoded = frappe.form_dict.get("data")
	payload = json.loads(base64.b64decode(encoded))
	context.data = payload
