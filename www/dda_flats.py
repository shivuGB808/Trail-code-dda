import random
import string

import frappe


def get_context(context):
	captcha = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
	frappe.session["captcha"] = captcha
	context.captcha = captcha

	context.no_cache = 1

	context.zones = frappe.get_all(
		"Awaas Zones", fields=["name", "zone_code", "zone_id", "awaas_zone_name"], order_by="name"
	)

	context.schemes = frappe.get_all("DDA Awaas Scheme", fields=["scheme_name", "scheme_id"], order_by="name")

	context.locality = frappe.get_list(
		"DDA Awaas Locality", fields=["locality_name", "locality_id", "zone"], order_by="creation desc"
	)

	context.receipt = frappe.get_list(
		"Receipt Types", fields=["receipt_type", "receipt_code"], filters={"type": "Housing"}
	)
	context.banks = frappe.get_all(
        "DDA Awaas Banks", fields=["bank", "ifsc_code"], order_by="creation desc"
    )






@frappe.whitelist(allow_guest=True)
def get_localities(zone):
	return frappe.get_all(
		"DDA Awaas Locality",
		filters={"zone": zone},
		fields=["locality_name", "locality_id"],
		order_by="locality_name",
	)


@frappe.whitelist(allow_guest=True)
def get_locality_id(locality_name):
	return frappe.db.get_value("DDA Awaas Locality", {"locality_name": locality_name}, "locality_id")

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

    doc = doc[0]
    full_name = " ".join(
        filter(None, [
            doc.get("applicant_first_name"),
            doc.get("applicant_middle_name"),
            doc.get("applicant_last_name")
        ])
    )
    address_line_1 = " ".join(
        filter(None, [
            doc.get("houseplot_no"),
            doc.get("streetroad")
        ])
    )
    address_line_2 = " ".join(
        filter(None, [
            doc.get("arealocality"),
            doc.get("townvillage")
        ])
    )
    address_line_3 = " ".join(
        filter(None, [
            doc.get("district"),
            doc.get("state")
        ])
    )

    doc["name_of_the_allottee"] = full_name
    doc["address_line_1"] = address_line_1
    doc["address_line_2"] = address_line_2
    doc["address_line_3"] = address_line_3

    return doc
@frappe.whitelist(allow_guest=True)
def validate_captcha(captcha):
	if captcha != frappe.session.get("captcha"):
		frappe.throw("Invalid Captcha")
	return True
