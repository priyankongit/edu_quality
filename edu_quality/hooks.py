from . import __version__ as app_version

app_name = "edu_quality"
app_title = "Edu Quality"
app_publisher = "Hybrowlabs Technologies"
app_description = "Edu Quality"
app_email = "contact@hybrowlabs.com"
app_license = "AGPL-3.0"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/edu_quality/css/edu_quality.css"
app_include_js = [
	"/assets/edu_quality/js/exportTool.js" "/assets/edu_quality/js/carnivalEvent.js",
	# "export_tool.bundle.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/edu_quality/css/edu_quality.css"
# web_include_js = "/assets/edu_quality/js/edu_quality.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "edu_quality/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Payment Entry": "public/js/payment_entry.js",
	"Student Applicant": "public/js/application.js",
	"Reference Number Settings": "public/js/reference_number.js",
	"Fees": "public/js/fees.js",
	"Lead": "public/js/lead.js",
	"Fee Schedule": "public/js/fee_schedule.js",
	"Student": "public/js/student.js",
	"Item": "public/js/item.js",
	"Purchase Order": "public/js/purchase_order.js",
	"Purchase Receipt": "public/js/purchase_receipt.js",
	"Topic": "public/js/topic.js",
	"Instructor": "public/js/instructor.js",
	"Payment Request": "public/js/payment_request.js",
	"Program Enrollment": "public/js/program_enrollment.js",
	"Program": "public/js/program.js",
	"Employee": "public/js/employee.js",
	"Assessment Plan": "public/js/assessment_plan.js",
	"Assessment Group": "public/js/assessment_group.js",
	"Event": "public/js/event.js",
	"Company": "public/js/company.js",
	"School": "public/js/school.js",
}
doctype_list_js = {
	"Student Applicant": "public/js/list/student_applicant_list.js",
	"Guardian": "public/js/list/guardian_list.js",
	"Lead": "public/js/list/lead_list.js",
	"Program Enrollment": "public/js/list/program_enrollment_list.js",
	"Student": "public/js/list/student_list.js",
	"Student ID Card": "public/js/list/student_id_card.js",
	"Fees": "public/js/list/fees_list.js",
	"Purchase Order": "public/js/list/purchase_order_list.js",
	"Assessment Group": "public/js/list/assessment_group_list.js",
	"Descriptive Exam Paper": "public/js/list/descriptive_paper_list.js",
	"Descriptive Question": "public/js/list/descriptive_ques_list.js",
	"Carnival Event": [
		# "public/js/list/list_view.js",
		"public/js/list/carnival_event_list.js",
	],
	"Class Photo": [
		# "public/js/list/list_view.js",
		"public/js/list/class_photo_list.js",
	],
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
	"methods": [
		"edu_quality.overrides_hooks.purchase_order",
		"edu_quality.public.py.utils",
	],
	# "filters": "edu_quality.utils.jinja_filters"
}

# Installation
# ------------

# before_install = "edu_quality.install.before_install"
after_install = "edu_quality.common.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "edu_quality.uninstall.before_uninstall"
after_uninstall = "edu_quality.common.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "edu_quality.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Contact": "edu_quality.permissions.contacts.contact_query",
	"Purchase Order": "edu_quality.permissions.purchase_orders.purchase_query",
	"Student": "edu_quality.permissions.students.student_query",
}
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Student Group": "edu_quality.edu_quality.overrides.student_group.CustomStudentGroup",
	"Employee": "edu_quality.edu_quality.overrides.employee.customEmployee",
	"Program": "edu_quality.edu_quality.overrides.program.customProgram",
	"Journal Entry": "edu_quality.edu_quality.overrides.journal_entry.customJournalEntry",
	"Payment Request": "edu_quality.overrides.CustomPaymentRequest",
	"Fee Schedule": "edu_quality.public.py.fee_schedule.CustomFeeSchedule",
	"Program Enrollment": "edu_quality.edu_quality.overrides.program_enrollment.CustomProgramEnrollment",
	"Fees": "edu_quality.edu_quality.overrides.fees.CustomFees",
	"Student": "edu_quality.edu_quality.overrides.student.CustomStudent",
	"Payment Entry": "edu_quality.edu_quality.overrides.payment_entry.CustomPaymentEntry",
	"Lead": "edu_quality.public.py.lead.CustomLead",
	"Instructor": "edu_quality.edu_quality.overrides.instructor.CustomInstructor",
	"HD Ticket": "edu_quality.edu_quality.overrides.hd_ticket.CustomHDTicket",
	"Communication": "edu_quality.edu_quality.overrides.communication.CustomCommunication",
	"Email Template": "edu_quality.edu_quality.overrides.email_templates.CustomEmailTemplate",
	"Assessment Group": "edu_quality.edu_quality.overrides.assessment_group.CustomAssessmentGroup",
	"Assessment Plan": "edu_quality.edu_quality.overrides.assessment_plan.CustomAssessmentPlan",
	"Assessment Result": "edu_quality.edu_quality.overrides.assessment_result.CustomAssessmentResult",
	"Event": "edu_quality.edu_quality.overrides.event.CustomEvent",
	"Company": "edu_quality.edu_quality.overrides.company.CustomCompany",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Guardian": {
		"before_insert": "edu_quality.edu_quality.server_scripts.guardian.before_insert",
		"after_insert": "edu_quality.edu_quality.server_scripts.guardian.after_insert",
		"on_update": "edu_quality.edu_quality.server_scripts.guardian.on_update",
	},
	"Student Applicant": {
		"on_update": "edu_quality.edu_quality.server_scripts.student_applicant.on_update",
		"before_save": "edu_quality.public.py.application.before_save",
		"after_insert": "edu_quality.edu_quality.server_scripts.student_applicant.after_insert",
		"autoname": "edu_quality.public.py.application.autoname",
	},
	"Program Enrollment": {
		"on_submit": [
			"edu_quality.public.py.fee.create_fees",
			"edu_quality.public.py.fee.collect_birthday_details_on_submit",
		],
		"before_insert": "edu_quality.public.py.fee.sync_student_data",
		"after_insert": [
			"edu_quality.public.py.fee.append_program_enrollment",
			"edu_quality.public.py.fee.create_id_card",
			"edu_quality.public.py.fee.create_birthday_card",
		],
		"on_trash": "edu_quality.public.py.fee.remove_program_enrollment",
		"on_cancel": "edu_quality.edu_quality.server_scripts.program_enrollment.on_cancel",
	},
	"Contact": {"before_validate": "edu_quality.overrides_hooks.contact.before_validate"},
	"Fees": {
		"after_insert": "edu_quality.public.py.fee.after_insert",
		"on_submit": "edu_quality.public.py.fee.on_submit",
		"before_submit": "edu_quality.public.py.fee.before_submit",
		"before_save": "edu_quality.edu_quality.overrides.fees.before_save",
		"on_update_after_submit": "edu_quality.public.py.fee.on_update",
	},
	"Payment Request": {
		"before_save": "edu_quality.public.py.payment_request.before_save",
		"on_submit": "edu_quality.public.py.payment_request.on_submit",
	},
	"Student": {
		"after_insert": "edu_quality.public.py.student.after_insert",
		"before_save": "edu_quality.public.py.student.before_save",
	},
	"Payment Entry": {"validate": "edu_quality.edu_quality.server_scripts.payment_entry.validate"},
	"Item": {
		"autoname": "edu_quality.overrides_hooks.item.autoname",
		"before_insert": "edu_quality.overrides_hooks.item.before_insert",
		"after_delete": "edu_quality.overrides_hooks.item.after_delete",
		"on_update": "edu_quality.overrides_hooks.item.on_update",
	},
	"Program": {"validate": "edu_quality.public.py.program.validate"},
	"Topic": {
		"autoname": "edu_quality.overrides_hooks.topic.autoname",
		"after_insert": "edu_quality.overrides_hooks.topic.after_insert",
	},
	"Purchase Order": {
		"before_validate": "edu_quality.overrides_hooks.purchase_order.before_validate",
		"on_submit": [
			"edu_quality.edu_quality.server_scripts.purchase_order.on_submit",
			"edu_quality.edu_quality.server_scripts.purchase_order.mark_id_card_sent_to_print",
		],
	},
	# "Instructor": {
	#     "after_insert": "edu_quality.overrides_hooks.instructor.after_insert",
	#     "after_delete": "edu_quality.overrides_hooks.instructor.after_delete",
	# },
	"Purchase Receipt": {
		"before_save": "edu_quality.overrides_hooks.purchase_receipt.before_save",
		"before_validate": "edu_quality.overrides_hooks.purchase_order.before_validate",
	},
	"Employee": {
		"before_save": "edu_quality.edu_quality.server_scripts.employee.before_save",
		"after_insert": "edu_quality.edu_quality.server_scripts.employee.after_insert",
		"before_insert": "edu_quality.edu_quality.server_scripts.employee.before_insert",
		"on_update": "edu_quality.edu_quality.server_scripts.employee.on_update",
	},
	"Student Group": {
		# "on_update": "edu_quality.overrides_hooks.student_group.on_update",
		"before_save": "edu_quality.overrides_hooks.student_group.before_save",
	},
}

# Scheduled Tasks
# ---------------
scheduler_events = {
	"all": [
		"edu_quality.tasks.sync_student_data_from_program_enrollment",
		"edu_quality.api.student_application.get_and_schedule_pending_walkouts",
		"edu_quality.overrides_hooks.item.upload_all_imported_to_drive",
	],
	"cron": {
		"0 19 * * *": ["edu_quality.tasks.send_bulk_notification_cmap_to_guardian"],
		"0 6 * * *": [
			"edu_quality.tasks.schedule_birthday_greeting",
			"edu_quality.tasks.event_reminder",
		],
		"* * * * *": [
			"edu_quality.cmap_jobs.send_ptm_notifications_to_students",
			"edu_quality.cmap_jobs.notify_teacher_before_one_hour_job",
		],
	},
	"daily": [
		"edu_quality.tasks.time_based",
		"edu_quality.tasks.create_payment_request_before_due_date",
		"edu_quality.tasks.create_payment_request_before_due_date_fee_advance",
		# "edu_quality.tasks.update_academic_year",
	],
}
# scheduler_events = {
# 	"all": [
# 		"edu_quality.tasks.all"
# 	],
# 	"daily": [
# 		"edu_quality.tasks.daily"
# 	],
# 	"hourly": [
# 		"edu_quality.tasks.hourly"
# 	],
# 	"weekly": [
# 		"edu_quality.tasks.weekly"
# 	],
# 	"monthly": [
# 		"edu_quality.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "edu_quality.edu_quality.unit_tests.before_tests.setup_master_data"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "edu_quality.event.get_events"
# }

override_whitelisted_methods = {
	"helpdesk.helpdesk.doctype.hd_ticket.api.get_one": "edu_quality.edu_quality.server_scripts.hd_ticket.get_one"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "edu_quality.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
auto_cancel_exempted_doctypes = ["Journal Entry"]


# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["edu_quality.utils.before_request"]
# after_request = ["edu_quality.utils.after_request"]

# Job Events
# ----------
# before_job = ["edu_quality.utils.before_job"]
# after_job = ["edu_quality.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"edu_quality.auth.validate"
# ]

fixtures = [{"dt": "Custom DocPerm"}]


after_migrate = [
	"edu_quality.common.install.create_default_roles",
	"edu_quality.public.py.utils.migrate",
	"edu_quality.edu_quality.server_scripts.after_migrate.after_migrate",
]

website_route_rules = [
	{"from_route": "/walsh/<path:app_path>", "to_route": "walsh"},
	{"from_route": "/ui/<path:app_path>", "to_route": "ui"},
	{"from_route": "/school/<path:app_path>", "to_route": "school"},
]


page_renderer = [
	"edu_quality.edu_quality.page_renderers.web_form.WebFormPage",
]
