"""Endpoints backing the /school progressive web app.

Branding comes from the School App Settings single so the same app can be deployed
for any school; nothing school-specific lives in code.
"""

import json

import frappe
from frappe.sessions import get_csrf_token
from frappe.utils import get_url
from werkzeug.wrappers import Response

from edu_quality.common.utils.access import ADMIN_ROLES

BRANDING_CACHE_KEY = "school_app_branding"

DEFAULT_BRANDING = {
	"app_name": "School App",
	"short_name": "School",
	"school_name": "",
	"tagline": "",
	"logo": "",
	"icon": "",
	"colors": {"primary": "#3346D3", "secondary": "#E8ECF8", "ink": "#111827"},
	"teacher_app_enabled": True,
}


def get_branding_dict():
	"""Public branding for the app shell. Safe to expose to guests."""
	cached = frappe.cache().get_value(BRANDING_CACHE_KEY)
	if cached:
		return cached

	branding = json.loads(json.dumps(DEFAULT_BRANDING))
	try:
		settings = frappe.get_cached_doc("School App Settings")
	except frappe.DoesNotExistError:
		settings = None

	if settings:
		app_name = settings.app_name or branding["app_name"]
		branding.update(
			{
				"app_name": app_name,
				"short_name": settings.short_name or app_name[:12],
				"school_name": settings.school_name or "",
				"tagline": settings.tagline or "",
				"logo": settings.logo or "",
				"icon": settings.app_icon or settings.logo or "",
				"teacher_app_enabled": bool(settings.enable_teacher_app),
			}
		)
		for key, field in (("primary", "primary_color"), ("secondary", "secondary_color"), ("ink", "ink_color")):
			if settings.get(field):
				branding["colors"][key] = settings.get(field)

	frappe.cache().set_value(BRANDING_CACHE_KEY, branding)
	return branding


def clear_branding_cache():
	frappe.cache().delete_value(BRANDING_CACHE_KEY)


@frappe.whitelist(allow_guest=True)
def get_branding():
	return get_branding_dict()


def _instructor_for(user):
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return None
	return frappe.db.get_value(
		"Instructor",
		{"employee": employee, "status": "Active"},
		["name", "instructor_name", "custom_school as school", "image"],
		as_dict=True,
	)


@frappe.whitelist(allow_guest=True)
def get_session():
	"""Who is signed in and which app experiences they get."""
	user = frappe.session.user
	if not user or user == "Guest":
		return {"user": "Guest", "personas": []}

	roles = set(frappe.get_roles(user))
	full_name, user_image = frappe.db.get_value("User", user, ["full_name", "user_image"])
	instructor = _instructor_for(user)

	personas = []
	if instructor:
		personas.append("teacher")
	if roles & ADMIN_ROLES:
		personas.append("admin")
	if frappe.db.exists("Guardian", {"user": user}):
		personas.append("guardian")
	if frappe.db.exists("Student", {"user": user}):
		personas.append("student")

	return {
		"user": user,
		"full_name": full_name or user,
		"user_image": (instructor and instructor.image) or user_image,
		"personas": personas,
		"instructor": instructor,
		"csrf_token": get_csrf_token(),
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def manifest():
	"""Web app manifest so the app can be added to a phone's home screen with the school's name and icon."""
	branding = get_branding_dict()
	icon = branding["icon"]
	icons = []
	if icon:
		icon_url = get_url(icon)
		icons = [
			{"src": icon_url, "sizes": "192x192", "type": "image/png", "purpose": "any"},
			{"src": icon_url, "sizes": "512x512", "type": "image/png", "purpose": "any"},
		]

	data = {
		"name": branding["app_name"],
		"short_name": branding["short_name"],
		"description": branding["tagline"] or branding["school_name"],
		"id": "/school/",
		"start_url": "/school/",
		"scope": "/school/",
		"display": "standalone",
		"orientation": "portrait",
		"background_color": "#FFFFFF",
		"theme_color": branding["colors"]["primary"],
		"icons": icons,
	}
	response = Response(json.dumps(data), mimetype="application/manifest+json")
	response.headers["Cache-Control"] = "no-cache"
	return response
