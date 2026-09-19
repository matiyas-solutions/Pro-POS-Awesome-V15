# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    import frappe
except ModuleNotFoundError:  # pragma: no cover - frappe may not be installed during setup
    frappe = None

__version__ = "15.34.0"


def console(*data):
    if frappe:
        frappe.publish_realtime("toconsole", data, user=frappe.session.user)


try:
    from posawesome.posawesome.overrides.return_serial_batch import (
        apply_return_serial_batch_patch,
    )

    apply_return_serial_batch_patch()
except Exception:
    pass
