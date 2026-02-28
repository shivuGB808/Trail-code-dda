import random
import string

import frappe


def get_context(context):
	captcha = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
	frappe.session["captcha"] = captcha
	context.captcha = captcha

	context.no_cache = 1

	context.depts = frappe.get_all("Department", fields=["name"], order_by="name")

	context.bhoomizones = frappe.get_all("Bhoomi Zone List", fields=["name","bhoomi_zone_name", "zone_code"], order_by="name")

	context.locality = frappe.get_list(
		"DDA Bhoomi Locality", fields=["locality_name", "locality_id", "zone"], order_by="creation desc"
	)

	context.receipt = frappe.get_list(
		"Receipt Types", fields=["receipt_type", "receipt_code"], filters={"type": "Land"}
	)


@frappe.whitelist(allow_guest=True)
def get_localities(zone):
	return frappe.get_all(
		"DDA Bhoomi Locality",
		filters={"zone": zone},
		fields=["locality_name", "locality_id"],
		order_by="locality_name",
	)


@frappe.whitelist(allow_guest=True)
def get_locality_id(locality_name):
	return frappe.db.get_value("DDA Bhoomi Loacality", {"locality_name": locality_name}, "locality_id")


@frappe.whitelist(allow_guest=True)
def validate_captcha(captcha):
	if captcha != frappe.session.get("captcha"):
		frappe.throw("Invalid Captcha")
	return True