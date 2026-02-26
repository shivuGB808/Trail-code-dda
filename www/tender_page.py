import frappe
from frappe.utils import now_datetime


def get_context(context):
	# Fetch all records from the Doctype
	records = frappe.get_all(
		"Tender",
		filters={"date_and_time_of_last_submission_of_emd": (">", now_datetime())},
		fields=[
			"name",
			"tenderorder_ref_no",
			"name_of_work",
			"zone",
			"division",
			"date_of_opening_of_tender_with_time",
			"date_and_time_of_last_submission_of_emd",
			"mode_of_tender",
			"emd_amount",
		],
	)

	# Pass to context
	context.Tender = records
