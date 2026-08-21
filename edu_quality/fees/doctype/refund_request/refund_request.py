# Copyright (c) 2023, Hybrowlabs Technologies and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.doctype.payment_request.payment_request import (
	get_dummy_message,
	get_gateway_details,
)
from erpnext.accounts.doctype.bank_account.bank_account import get_party_bank_account
from frappe.model.document import Document


class RefundRequest(Document):
	def before_save(self):
		amount = 0
		if frappe.db.exists("Fees", {"student": self.student_id, "outstanding_amount": "0"}):
			fee = frappe.get_doc("Fees", {"student": self.student_id, "outstanding_amount": "0"})
			self.security_deposit = []
			for component in fee.components:
				fee_name = component.fees_category
				if frappe.db.exists("Security Deposit", fee_name):
					self.append(
						"security_deposit",
						{
							"safety_deposit": fee_name,
							"amount": component.amount,
						},
					)

					amount += component.amount

		self.amount = amount
		if frappe.db.exists("Fees", {"student": self.student_id}):
			fee_list = frappe.get_list("Fees", {"student": self.student_id})
			for f in fee_list:
				fee = frappe.get_doc("Fees", f.name)
				if fee.outstanding_amount > 0:
					self.append(
						"pending_fees",
						{
							"fees": fee.name,
						},
					)

			if fee.outstanding_amount < self.amount:
				self.adjusted_amount = self.amount - fee.outstanding_amount
				frappe.db.set_value("Fees", fee.name, "outstanding_amount", 0)
		else:
			self.adjusted_amount = self.amount

		if self.approved == 1:
			fee = frappe.get_doc("Fees", {"student": self.student_id})
			if not frappe.db.exists(
				"Payment Request",
				{"reference_name": fee.name, "payment_request_type": "Outward"},
			):
				transaction_id = frappe.db.get_value(
					"Payment Request",
					{"reference_name": self.student_id, "status": "Paid"},
					"transaction_id",
				)
				phone = frappe.db.get_value("Student", fee.student, "student_mobile_number")
				email = frappe.db.get_value("Student", fee.student, "student_email_id")
				create_payment_request(
					dt=fee.doctype,
					dn=fee.name,
					party_type="Student",
					party=fee.student,
					recipient_id=email,
					payment_request_type="Outward",
					grand_total=self.adjusted_amount,
					amount=self.amount,
					transaction_id=transaction_id,
					phone=phone,
				)


def create_payment_request(**args):
	# Create a new Payment Request document
	args = frappe._dict(args)

	ref_doc = frappe.get_doc(args.dt, args.dn)
	gateway_account = get_gateway_details(args)

	bank_account = (
		get_party_bank_account(args.get("party_type"), args.get("party")) if args.get("party_type") else ""
	)

	pr = frappe.new_doc("Payment Request")
	pr.update(
		{
			"payment_gateway_account": gateway_account.get("name"),
			"payment_gateway": gateway_account.get("payment_gateway"),
			"payment_account": gateway_account.get("payment_account"),
			"payment_channel": gateway_account.get("payment_channel"),
			"payment_request_type": args.get("payment_request_type"),
			"currency": ref_doc.currency,
			"grand_total": args.grand_total,
			"mode_of_payment": args.mode_of_payment,
			"email_to": args.recipient_id or ref_doc.owner,
			"subject": frappe._("Payment Request for {0}").format(args.dn),
			"message": gateway_account.get("message") or get_dummy_message(ref_doc),
			"reference_doctype": args.dt,
			"reference_name": args.dn,
			"party_type": args.get("party_type") or "Customer",
			"party": args.get("party") or ref_doc.get("customer"),
			"bank_account": bank_account,
		}
	)
	# Save the Payment Request document
	pr.insert(ignore_permissions=True)
	easebuzz = frappe.get_doc("Easebuzz Settings")
	res = easebuzz.initiateRefund(
		{
			"txnid": args.transaction_id,
			"refund_amount": args.grand_total,
			"phone": args.phone,
			"email": args.recipient_id or ref_doc.owner,
			"amount": args.amount,
		}
	)
