// function payNow() {
//     const payment_name = "{{ doc.name }}";  // awaas-regfee-00097

//     if (!payment_name) {
//         frappe.msgprint("Payment record not found");
//         return;
//     }

//     // Call backend python method
//     frappe.call({
//         method: "dda_ifmis.dda_payments.api.make_payment",
//         args: {
//             payment_name: payment_name
//         },
//         freeze: true,
//         callback: function (r) {
//             if (r.message && r.message.payment_url) {
//                 window.location.href = r.message.payment_url;
//             } else {
//                 frappe.msgprint("Unable to initiate payment");
//             }
//         }
//     });
// }
