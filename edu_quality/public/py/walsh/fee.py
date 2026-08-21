import frappe

from edu_quality.edu_quality.server_scripts.utils import (
	current_academic_year,
	next_academic_year,
)


@frappe.whitelist()
def get_academic_year_with_fees(student):
	from edu_quality.common.utils.access import assert_student_access

	assert_student_access(student)
	fees = frappe.db.get_all("Fees", filters={"docstatus": 1, "student": student}, fields=["academic_year"])
	fa = frappe.db.get_all(
		"Fee Advance",
		filters={"docstatus": 1, "student": student},
		fields=["academic_year"],
	)
	fees = set([i.get("academic_year") for i in fees])
	fa = set([i.get("academic_year") for i in fa])

	return fees | fa


@frappe.whitelist()
def get_student_fee_schedule(student):
	from edu_quality.common.utils.access import assert_student_access

	assert_student_access(student)
	academic_year = current_academic_year()
	next_acad_year = next_academic_year()
	fee_advance = (
		frappe.get_all(
			"Fee Advance",
			filters={"student": student, "academic_year": next_acad_year},
			fields=["payment_term", "amount as payment_amount", "due_date"],
		)
		or []
	)

	fee_qb = frappe.qb.DocType("Fees")
	p_schedule_qb = frappe.qb.DocType("Payment Schedule")

	enrollment = frappe.db.get_value(
		"Program Enrollment",
		{"academic_year": academic_year, "docstatus": 1, "student": student},
		"name",
	)

	if not enrollment:
		return fee_advance

	payment_term_query = (
		frappe.qb.from_(fee_qb)
		.inner_join(p_schedule_qb)
		.on((fee_qb.name == p_schedule_qb.parent) & (fee_qb.program_enrollment == enrollment))
		.orderby(p_schedule_qb.payment_term)
		.select(
			p_schedule_qb.payment_term,
			p_schedule_qb.due_date,
			p_schedule_qb.payment_amount,
		)
	)
	fee_schedule = payment_term_query.run(as_dict=True)

	return fee_advance + fee_schedule


def get_fees(student, acad_year):
	stud_qb = frappe.qb.DocType("Student")
	fee_qb = frappe.qb.DocType("Fees")
	pay_l_qb = frappe.qb.DocType("Payment Request")
	p_schedule_qb = frappe.qb.DocType("Payment Schedule")
	academic_year = acad_year or current_academic_year()

	all_fees = (
		frappe.qb.from_(stud_qb)
		.where(stud_qb.name == student)
		.inner_join(fee_qb)
		.on(fee_qb.student == stud_qb.name)
		.where((fee_qb.docstatus == 1) & (fee_qb.academic_year == academic_year))
		.inner_join(pay_l_qb)
		.on((pay_l_qb.reference_name == fee_qb.name) & (pay_l_qb.docstatus == 1))
		.left_join(p_schedule_qb)
		.on((p_schedule_qb.payment_term == pay_l_qb.payment_term) & (p_schedule_qb.parent == fee_qb.name))
	).select(
		pay_l_qb.status,
		pay_l_qb.grand_total,
		pay_l_qb.payment_term,
		pay_l_qb.payment_hash,
		pay_l_qb.payment_url,
		p_schedule_qb.payment_amount,
		p_schedule_qb.due_date,
	)

	return all_fees.run(as_dict=True)


def get_adv_fees(student, acad_year):
	stud_qb = frappe.qb.DocType("Student")

	pay_l_qb = frappe.qb.DocType("Payment Request")
	fee_adv_qb = frappe.qb.DocType("Fee Advance")
	academic_year = acad_year or current_academic_year()

	all_adv_fees = (
		(
			frappe.qb.from_(stud_qb)
			.where(stud_qb.name == student)
			.inner_join(fee_adv_qb)
			.on(fee_adv_qb.student == stud_qb.name)
			.where((fee_adv_qb.docstatus == 1) & (fee_adv_qb.academic_year == academic_year))
			.inner_join(pay_l_qb)
			.on((pay_l_qb.reference_name == fee_adv_qb.name) & (pay_l_qb.docstatus == 1))
		)
		.orderby(fee_adv_qb.payment_term)
		.select(
			pay_l_qb.status,
			pay_l_qb.grand_total,
			pay_l_qb.grand_total.as_("payment_amount"),
			pay_l_qb.payment_term,
			pay_l_qb.payment_hash,
			pay_l_qb.payment_url,
			# pay_l_qb.payment_amount,
			fee_adv_qb.due_date,
		)
	)

	return all_adv_fees.run(as_dict=True)


@frappe.whitelist()
def get_student_fees(student, academic_year):
	from edu_quality.common.utils.access import assert_student_access

	assert_student_access(student)
	fees = get_fees(student, academic_year)
	adv_fees = get_adv_fees(student, academic_year)

	combined_fees = []

	for fee in adv_fees:
		combined_fees.append({**fee, "type": "advance"})

	for fee in fees:
		combined_fees.append({**fee, "type": "fees"})

	return combined_fees
