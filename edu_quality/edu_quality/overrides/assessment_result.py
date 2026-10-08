import education.education
import frappe
from education.education.api import get_assessment_details
from education.education.api import get_grade as inner_get_grade
from education.education.doctype.assessment_result.assessment_result import (
	AssessmentResult,
)
from frappe.query_builder import Order
from frappe.utils import flt
from pypika.analytics import Rank

from edu_quality.public.py.utils import extract_year_from_academic_year_name


class CustomAssessmentResult(AssessmentResult):
	def validate(self):
		# education.education.validate_student_belongs_to_group(
		#     self.student, self.student_group
		# )
		if not self.custom_is_descriptive:
			self.validate_maximum_score()

		if self.custom_scoring_type == "Marks":
			self.validate_grade()
			self.validate_processed_result()

		if self.custom_scoring_type == "Grades":
			self.duplicate_grades()

		self.validate_duplicate()

	def validate_duplicate(self):
		# Education uses get_list here, which fails for anyone without read access to every result —
		# e.g. teachers saving marks from the school app. The check itself isn't about permissions.
		existing = frappe.get_all(
			"Assessment Result",
			filters={
				"name": ("!=", self.name),
				"student": self.student,
				"assessment_plan": self.assessment_plan,
				"docstatus": ("!=", 2),
			},
			pluck="name",
			limit=1,
		)
		if existing:
			frappe.throw(
				frappe._("Assessment Result record {0} already exists.").format(
					frappe.utils.get_link_to_form("Assessment Result", existing[0])
				)
			)

	def validate_grade(self):
		self.total_score = 0.0
		if self.maximum_score:
			for d in self.details:
				d.grade = get_grade(
					self.grading_scale,
					(flt(d.score) / (d.maximum_score or 1)) * 100,
					d.score,
				)
				self.total_score += d.score
			self.grade = get_grade(
				self.grading_scale,
				(self.total_score / (self.maximum_score or 1)) * 100,
				self.total_score,
			)

	def calculate_scaled_maximum_score(self):
		total_scaled_max_score = 0
		for d in self.details:
			d.custom_scale = d.custom_scale or 1
			if d.maximum_score:
				total_scaled_max_score += d.maximum_score * d.custom_scale
		self.custom_scaled_maximum_score = total_scaled_max_score

	def duplicate_grades(self):
		if self.docstatus in [1, 2]:
			return
		for d in self.details:
			d.custom_processed_grade = d.grade

	def process_result(self):
		self.total_score = 0.0
		self.custom_total_processed_score = 0.0
		self.custom_scaled_maximum_score = 0.0
		for d in self.details:
			d.custom_scale = d.custom_scale or 1
			d.custom_processed_result = d.score * d.custom_scale
			d.custom_scaled_maximum_score = (d.maximum_score or 0) * d.custom_scale
			if d.maximum_score:
				d.custom_processed_grade = get_grade(
					self.grading_scale,
					(flt(d.custom_processed_result) / d.maximum_score) * 100,
					d.custom_processed_result,
				)
			else:
				d.custom_processed_grade = get_grade(
					self.grading_scale,
					flt(d.custom_processed_result),
					d.custom_processed_result,
				)
			self.total_score += d.score
			self.custom_total_processed_score += d.custom_processed_result
			self.custom_scaled_maximum_score += d.custom_scaled_maximum_score

		if self.maximum_score:
			self.custom_processed_grade = get_grade(
				self.grading_scale,
				(self.custom_total_processed_score / self.maximum_score) * 100,
				self.custom_total_processed_score,
			)
			self.grade = get_grade(
				self.grading_scale,
				(self.total_score / self.maximum_score) * 100,
				self.total_score,
			)

			self.custom_processed_percentage = (self.custom_total_processed_score / self.maximum_score) * 100

		else:
			self.custom_processed_grade = get_grade(
				self.grading_scale,
				self.custom_total_processed_score,
				self.custom_total_processed_score,
			)

			self.grade = get_grade(
				self.grading_scale,
				self.total_score,
				self.total_score,
			)

		return self

	def validate_processed_result(self):
		if self.docstatus in [1, 2]:
			return
		self.process_result()

	def calculate_ordering(self):
		assess_res_qb = frappe.qb.DocType("Assessment Result")
		subquery = (
			assess_res_qb.select(
				Rank()
				.over()
				.orderby(assess_res_qb.custom_total_processed_score, order=Order.desc)
				.as_("ranking"),
				assess_res_qb.name,
			)
			.where(
				(assess_res_qb.assessment_plan == self.assessment_plan)
				& (assess_res_qb.docstatus == 1)
				& (assess_res_qb.custom_scoring_type == "Marks")
			)
			.as_("ranked_table")
		)
		query = (
			frappe.qb.from_(assess_res_qb).inner_join(subquery).on(self.name == assess_res_qb.name)
		).select(subquery.ranking)

		data = query.run(as_dict=True)
		if data:
			self.custom_rank = data[0].get("ranking")
			return self.custom_rank
		else:
			None

	def before_submit(self, method=None):
		if self.custom_scoring_type == "Marks":
			self.process_result()
			assessment_group_doc = frappe.get_doc("Assessment Group", self.assessment_group)
			if (
				assessment_group_doc.custom_process_passing
				and self.custom_processed_percentage >= assessment_group_doc.custom_passing_percentage
			):
				self.custom_passed = 1

			self.calculate_ordering()


def get_grade(grading_scale, percentage, score):
	use_score_map = frappe.db.get_value("Grading Scale", grading_scale, "custom_use_score_mapping")

	if use_score_map:
		grading_scale_interval = frappe.db.get_value(
			"Grading Scale Interval",
			filters={"parent": grading_scale, "custom_score_mapping": score},
			fieldname="grade_code",
		)
		if not grading_scale_interval:
			return ""

		return grading_scale_interval or ""
	else:
		return inner_get_grade(grading_scale, percentage)
