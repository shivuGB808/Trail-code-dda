import base64
import json

import frappe


def get_context(context):
	encoded = frappe.form_dict.get("data")
	payload = json.loads(base64.b64decode(encoded))
	# context.data = payload
	context.action = payload["action"]
	context.merchIdVal = payload["fields"]["merchIdVal"]
	context.EncryptTrans = payload["fields"]["EncryptTrans"]
	frappe.log_error("Payload", payload)
