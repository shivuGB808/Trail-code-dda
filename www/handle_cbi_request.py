import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime

import frappe
from frappe.utils import now


@frappe.whitelist(allow_guest=True)
def cbi_challan_verification_webhook():
	"""
	Webhook for CBI challan verification.
	- parse_transactions(payload) -> list[dict]
	- update existing Challan Status by challan_no or create new one
	- minimal, per-transaction try/except using frappe.get_traceback()
	"""

	frappe.log_error("Invoked CBI Webhook")

	payload = None
	try:
		payload = frappe.request.get_data(as_text=True)
		frappe.log_error("raw payload", payload)
	except Exception:
		frappe.log_error("No Payload Received")
		frappe.local.response["message"] = "No payload received"
		frappe.local.response["http_status_code"] = 400
		return

	frappe.log_error("Received payload", payload)

	# If payload is still empty, return 400 so sender knows
	if not payload:
		frappe.local.response["message"] = "No payload received"
		frappe.local.response["http_status_code"] = 400
		return

	try:
		parsed_payload = parse_transactions(payload)
	except Exception:
		frappe.log_error("Failed to parse payload in webhook", frappe.get_traceback())
		parsed_payload = []

	frappe.log_error("CBI parsed response", parsed_payload)

	for transaction in parsed_payload:
		try:
			challan_no = (transaction.get("ChallanNo") or transaction.get("challan_no") or "").strip()
			bank = "CBI"
			# map incoming fields to your DocType fields (adjust names as needed)
			doc_fields = {
				"bank": bank,
				"challan_no": challan_no,
				"request_id": transaction.get("RequestId"),
				"amount_paid": transaction.get("AmountPaid"),
				"amount_received": transaction.get("AmountReceived"),
				"payment_mode": transaction.get("PaymentMode"),
				"payment_date": transaction.get("PaymentDate"),  # datetime.date or string or None
				"bank_utr_no": transaction.get("BankUTRNo"),
				"webhook_received_at": now(),
			}
			frappe.log_error("Parsed CBI payload(doc_fields)", doc_fields)
			# optional: avoid overwriting with empty values
			# doc_fields = {k: v for k, v in doc_fields.items() if v not in (None, "")}

			existing_name = None
			if challan_no:
				try:
					existing_name = frappe.db.get_value("Challan Status", {"challan_no": challan_no}, "name")
				except Exception:
					try:
						rows = frappe.get_all(
							"Challan Status",
							filters={"challan_no": challan_no},
							fields=["name"],
							limit_page_length=1,
						)
						existing_name = rows[0].name if rows else None
					except Exception:
						existing_name = None

			if existing_name:
				doc = frappe.get_doc("Challan Status", existing_name)
				for key, val in doc_fields.items():
					if hasattr(doc, key):
						setattr(doc, key, val)
				doc.save(ignore_permissions=True)
				frappe.log_error(f"Updated Challan Status: {existing_name}", doc_fields)
			else:
				# remove helper-only keys if they don't exist on the DocType
				create_fields = {k: v for k, v in doc_fields.items() if k != "webhook_received_at"}
				new_doc = frappe.get_doc({"doctype": "Challan Status", **create_fields})
				new_doc.insert(ignore_permissions=True)
				frappe.log_error(f"Inserted Challan Status: {new_doc.name}", doc_fields)

		except Exception:
			frappe.log_error("Error processing transaction in webhook", frappe.get_traceback())

	# acknowledge sender
	frappe.local.response["message"] = "OK"
	frappe.local.response["http_status_code"] = 200
	return


def _strip_quotes(s: str) -> str:
	if s is None:
		return ""
	s = s.strip()
	if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
		return s[1:-1]
	return s


def _element_children_to_dict(elem):
	"""
	Convert direct children of elem into a dict.
	If a child tag repeats, its values become a list.
	Leaf child values are returned as stripped strings (no '#text' wrapper).
	"""
	result = {}
	counts = defaultdict(int)

	for child in list(elem):
		tag = child.tag
		# If child has its own children, recurse
		if list(child):
			value = _element_children_to_dict(child)
		else:
			value = _strip_quotes(child.text) if child.text else ""

		counts[tag] += 1
		if counts[tag] == 1:
			result[tag] = value
		else:
			if not isinstance(result[tag], list):
				result[tag] = [result[tag]]
			result[tag].append(value)

	if elem.attrib:
		result["@attrs"] = dict(elem.attrib)

	return result


def _parse_date_simple(s: str) -> date | None:
	"""
	Try a few common date formats and return a datetime.date.
	On failure return None. Keep it simple and handle exceptions.
	"""
	if not s:
		return None
	s = s.strip().strip("\"'")
	formats = [
		"%m/%d/%Y",  # 6/30/2014
		"%d-%m-%Y",  # 23-01-2016
		"%d/%m/%Y",  # 23/01/2016
		"%Y-%m-%d",  # 2016-01-23
		"%d%m%Y",  # 23012016
		"%d-%m-%Y %H:%M:%S",
		"%d/%m/%Y %H:%M:%S",
		"%Y-%m-%d %H:%M:%S",
		"%m/%d/%Y %H:%M:%S",
	]
	for fmt in formats:
		try:
			return datetime.strptime(s, fmt).date()
		except Exception:
			continue
	# last-ditch: try to parse date part if there's a datetime string
	try:
		date_part = s.split()[0]
		for fmt in ("%m/%d/%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d%m%Y"):
			try:
				return datetime.strptime(date_part, fmt).date()
			except Exception:
				continue
	except Exception:
		frappe.log_error("Date converisn failed for CBI message", frappe.get_traceback())

	try:
		frappe.log_error(f"Unparsed date string in _parse_date_simple: {s}", "date_parse_failure")
	except Exception:
		pass

	return None


def parse_transactions(xml_text: str, record_tag: str = "post"):
	"""
	Parse xml_text and return a list of dicts for each <record_tag> element.
	Converts PaymentDate (if present) to datetime.date objects.
	Always returns a list (empty list on parse error or if no records found).
	"""
	try:
		root = ET.fromstring(xml_text)
	except Exception as e:
		try:
			import frappe

			frappe.log_error(f"XML parse error in parse_transactions: {e}", xml_text[:1000])
		except Exception:
			pass
		return []

	records = root.findall(".//" + record_tag)
	if not records and root.tag == record_tag:
		records = [root]
	if not records:
		single = root.find(record_tag)
		if single is not None:
			records = [single]

	parsed = []
	for rec in records:
		rec_dict = _element_children_to_dict(rec)

		# Convert PaymentDate to datetime.date if present and is a string
		try:
			if "PaymentDate" in rec_dict and isinstance(rec_dict["PaymentDate"], str):
				parsed_date = _parse_date_simple(rec_dict["PaymentDate"])
				rec_dict["PaymentDate"] = parsed_date
		except Exception:
			# keep minimal handling: log if frappe available, otherwise ignore
			try:
				import frappe

				frappe.log_error("PaymentDate conversion failed", rec_dict.get("PaymentDate", ""))
			except Exception:
				pass

		parsed.append(rec_dict)

	return parsed
