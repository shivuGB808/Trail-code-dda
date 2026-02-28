import base64
import json
from urllib.parse import quote

import frappe

from dda_ifmis.dda_pg.doctype.icici_pg.icici_pg import make_payment_icici, make_refund_icici
from dda_ifmis.dda_pg.doctype.payu_pg.payu_pg import make_payment_payu, make_refund_payu
from dda_ifmis.dda_pg.doctype.razorpay_pg.razorpay_pg import make_payment_razorpay, make_refund_razorpay
from dda_ifmis.dda_pg.doctype.sbi_epay_pg.sbi_epay_pg import make_payment_sbi_epay, make_refund_sbi

PAYMENT_DETAILS_MAP = {
	"Awaas_registration_fee": {
		"name": "applicant_name",
		"amount": "registration_amount",
		"email": "email",
		"mobile": "mobile_no",
	},
	"Awaas booking amount": {
		"name": "applicant_first_name",
		"amount": "total_amount",
		"email": "email",
		"mobile": "mobile_no",
	},
	"CRB Fee Payment": {
		"name": "name_of_agency",
		"amount": "total_amount",
		"email": "email",
		"mobile": "mobile_no",
	},
	"Park Booking": {
		"name": "applicant_name",
		"amount": "total_payable_amount",
		"email": "email",
		"mobile": "mobile_no",
	},
	"Land Pooling": {
		"name": "applicant_name",
		"amount": "total_payment",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"Permission Lift": {
		"name": "applicant_name",
		"amount": "application_fees",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"Additional Alternation": {
		"name": "applicant_name",
		"amount": "fees",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"Fuel station": {
		"name": "applicant_name",
		"amount": "amount",
		"mobile": "mobile_no",
	},
	"Water Bill": {
		"name": "applicant_name",
		"amount": "total_payable_amount",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"Hall Booking": {
		"name": "name_of_applicant",
		"amount": "net_payable_amount",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"PM UDAY": {
		"name": "name1",
		"amount": "amount",
		# "email": "email_id",
		# "mobile": "mobile_no",
	},
	"IDLI Conversion_Dues_Payment": {
		"name": "applicants_name",
		"amount": "total",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"IDLI EOT_Dues_Fee": {
		"name": "applicants_name",
		"amount": "total",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"IDLI EOT_Fee": {
		"name": "original_allottee_name",
		"amount": "total_amount",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"EMD Adhoc Challan": {
		"name": "name_of_agency",
		"amount": "emd_amount",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"IDLI Conversion_Fee_Payment": {
		"name": "freehold_in_favour_of",
		"amount": "total",
		"email": "email_id" or "",
		"mobile": "mobile_no",
	},
	"Online Building Permit System": {
		"name": "name1",
		"amount": "total_amount",
		"email": "email_id",
		"mobile": "phone_no",
	},
	"Imprest Refund": {
		"name": "employee_name",
		"amount": "amount",
	},
	"Damage Old": {
		"name": "name1",
		"amount": "total_payable_amount",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"BHOOMI LOI": {
		"name": "bidder_name",
		"amount": "grand_total",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"Park Monthly Pass": {
		"name": "primary_visitor_name",
		"amount": "amount",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"Park Ticket Booking": {
		"name": "primary_visitor_name",
		"amount": "amount",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"Bhoomi Demand letter": {
		"name": "applicant_name",
		"amount": "total_due_amount",
		"email": "email_id",
		"mobile": "mobile_no",
	},
	"Lease and License": {
		"name": "licensee_name",
		"amount": "amount",
		"email": "email_id",
		"mobile": "mobile",
	},
	"Housing Conversion": {
		"name": "allottee_name",
		"amount": "total",
		"email": "email_id",
		"mobile": "mobile_no",
	},
    "Challan":{
		"name":"name_of_the_allottee",
		"amount":"total_amount",
		"email":"email_id",
		"mobile":"mobile_number",

	},

}


@frappe.whitelist(allow_guest=True)
def get_payment_details(doctype, docname):
	if not frappe.db.exists(doctype, docname):
		frappe.throw("Invalid document")

	doc = frappe.get_doc(doctype, docname)

	return {
		"doctype": doctype,
		"docname": doc.name,
		**{
			k: getattr(doc, v, (0 if k in ["amount"] else ""))
			for k, v in PAYMENT_DETAILS_MAP.get(doctype, {}).items()
		},
	}


@frappe.whitelist(allow_guest=True)
def make_payment(doctype, docname, gateway):
	if not frappe.db.exists(doctype, docname):
		frappe.throw("Invalid Document" + doctype + " Name " + docname)

	doc = frappe.get_doc(doctype, docname)
	if doc.payment_status == "Paid":
		frappe.throw("Payment is already Received for this Transaction " + doctype + " Name " + docname)

	mobile_no = getattr(doc, PAYMENT_DETAILS_MAP.get(doctype, {}).get("mobile", ""), None)
	email = getattr(doc, PAYMENT_DETAILS_MAP.get(doctype, {}).get("email", ""), None)

	amount = getattr(doc, PAYMENT_DETAILS_MAP.get(doctype, {}).get("amount", 0), 0)
	applicant_name = getattr(doc, PAYMENT_DETAILS_MAP.get(doctype, {}).get("name", ""), None)

	if gateway == "ICICI":
		status, payment_url = make_payment_icici(doctype, docname, amount, applicant_name, mobile_no, email)
		frappe.log_error(" ICICI Sttaus " + status)
		frappe.log_error(" ICICI payment_url " + payment_url)

	elif gateway == "PayU":
		status, payment_url = make_payment_payu(doctype, docname, amount, applicant_name, mobile_no, email)
		if status == "000":
			encoded = base64.b64encode(json.dumps(payment_url).encode("utf-8")).decode("utf-8")
			return "/payu_redirect?data=" + encoded
		else:
			frappe.throw(payment_url["message"])

	elif gateway == "Razorpay":
		status, payment_url = make_payment_razorpay(
			doctype, docname, amount, applicant_name, mobile_no, email
		)
		if status == "000":
			encoded = base64.b64encode(json.dumps(payment_url).encode("utf-8")).decode("utf-8")
			return "/razorpay_redirect?data=" + encoded
		else:
			frappe.throw(payment_url["message"])

	elif gateway == "SBIePay":
		status, payment_url = make_payment_sbi_epay(
			doctype, docname, amount, applicant_name, mobile_no, email
		)
		if status == "000":
			encoded = base64.b64encode(json.dumps(payment_url).encode("utf-8")).decode("utf-8")
			return "/sbi_ePay_redirect?data=" + encoded
		else:
			frappe.throw(payment_url["message"])

	else:
		frappe.throw("Invalid payment gateway selected")

	if status == "000":
		return payment_url
	else:
		frappe.throw(payment_url)


@frappe.whitelist(allow_guest=True)
def make_refund_through_pg(doctype, docname, amount, requested_by="System", reason="Automatic"):
	status = "100"
	retMsg = "Failed to Refund"
	try:
		pg_doc = get_transaction_id_from_pg(doctype, docname)
		if not pg_doc:
			frappe.throw("No received PG transaction found")

		# use full document
		received_amount = float(pg_doc.amount)
		if float(amount) > received_amount:
			frappe.throw("Refund amount greater than original amount")

		new_refund_request = frappe.new_doc("Refund Request")
		if doctype == "CRB":
			doctype = "CRB Fee Payment"
		# MUST be set first
		new_refund_request.reference_doctype = doctype

		# Dynamic Link depends on the above field
		new_refund_request.reference_name = docname

		new_refund_request.refund_amount = amount
		new_refund_request.refund_reason = reason
		new_refund_request.status = "Requested"
		new_refund_request.requested_by = requested_by
		new_refund_request.requested_date_and_time = frappe.utils.now()
		new_refund_request.original_transaction_no = pg_doc.name

		new_refund_request.insert(ignore_permissions=True)
		frappe.db.commit()

		refund_request_id = new_refund_request.name

		status = "100"
		retMsg = "Failed"
		# frappe.msgprint(pg_doc.name)
		if pg_doc.payment_gateway == "PayU":
			status, retMsg = make_refund_payu(pg_doc.txn_id, amount, refund_request_id)
		elif pg_doc.payment_gateway == "ICICI":
			status, retMsg = make_refund_icici(pg_doc.txn_id, amount, refund_request_id)
		elif pg_doc.payment_gateway == "Razorpay":
			status, retMsg = make_refund_razorpay(pg_doc.txn_id, amount, refund_request_id)
		elif pg_doc.payment_gateway == "SBI":
			status, retMsg = make_refund_sbi(pg_doc.txn_id, amount, refund_request_id)

	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Razorpay Refund Failed | {docname}")

	return status, retMsg


def get_transaction_id_from_pg(doctype, docname):
	frappe.log_error(f"Searching for PG Transaction with document_id: {docname}")

	pg_list = frappe.get_all(
		"PG Transactions",
		filters={"document_id": docname, "status": "Received"},
		pluck="name",  # only fetch name
		order_by="creation desc",
		limit=1,
	)

	if not pg_list:
		return

	pg_doc = frappe.get_doc("PG Transactions", pg_list[0])
	return pg_doc


@frappe.whitelist()
def get_transaction_status(type, data):
	if type == "ifmis":
		doc = frappe.get_doc("Receipt Doctype Mapping", data.get("reference_no"))

	elif type == "txn":
		doc = frappe.get_doc("Receipt Doctype Mapping", data.get("transaction_id"))

	elif type == "bank":
		doc = frappe.get_doc("Receipt Doctype Mapping", data.get("bank_ref"))

	return {"status": doc.status}
