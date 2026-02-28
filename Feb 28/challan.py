# # Copyright (c) 2026, BEL and contributors
# # For license information, please see license.txt
import json
import secrets
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.pdf import get_pdf


class Challan(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from dda_ifmis.dda_receipts.doctype.challan_payment_child_table.challan_payment_child_table import ChallanPaymentChildtable
		from frappe.types import DF

		aadhaar_no: DF.Int
		address_line_1: DF.Data | None
		address_line_2: DF.Data | None
		address_line_3: DF.Data | None
		amended_from: DF.Link | None
		area_sq_mtr: DF.Float
		bank_account_no: DF.Int
		bank_name: DF.Data | None
		block: DF.Data | None
		category_header: DF.Data | None
		department: DF.Data | None
		depositor_name: DF.Data | None
		email_id: DF.Data | None
		file_name: DF.Data | None
		fl_noid: DF.Data | None
		flatplotunit_no: DF.Data | None
		floor: DF.Data | None
		gst_number: DF.Data | None
		gst_type: DF.Literal["Not Applicable", "Individual", "Company"]
		ifsc_code: DF.Data | None
		locality: DF.Data | None
		locality_header: DF.Data | None
		locality_id: DF.Data | None
		mobile_number: DF.Data | None
		mode_of_payment: DF.Literal["--Select--", "RTGS / NEFT", "Net Banking / SBI NEFT"]
		name_of_the_allottee: DF.Data | None
		pan_number: DF.Data | None
		payment_status: DF.Literal["Paid", "Partially Paid", "Unpaid"]
		pdf_file: DF.Data | None
		pincode: DF.Int
		pocket: DF.Data | None
		public_token: DF.Data | None
		scheme: DF.Data | None
		scheme_descr: DF.Data | None
		scheme_id: DF.Data | None
		sector: DF.Data | None
		sequence_no: DF.Data | None
		source_type: DF.Literal["Flats", "Plots"]
		token_expiry: DF.Datetime | None
		total_amount: DF.Currency
		type_of_payments: DF.Table[ChallanPaymentChildtable]
		virtual_bank_acc: DF.Data | None
		year: DF.Data | None
		zone: DF.Data | None
	# end: auto-generated types
	# --- Token generation before insert ---
	def before_insert(self):
		"""Generate secure public token if not already present"""
		if not self.public_token:
			self.public_token = secrets.token_urlsafe(32)
			self.token_expiry = datetime.now() + timedelta(minutes=15)





	# --- Generate PDF after submit ---
	def on_submit(self):
		"""Generate PDF on submit safely"""
		try:
			html = frappe.get_print(doctype="Challan", name=self.name, print_format="Challan")

			pdf = get_pdf(html)

			file_doc = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": f"{self.name}.pdf",
					"attached_to_doctype": "Challan",
					"attached_to_name": self.name,
					"content": pdf,
					"is_private": 1,  # keep private
				}
			)
			file_doc.save(ignore_permissions=True)

			# Use db_set to avoid submit errors
			self.db_set("pdf_file", file_doc.file_url, update_modified=False)

		except Exception:
			frappe.log_error(frappe.get_traceback(), title=f"PDF Generation Failed for {self.name}")
			frappe.msgprint(_("PDF generation failed, but Challan was submitted."))

	def before_submit(self):

		if not self.virtual_bank_acc and self.bank_name:

			bank_ifsc = frappe.db.get_value(
				"DDA Awaas Banks",
				{"bank": self.bank_name},  # ← use field filter
				"ifsc_code"
			)

			if bank_ifsc:
				self.ifsc_code = bank_ifsc
				ifsc_prefix = bank_ifsc[:3]
				clean_name = self.name.replace("-", "")
				self.virtual_bank_acc = f"DDA{ifsc_prefix}{clean_name}"


# --- Download API ---
@frappe.whitelist(allow_guest=True)
def download_challan(challan_name, token):
	frappe.local.flags.ignore_csrf = True
	try:
		doc = frappe.get_doc("Challan", challan_name)

		# Token validation
		if not doc.public_token or token != doc.public_token:
			frappe.throw(_("Unauthorized access"))

		# Expiry validation
		if doc.token_expiry and frappe.utils.now_datetime() > doc.token_expiry:
			frappe.throw(_("Download link expired"))

		# Return PDF
		file_doc = frappe.get_doc("File", {"file_url": doc.pdf_file})
		frappe.local.response.filename = f"{challan_name}.pdf"
		frappe.local.response.filecontent = file_doc.get_content()
		frappe.local.response.type = "download"

	except Exception:
		frappe.throw(_("Unable to download PDF"))


# --- Create Flats Challan API ---
@frappe.whitelist(allow_guest=True)
def create_challan(data=None):
	frappe.local.flags.ignore_csrf = True

	try:
		raw_data = frappe.local.request.get_data(as_text=True)
		if not raw_data:
			frappe.throw(_("No data received"))

		data = json.loads(raw_data)

		required_fields = [
			"scheme",
			"zone",
			"locality",
			"name_of_the_allottee",
			"mobile_number",
			"total_amount",
		]
		for field in required_fields:
			if not data.get(field):
				frappe.throw(_(f"Missing required field: {field}"))

		# Generate file_name
		category = data.get("category_header", "")
		locality_header = data.get("locality_header", "")
		sequence = data.get("sequence_no", "")
		year = data.get("year", "")
		scheme_id = data.get("scheme_id", "")
		locality_id = data.get("locality_id", "")

		file_name = f"{category} / {locality_header} ({sequence}) {year} / {scheme_id} / {locality_id}"

		# Ensure child table exists
		type_of_payments = data.get("type_of_payments") or []

		# Create Challan doc
		doc = frappe.get_doc(
			{
				"doctype": "Challan",
				"scheme": data.get("scheme"),
				"zone": data.get("zone"),
				"locality": data.get("locality"),
				"name_of_the_allottee": data.get("name_of_the_allottee"),
				"mobile_number": data.get("mobile_number"),
				"depositor_name": data.get("depositor_name"),
				"block": data.get("block"),
				"pocket": data.get("pocket"),
				"flatplotunit_no": data.get("flatplotunit_no"),
				"floor": data.get("floor"),
				"fl_noid": data.get("fl_noid"),
				"area_sq_mtr": data.get("area_sq_mtr"),
				"scheme_descr": data.get("scheme_descr"),
				"gst_type": data.get("gst_type"),
				"gst_number": data.get("gst_number"),
				"address_line_1": data.get("address_line_1"),
				"address_line_2": data.get("address_line_2"),
				"address_line_3": data.get("address_line_3"),
				"pincode": data.get("pincode"),
				"email_id": data.get("email_id"),
				"pan_number": data.get("pan_number"),
				"category_header": category,
				"locality_header": locality_header,
				"sequence_no": sequence,
				"year": year,
				"scheme_id": scheme_id,
				"locality_id": locality_id,
				"file_name": file_name,
				"sector": data.get("sector"),
				"total_amount": data.get("total_amount"),
				"mode_of_payment": data.get("mode_of_payment"),
				"type_of_payments": type_of_payments,
				"bank_name" : data.get("bank_name"),
				"ifsc_code" : data.get("ifsc_code"),
				"source_type": "Flats",
			}
		)

		doc.insert(ignore_permissions=True)
		doc.submit()
		frappe.db.commit()

		return {"status": "success", "token": doc.public_token, "name": doc.name}

	except frappe.ValidationError as ve:
		frappe.db.rollback()
		frappe.log_error(
    message=frappe.get_traceback(),
    title="Challan Validation Error"
)
		# frappe.log_error(frappe.get_traceback(), title="Challan Validation Error")
		return {"status": "error", "message": str(ve), "_traceback": frappe.get_traceback()}

	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), title="Challan Creation Failed")
		return {"status": "error", "message": str(e), "_traceback": frappe.get_traceback()}


# --- Create Plots Challan API ---
@frappe.whitelist(allow_guest=True)
def create_plots_challan(data):
	frappe.local.flags.ignore_csrf = True
	try:
		data = frappe.parse_json(data)

		category = data.get("category_header", "")
		locality_header = data.get("locality_header", "")
		sequence = data.get("sequence_no", "")
		year = data.get("year", "")
		scheme_id = data.get("scheme_id", "")
		locality_id = data.get("locality_id", "")

		file_name = f"{category} / {locality_header} ({sequence}) {year} / {scheme_id} / {locality_id}"

		doc = frappe.get_doc(
			{
				"doctype": "Challan",
				"scheme": data.get("scheme"),
				"zone": data.get("zone"),
				"locality": data.get("locality"),
				"name_of_the_allottee": data.get("name_of_the_allottee"),
				"mobile_number": data.get("mobile_number"),
				"depositor_name": data.get("depositor_name"),
				"block": data.get("block"),
				"pocket": data.get("pocket"),
				"flatplotunit_no": data.get("flatplotunit_no"),
				"floor": data.get("floor"),
				"fl_noid": data.get("fl_noid"),
				"area_sq_mtr": data.get("area_sq_mtr"),
				"scheme_descr": data.get("scheme_descr"),
				"gst_type": data.get("gst_type"),
				"gst_number": data.get("gst_number"),
				"address_line_1": data.get("address_line_1"),
				"address_line_2": data.get("address_line_2"),
				"address_line_3": data.get("address_line_3"),
				"pincode": data.get("pincode"),
				"email_id": data.get("email_id"),
				"pan_number": data.get("pan_number"),
				"category_header": category,
				"locality_header": locality_header,
				"sequence_no": sequence,
				"year": year,
				"scheme_id": scheme_id,
				"locality_id": locality_id,
				"file_name": file_name,
				"sector": data.get("sector"),
				"total_amount": data.get("total_amount"),
				"mode_of_payment": data.get("mode_of_payment"),
				"payment_type": data.get("payment_type"),
				"payment_code": data.get("payment_code"),
				"amount": data.get("amount"),
				"source_type": "Plots",
			}
		)

		doc.insert(ignore_permissions=True)
		doc.submit()
		frappe.db.commit()

		return {"status": "success", "name": doc.name}

	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), title="Plots Challan Creation Failed")
		return {"status": "error", "message": str(e), "_traceback": frappe.get_traceback()}


# --- Get Challan Details API ---
@frappe.whitelist(allow_guest=True)
def get_challan_details(source_type, docname, mobile_number):
	docname = docname.strip()
	mobile_number = mobile_number.strip()

	doc = frappe.get_value(
		"Challan",
		{
			"name": docname,
			"mobile_number": mobile_number,
			"source_type": source_type,
			"docstatus": 1,
		},
		["name", "name_of_the_allottee", "mobile_number", "total_amount", "payment_status"],
		as_dict=True,
	)

	if not doc:
		return {"status": "not_found"}

	if doc.payment_status == "Paid":
		return {"status": "paid"}

	return {"status": "unpaid", "data": doc}







@frappe.whitelist(allow_guest=True)
def get_sector(file_number):

    doc = frappe.get_all(
        "Awaas Demand Letter",
        filters={"file_number": file_number},
        fields=[
            "sector",
            "block",
            "pocket",
            "floor",
            "floor_no",
            "mobile_no",
            "email",
            "pan_number",
            "houseplot_no",
            "streetroad",
            "arealocality",
            "pincode",
            "district",
            "state",
            "townvillage",
            "applicant_first_name",
            "applicant_middle_name",
            "applicant_last_name"
        ],
        limit=1
    )

    if not doc:
        return None















# @frappe.whitelist(allow_guest=True)
# def create_challan_and_download(data=None):
#     import json
#     from frappe.utils.pdf import get_pdf

#     frappe.local.flags.ignore_csrf = True

#     try:
#         data = json.loads(frappe.local.request.get_data(as_text=True))

#         # --- Step 1: Create Challan ---
#         doc = frappe.get_doc({
#             "doctype": "Challan",
#             "scheme": data.get("scheme"),
#             "zone": data.get("zone"),
#             "locality": data.get("locality"),
#             "name_of_the_allottee": data.get("name_of_the_allottee"),
#             "mobile_number": data.get("mobile_number"),
#             "depositor_name": data.get("depositor_name"),
#             "block": data.get("block"),
#             "pocket": data.get("pocket"),
#             "flatplotunit_no": data.get("flatplotunit_no"),
#             "floor": data.get("floor"),
#             "fl_noid": data.get("fl_noid"),
#             "area_sq_mtr": data.get("area_sq_mtr"),
#             "scheme_descr": data.get("scheme_descr"),
#             "total_amount": data.get("total_amount"),
#             "mode_of_payment": data.get("mode_of_payment"),
#             "source_type": "Flats"
#         })
#         doc.insert(ignore_permissions=True)

#         # --- Step 2: Generate virtual account number ---
#         selected_bank = data.get("bank_name")
#         if selected_bank:
#             bank_doc = frappe.get_all(
#                 "DDA Awaas Banks",
#                 filters={"name": selected_bank},
#                 fields=["ifsc_code"],
#                 limit=1
#             )
#             if bank_doc:
#                 ifsc_code = bank_doc[0].ifsc_code
#                 ifsc_prefix = ifsc_code[2:5]  # adjust prefix as needed
#                 virtual_ac_no = f"DDA{ifsc_prefix}{doc.name}"
#                 doc.db_set("virtual_ac_no", virtual_ac_no)

#         # --- Step 3: Submit Challan ---
#         doc.submit()
#         frappe.db.commit()

#         # --- Step 4: Generate PDF with virtual_ac_no now set ---
#         html = frappe.get_print(doctype="Challan", name=doc.name, print_format="Challan")
#         pdf = get_pdf(html)

#         # --- Step 5: Save PDF as File ---
#         file_doc = frappe.get_doc({
#             "doctype": "File",
#             "file_name": f"{doc.name}.pdf",
#             "attached_to_doctype": "Challan",
#             "attached_to_name": doc.name,
#             "content": pdf,
#             "is_private": 1
#         })
#         file_doc.save(ignore_permissions=True)

#         # Update Challan with PDF file URL
#         doc.db_set("pdf_file", file_doc.file_url, update_modified=False)

#         # --- Step 6: Return PDF for immediate download ---
#         frappe.local.response.filename = f"{doc.name}.pdf"
#         frappe.local.response.filecontent = pdf
#         frappe.local.response.type = "download"

#     except Exception:
#         frappe.log_error(frappe.get_traceback(), "Challan Save & Download Failed")
#         frappe.throw("Unable to create and download Challan")