// Copyright (c) 2026, BEL and contributors
// For license information, please see license.txt

frappe.ui.form.on("Challan", {
	refresh(frm) {
		if (frm.is_new()) {
			frm.add_child("type_of_payments");
			frm.refresh_field("type_of_payments");
		}

		if (!frm.is_new()) {
			frm.toggle_display("generate_challan", false);
			frm.toggle_display("pay_now", false);
			frm.toggle_display("cancel", false);
		}
		toggle_payment_buttons(frm);
	},

	mode_of_payment(frm) {
		toggle_payment_buttons(frm);
	},
});

function toggle_payment_buttons(frm) {
	frm.toggle_display("generate_challan", false);

	// Show based on mode of payment
	if (frm.doc.mode_of_payment == "Online") {
		frm.toggle_display("pay_now", true);
	} else {
		frm.toggle_display("pay_now", false);
		frm.toggle_display("generate_challan", true);
	}
}
