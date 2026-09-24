import frappe
from frappe.sessions import get_csrf_token
from frappe.utils import escape_html

from edu_quality.api.school_app import get_branding_dict

no_cache = 1


def get_context(context):
	branding = get_branding_dict()
	icon = escape_html(branding["icon"])
	short_name = escape_html(branding["short_name"])
	primary = escape_html(branding["colors"]["primary"])

	head = [
		f'<meta name="theme-color" content="{primary}">',
		f'<meta name="apple-mobile-web-app-title" content="{short_name}">',
		'<link rel="manifest" href="/api/method/edu_quality.api.school_app.manifest">',
	]
	if icon:
		head += [
			f'<link rel="icon" href="{icon}">',
			f'<link rel="apple-touch-icon" href="{icon}">',
		]

	boot = {
		"branding": branding,
		"csrf_token": get_csrf_token() if frappe.session.user != "Guest" else "",
		"user": frappe.session.user,
	}
	context.title = escape_html(branding["app_name"])
	context.head_html = "\n\t\t".join(head)
	# Escape "</" so admin-entered text can never close the <script> tag.
	context.boot_json = frappe.as_json(boot, indent=None).replace("</", "<\\/")
