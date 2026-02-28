# Copyright (c) 2025, awaas and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from india_compliance.gst_india.utils import (
	guess_gst_category,
	is_autofill_party_info_enabled,
	is_valid_pan,
	validate_gst_category,
	validate_gstin,
)


class AwaasDemandLetter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from dda_ifmis.awaas.doctype.dl_payment_table.dl_payment_table import DLPaymentTable

		amended_from: DF.Link | None
		amount_of_corpus_fund: DF.Currency
		applicant_first_name: DF.Autocomplete | None
		applicant_last_name: DF.Autocomplete | None
		applicant_middle_name: DF.Autocomplete | None
		application_no: DF.Autocomplete | None
		arealocality: DF.Autocomplete | None
		bank_account_no: DF.Autocomplete | None
		bank_name: DF.Autocomplete | None
		block: DF.Autocomplete | None
		block_end_date: DF.Autocomplete | None
		branch_name: DF.Autocomplete | None
		capitalized_ground_rent: DF.Currency
		carpet_areasqm: DF.Autocomplete | None
		category: DF.Autocomplete | None
		demand_letter_no: DF.Autocomplete | None
		district: DF.Autocomplete | None
		email: DF.Autocomplete | None
		emd: DF.Currency
		father_name: DF.Autocomplete | None
		file_number: DF.Autocomplete | None
		final_demanded_amount: DF.Currency
		fire_risk_cover: DF.Currency
		flat_category: DF.Autocomplete | None
		floor: DF.Autocomplete | None
		floor_no: DF.Autocomplete | None
		free_hold_conversion_charges: DF.Currency
		gst_corpus_fund_and_monthly_maintenance_charges__18: DF.Currency
		gst_number: DF.Autocomplete | None
		h1_bid_amount: DF.Currency
		houseplot_no: DF.Autocomplete | None
		ifsc_code: DF.Autocomplete | None
		interest_on_application_money: DF.Currency
		is_gst_applicable: DF.Literal["YES", "NO"]
		is_joint_applicant: DF.Autocomplete | None
		joint_applicant_name: DF.Autocomplete | None
		less_subsidy_rebate_if_any: DF.Currency
		less_tds_us_194_1a_to_be_deposited_directly_by_allottee__18: DF.Currency
		locality: DF.Autocomplete | None
		martial_status: DF.Autocomplete | None
		misc_charges: DF.Currency
		mobile_no: DF.Autocomplete | None
		monthly_maintenance_charge__rs_15_per_sq_ft_for_12_months: DF.Currency
		mother_name: DF.Autocomplete | None
		nationality: DF.Autocomplete | None
		net_due_amount: DF.Currency
		net_less: DF.Currency
		pan_number: DF.Autocomplete | None
		payment_status: DF.Literal["Unpaid", "Paid", "Partially Paid"]
		payment_table: DF.Table[DLPaymentTable]
		physically_handicapped: DF.Autocomplete | None
		pincode: DF.Autocomplete | None
		plinth_area_sqm: DF.Autocomplete | None
		pocket: DF.Autocomplete | None
		processing_fees: DF.Currency
		property_id: DF.Autocomplete | None
		region: DF.Autocomplete | None
		reserved_price: DF.Currency
		response_date_and_time: DF.Datetime | None
		scheme_name: DF.Autocomplete | None
		sector: DF.Autocomplete | None
		state: DF.Autocomplete | None
		streetroad: DF.Autocomplete | None
		tds: DF.Currency
		total_disposal_cost: DF.Currency
		total_excluding_gst: DF.Currency
		townvillage: DF.Autocomplete | None
		water_connection_charges: DF.Currency
	# end: auto-generated types
	pass


def validate_mobile_no_value(mobile_no):
	if not mobile_no:
		frappe.throw("Mobile number is required")

	mobile_no = str(mobile_no).strip()

	if not frappe.utils.re.match(r"^[6-9]\d{9}$", mobile_no):
		frappe.throw("Invalid Mobile Number. Enter a valid 10-digit Indian mobile number")


# @frappe.whitelist()
# def add_awaas_dl(details):
#     status = "000"
#     retMessage = "Successfully Saved the Awaas DL Details"
#     #retMessage=http://34.100.217.2/awaas-registration-fee/awaas-regfee-00097
#     try:
#         awaas_details = frappe.new_doc("Awaas Demand Letter")
#         awaas_details.update(details)
#         awaas_details.insert(ignore_permissions=True)

#         mobile_no = details.get("mobile_no")
#         pan_no =  details.get("pan_number")
#         gst_no = details.get("gst_number")

#         validate_mobile_no_value(mobile_no)

#         if pan_no:
#             if not is_valid_pan(pan_no):
#                 return{"status": "101","retMessage": "PAN number is Invalid"}

#         if gst_no:
#             validate_gstin(gst_no)

#     except frappe.ValidationError:
#         #  GST / PAN /Aadhaar no / mobile validation errors go to the client
#          raise

#     except Exception:
#         status = "100"
#         retMessage = "Unable to Create Awaas DL"

#     if status == "000":
#     	retMessage = "http://34.100.217.2/"+awaas_details.doctype+"/"+awaas_details.docname

#     return {"status":status,"message":retMessage}


@frappe.whitelist()
def add_awaas_dl(details):
	status = "000"
	retMessage = "Successfully Saved the Awaas DL Details"

	try:
		file_number = details.get("file_number")
		mobile_no = details.get("mobile_no")
		pan_no = details.get("pan_no")
		gst_no = details.get("gst_number")

		# Validations
		validate_mobile_no_value(mobile_no)

		if pan_no and not is_valid_pan(pan_no):
			return {"status": "101", "retMessage": "PAN number is Invalid"}

		if gst_no:
			validate_gstin(gst_no)

		if not file_number:
			frappe.throw("File No is required")

		# Check if document already exists
		existing_doc_name = frappe.db.exists("Awaas Demand Letter", {"file_number": file_number})
		Awaas_Demand_Letter = None
		if existing_doc_name:
			Awaas_Demand_Letter = frappe.get_doc("Awaas Demand Letter", existing_doc_name)

			if Awaas_Demand_Letter.payment_status == "Paid":
				return {"status": "110", "message": "Already Payment is Received"}

			Awaas_Demand_Letter.update(details)
			Awaas_Demand_Letter.save(ignore_permissions=True)
		else:
			# Create new
			Awaas_Demand_Letter = frappe.new_doc("Awaas Demand Letter")
			Awaas_Demand_Letter.update(details)
			Awaas_Demand_Letter.insert(ignore_permissions=True)

		frappe.db.commit()
		frappe.log_error("Letter created/updated", Awaas_Demand_Letter.name)

	except frappe.ValidationError:
		raise
	except Exception:
		status = "100"
		retMessage = "Unable to Create Awaas DL"
		frappe.log_error(frappe.get_traceback(), "Awaas DL Creation Failed")
		return {"status": status, "message": retMessage}
	if existing_doc_name:
		status == "000"
		# base_url = str(frappe.conf.get("dda_payment_url"))
		doc_type_name = Awaas_Demand_Letter.doctype.replace(" ", "%20")
		retMessage = str(
			frappe.utils.get_url()
			+ "/makepayment?doctype="
			+ doc_type_name
			+ "&docname="
			+ Awaas_Demand_Letter.name
		)

	return {"status": status, "message": retMessage}






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