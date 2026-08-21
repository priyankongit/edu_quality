import base64
import os
from collections import Counter, defaultdict

import frappe
import pandas as pd
from frappe import _


@frappe.whitelist()
def get_student_data(student):
	from edu_quality.common.utils.access import assert_student_access

	assert_student_access(student)
	student = frappe.get_doc("Student", student)
	data = student.as_dict()
	data["guardians"] = []
	for g in student.guardians:
		guardian_doc = frappe.get_doc("Guardian", g.guardian).as_dict()
		guardian_doc["relation"] = g.relation
		guardian_doc["guardian"] = g.guardian
		data["guardians"].append(guardian_doc)

	return data


@frappe.whitelist()
def get_student_details(program):
	from edu_quality.common.utils.access import get_user_schools

	schools = get_user_schools()
	if schools is not None and frappe.get_value("Program", program, "school") not in schools:
		frappe.throw(_("You are not permitted to access this record."), frappe.PermissionError)

	try:
		academic_year = frappe.get_value("Academic Year", {"custom_current_academic_year": 1}, "name")
		batches = set(
			frappe.get_all(
				"Student Group",
				{"program": program, "academic_year": academic_year},
				pluck="batch",
			)
		)
		# get all students in the program
		students = get_students(program, academic_year)

		# Group students by batch, house, and gender
		student_groups = defaultdict(lambda: defaultdict(list))
		for student in students:
			student_groups[student.batch][student.school_house, student.gender].append(student)

		division_data = {}

		for batch in batches:
			# Get student groups for this batch
			batch_groups = student_groups[batch]

			# Create a list of groups in the order we want to assign them to divisions
			house_lists = [
				batch_groups[house, gender]
				for house in ["Red", "Blue", "Green", "Yellow"]
				for gender in ["Female", "Male"]
			]

			divs = frappe.get_all(
				"Student Group",
				filters={
					"batch": batch,
					"program": program,
					"academic_year": academic_year,
					"disabled": 0,
				},
				fields=["name", "max_strength"],
				order_by="max_strength",
			)
			for div in divs:
				student_data = []
				for i in range(div.max_strength):
					house_list = house_lists[i % len(house_lists)]
					if not house_list:
						continue
					student_data.append(house_list.pop(0))

				gender_counts = Counter(s.gender for s in student_data)
				house_counts = Counter(s.school_house for s in student_data)
				division_data.setdefault(div.name, {}).update(
					{
						"students": student_data,
						"no_of_students": len(student_data),
						"boys": gender_counts["Male"],
						"girls": gender_counts["Female"],
						"yellow": house_counts["Yellow"],
						"green": house_counts["Green"],
						"red": house_counts["Red"],
						"blue": house_counts["Blue"],
					}
				)

		# Cache the data for 5 minutes to use if clicked okay in the dialog
		rs = frappe.cache()
		data = frappe.json.dumps(division_data)
		rs.set(program, data, 300)
		return division_data
	except Exception as e:
		frappe.log_error(
			"Error While Getting Student data During Division Shuffle",
			frappe.get_traceback(),
		)
		return False


def get_students(program, academic_year):
	return frappe.db.sql(
		"""
        SELECT s.name, s.first_name, s.gender, p.name as pname, p.school_house, d.batch
        FROM `tabStudent` as s
        LEFT JOIN `tabProgram Enrollment` as p
        ON s.name = p.student
        LEFT JOIN `tabStudent Group` as d
        ON p.student_group = d.name
        WHERE p.program = %s and p.academic_year = %s and s.student_status != 'Cancelled'
        GROUP BY d.batch, p.school_house, s.gender, s.name
        ORDER BY d.batch, p.school_house, s.gender, RAND()
        """,
		(program, academic_year),
		as_dict=True,
	)


@frappe.whitelist()
def shuffle_division_data(program):
	try:
		data = frappe.cache().get(program)
		division_data = frappe.json.loads(data)
		for division, details in division_data.items():
			students = details.get("students")
			div = frappe.get_doc("Student Group", division)
			div.students = []
			for student in students:
				div.append(
					"students",
					{
						"student": student.get("name"),
					},
				)
				# update student details after shuffling
				update_student_details(student, div)
			div.save()
		return "Division shuffled successfully"
	except Exception as e:
		frappe.log_error("Shuffle Division Data Error", frappe.get_traceback())
		return False


def update_student_details(student, division):
	"""
	student: dict
	(name, first_name, gender, house, program_enrollment(pname))
	"""
	# update student group and tiffin rack no in program enrollment
	frappe.db.set_value(
		"Program Enrollment",
		student.get("pname"),
		{"student_group": division.name, "tiffin_rack_no": ""},
	)
	# update student group in student
	frappe.db.set_value("Student", student.get("name"), {"custom_division": division.student_group_name})


@frappe.whitelist()
def export_student_details(program):
	try:
		data = frappe.cache().get(program)
		division_data = frappe.json.loads(data)
		academic_year = frappe.get_value("Academic Year", {"custom_current_academic_year": 1}, "name")
		columns = [
			"Previous Division",
			"New Division",
			"Name",
			"First Name",
			"Gender",
			"House",
			"Batch",
		]
		new_data = []

		for division, details in division_data.items():
			students = details.get("students")
			for student in students:
				prev_division = frappe.get_value(
					"Program Enrollment",
					{"student": student.get("name"), "academic_year": academic_year},
					"student_group",
				)
				new_data.append(
					[
						prev_division,
						division,
						student.get("name"),
						student.get("first_name"),
						student.get("gender"),
						student.get("school_house"),
						student.get("batch"),
					]
				)

		division_data = {columns[i]: [row[i] for row in new_data] for i in range(len(columns))}
		# Convert the data to a pandas DataFrame
		df = pd.DataFrame(division_data)
		public_path = frappe.get_site_path("public", "files")
		filename = f"Student Details - {program}.csv"
		filepath = os.path.join(public_path, filename)

		df.to_csv(filepath, index=False)
		with open(filepath, "rb") as file:
			filecontent = file.read()

		response = {
			"filename": filename,
			"filecontent": base64.b64encode(filecontent).decode(),
		}

		return response
	except:
		frappe.log_error("Error While Exporting Student Details", frappe.get_traceback())
		return False
