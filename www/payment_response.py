import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import frappe
import requests

from dda_ifmis.dda_pg.pg_utils import (
	get_invoice_details,
	get_pg_settings,
	get_razorpay_gateway_settings,
	sbi_decrypt,
	sbi_encrypt,
	sbi_parse_sbi_pipe_response,
	verify_icici_response_hash,
	verify_icici_transaction,
	verify_payment_payu,
	verify_sbi_transaction,
)
from dda_ifmis.dda_receipts.pg_utils import update_pg_transaction


def get_context(context):
	args = frappe.form_dict or {}

	headers = frappe.request.headers
	data = frappe.local.form_dict or frappe.request.get_json()
	if not data:
		frappe.throw("No Data Received in Response")
	frappe.log_error("Payment Response Page", data)
	pg = detect_pg(data)  # razorpay / icici / payu
	invoice_link = None
	status = None
	if pg == "RazorPay":
		raw_response, invoice_link = handle_razorpay_response(data)
		if raw_response:
			data = json.loads(raw_response)
		else:
			frappe.throw("Kindly Check Later. Contact DDA IFMIS Team")
	elif pg == "ICICI":
		status, invoice_link = handle_icici_response(data)
	elif pg == "PayU":
		status, invoice_link = handle_payu_response(data)
	elif pg == "SBI":
		sbi_settings = get_pg_settings("SBI")
		merchant_key = sbi_settings["merchant_key"]
		decrypted_data = sbi_decrypt(merchant_key, data.get("encData"))
		frappe.log_error("decrypted data", decrypted_data)
		data = sbi_parse_sbi_pipe_response(decrypted_data, "trans_resp")
		status, invoice_link = handle_sbi_response(data, decrypted_data)

		frappe.log_error("decrypted data for normalizing", data)
	else:
		frappe.throw("Unknown PG. Contact DDA IFMIS Team")
		frappe.log_error("Unknown PG webhook")
	frappe.log_error("Payment Response ", invoice_link)
	# return "OK"
	context.status = normalize_status(pg, data)
	fields = normalize_fields(pg, data)
	frappe.log_error("fields JSON", fields)
	context.gateway = pg
	context.transaction_id = fields.get("ref_id")
	context.bank_transaction_id = fields.get("pg_txn_id")
	context.transaction_date_time = fields.get("txn_date_time")
	context.payment_mode = fields.get("mode")
	context.amount = fields.get("amount")
	context.message = fields.get("message")
	if invoice_link and context.status == "success":
		invoice_link = invoice_link.replace("http://", "https://")
		context.invoice_url = invoice_link


#    context.redirect_url = "/"


def detect_pg(data):
	if data.get("razorpay_signature"):
		return "RazorPay"
	if data.get("merchantId"):
		return "ICICI"
	if data.get("mihpayid"):
		return "PayU"
	if data.get("merchIdVal"):
		return "SBI"
	return None


def normalize_status(pg, data):
	if pg == "RazorPay":
		return "success" if data.get("status") == "captured" else "failed"
	if pg == "ICICI":
		return "success" if data.get("responseCode") == "0000" else "failed"
	if pg == "PayU":
		return "success" if data.get("status") == "success" else "failed"
	if pg == "SBI":
		return "success" if data.get("status") == "SUCCESS" else "failed"


def handle_payu_response(data):
	txnid = data.get("txnid")
	try:
		response_data, invoice_link = get_invoice_details(txnid)
		frappe.log_error(
			title="handle_payu_response",
			message=f"Response Data: {frappe.as_json(response_data)} | Invoice Link: {invoice_link}",
		)
		if response_data is not None:
			return response_data, invoice_link
	except Exception:
		frappe.log_error("PayU Transaction not updated via WebHook", txnid)

	verification_response = verify_payment_payu(txnid)
	txn_data = verification_response["transaction_details"].get(txnid)
	status = None
	sales_download_link = None

	if not txn_data:
		frappe.log_error("PayU Transaction not found Response", txn_data)
	else:
		try:
			status, sales_download_link = update_pg_transaction(txnid, frappe.as_json(txn_data), "PayU")
			frappe.log_error("Sale Invoice URL {status}", sales_download_link)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "update_pg_transaction")

	if txn_data["status"] == "success" and txn_data["error_code"] == "E000":
		frappe.log_error("Verification Success ", str(txnid))

	return status, sales_download_link


def handle_razorpay_response(data):
	order_id = data.get("razorpay_order_id")
	data, invoice_link = get_invoice_details(order_id)
	return data, invoice_link


def handle_icici_response(data):
	gateway = get_pg_settings("ICICI")
	secret_key = gateway["secret_key"]
	is_valid = verify_icici_response_hash(data, secret_key)
	merchant_txn_no = data.get("merchantTxnNo")
	txn_ID = data.get("txnID")
	status = None
	sale_invoice_url = None
	if is_valid:
		try:
			response_json = verify_icici_transaction(merchant_txn_no, txn_ID)
			frappe.log_error("verify_icici_transaction json", response_json)
			status, sale_invoice_url = update_pg_transaction(
				merchant_txn_no, frappe.as_json(response_json), "ICICI"
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "update_pg_transaction")

	return status, sale_invoice_url


def handle_sbi_response(resp_parsed, decrypted_val):
	try:
		verification = verify_sbi_transaction(decrypted_val)
		frappe.log_error("sbi_verification_bool", verification)
		status, sale_invoice_url = update_pg_transaction(
			resp_parsed["merchantOrderNo"], frappe.as_json(resp_parsed), "SBI"
		)
		frappe.log_error("status and sale_invoice_url", [status, sale_invoice_url])
		#  TODO: verification logic and preceding function
		if verification:
			return status, sale_invoice_url
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), str(e))
	return status, sale_invoice_url


def normalize_fields(pg, data):
	received_date = frappe.utils.now()
	if pg == "RazorPay":
		if data.get("created_at") or data["acquirer_data"]["created_at"]:
			dt_utc = datetime.fromtimestamp(
				data.get("created_at") or data["acquirer_data"]["created_at"], tz=timezone.utc
			)
			dt_ist = dt_utc.astimezone(timezone(timedelta(hours=5, minutes=30)))
			received_date = dt_ist.replace(tzinfo=None)
		return {
			"ref_id": data.get("order_id"),
			"pg_txn_id": data.get("id"),
			"txn_date_time": received_date,
			"amount": (data.get("amount") / 100),  # paise → rupees
			"mode": data.get("method") or "",
			"message": data.get("error_description") or "Payment Successful",
		}

	if pg == "PayU":
		return {
			"ref_id": data.get("txnid"),
			"pg_txn_id": data.get("mihpayid"),
			"txn_date_time": data.get("addedon"),
			"amount": float(data.get("amount") or 0),
			"mode": data.get("mode") or "",
			"message": data.get("field7") or data.get("field9"),
		}

	if pg == "ICICI":
		if data.get("paymentDateTime"):
			received_date = datetime.strptime(data.get("paymentDateTime"), "%Y%m%d%H%M%S")

		return {
			"ref_id": data.get("merchantTxnNo") or data.get("orderId"),
			"pg_txn_id": data.get("txnID") or data.get("iciciTxnId"),
			"txn_date_time": received_date,
			"mode": data.get("paymentMode") or "",
			"amount": float(data.get("amount") or 0),
			"message": data.get("respDescription") or data.get("txnRespDescription"),
		}

	if pg == "SBI":
		return {
			"ref_id": data.get("merchantOrderNo"),
			"pg_txn_id": data.get("bankRefNo"),
			"amount": float(data.get("postingAmount") or 0),
			"message": data.get("respMsg"),
		}
