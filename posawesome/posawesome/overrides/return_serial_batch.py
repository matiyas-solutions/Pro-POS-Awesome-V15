# Copyright (c) 2026, POS Awesome and contributors
# For license information, please see license.txt

from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import cint


_PATCH_APPLIED = False


def apply_return_serial_batch_patch():
    """Patch ERPNext's filter_serial_batches to respect scanned/requested return serials.

    Standard ERPNext's filter_serial_batches blindly sorts and truncates available
    serials (sorted(available_serial_nos[0 : qty])) regardless of which serial
    numbers the customer returned. This patch ensures that if row.serial_no
    (or row.serial_no_selected) contains specific serials belonging to the original
    invoice, those exact serials are allocated to the return bundle.
    """
    global _PATCH_APPLIED
    if _PATCH_APPLIED:
        return

    try:
        import erpnext.controllers.sales_and_purchase_return as erpnext_return
        import erpnext.controllers.stock_controller as erpnext_stock

        erpnext_return.filter_serial_batches = posa_filter_serial_batches
        erpnext_stock.filter_serial_batches = posa_filter_serial_batches
        _PATCH_APPLIED = True
    except Exception as e:
        if hasattr(frappe, "logger"):
            frappe.logger().warning(f"Failed to patch filter_serial_batches: {e}")


def posa_filter_serial_batches(parent_doc, data, row, warehouse_field=None, qty_field=None):
    if not qty_field:
        qty_field = "stock_qty"

    if not hasattr(row, qty_field):
        qty_field = "qty"

    if not warehouse_field:
        warehouse_field = "warehouse"

    warehouse = row.get(warehouse_field)
    qty = abs(row.get(qty_field))

    filterd_serial_batch = frappe._dict(
        {
            "serial_nos": [],
            "batches": defaultdict(float),
            "serial_nos_valuation": data.get("serial_nos_valuation"),
            "batches_valuation": data.get("batches_valuation"),
        }
    )

    if data.serial_nos:
        available_serial_nos = []
        for serial_no, sn_qty in data.serial_nos.items():
            if sn_qty != 0:
                available_serial_nos.append(serial_no)

        if available_serial_nos:
            if parent_doc.doctype in ["Purchase Invoice", "Purchase Receipt"]:
                from erpnext.controllers.sales_and_purchase_return import get_available_serial_nos

                available_serial_nos = get_available_serial_nos(available_serial_nos, warehouse)

            # Map available serials case-insensitively
            avail_map = {s.strip().lower(): s for s in available_serial_nos if s and str(s).strip()}

            # Extract requested serials from row
            requested_raw = []
            serial_no_str = row.get("serial_no") or getattr(row, "serial_no", None)
            if serial_no_str:
                from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

                requested_raw = get_serial_nos(serial_no_str)
            elif row.get("serial_no_selected") or getattr(row, "serial_no_selected", None):
                raw_selected = row.get("serial_no_selected") or getattr(row, "serial_no_selected", None)
                if isinstance(raw_selected, (list, tuple, set)):
                    requested_raw = [str(s).strip() for s in raw_selected if str(s).strip()]

            # Fallback: check database for saved draft row if row object is missing serial_no
            if not requested_raw and getattr(row, "name", None) and getattr(row, "doctype", None):
                db_serial = frappe.db.get_value(row.doctype, row.name, "serial_no")
                if db_serial:
                    from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

                    requested_raw = get_serial_nos(db_serial)

            # Match requested serials against available serials from original invoice
            matched_serials = []
            seen = set()
            for s in requested_raw:
                s_key = str(s).strip().lower()
                if s_key in avail_map and s_key not in seen:
                    matched_serials.append(avail_map[s_key])
                    seen.add(s_key)

            if matched_serials:
                if len(matched_serials) >= qty:
                    filterd_serial_batch["serial_nos"] = matched_serials[: cint(qty)]
                else:
                    remaining = [s for s in available_serial_nos if s.strip().lower() not in seen]
                    filterd_serial_batch["serial_nos"] = matched_serials + remaining[: cint(qty - len(matched_serials))]
            elif len(available_serial_nos) > qty:
                filterd_serial_batch["serial_nos"] = sorted(available_serial_nos)[: cint(qty)]
            else:
                filterd_serial_batch["serial_nos"] = sorted(available_serial_nos)

    elif data.batches:
        preferred_batch = row.get("batch_no") or getattr(row, "batch_no", None)
        if not preferred_batch and getattr(row, "name", None) and getattr(row, "doctype", None):
            preferred_batch = frappe.db.get_value(row.doctype, row.name, "batch_no")

        batches_items = list(data.batches.items())
        if preferred_batch and preferred_batch in data.batches:
            batches_items.sort(key=lambda x: 0 if x[0] == preferred_batch else 1)

        for batch_no, batch_qty in batches_items:
            if parent_doc.get("is_internal_customer"):
                batch_qty = batch_qty * -1

            if batch_qty <= 0:
                continue

            if parent_doc.doctype in ["Purchase Invoice", "Purchase Receipt"]:
                from erpnext.controllers.sales_and_purchase_return import get_available_batch_qty

                batch_qty = get_available_batch_qty(
                    parent_doc,
                    batch_no,
                    warehouse,
                )

                if batch_qty <= 0:
                    frappe.throw(
                        _("Batch {0} is not available in warehouse {1}").format(batch_no, warehouse),
                        title=_("Batch Not Available for Return"),
                    )

            if qty <= 0:
                break

            if batch_qty > qty:
                filterd_serial_batch["batches"][batch_no] = qty
                qty = 0
            else:
                filterd_serial_batch["batches"][batch_no] += batch_qty
                qty -= batch_qty

    return filterd_serial_batch


def sync_return_item_serials_and_batches(doc, method=None):
    """Sync returned serial numbers and batch from Serial and Batch Bundle back to item row.

    ERPNext clears row.serial_no and row.batch_no upon bundle creation.
    Populating them from the created bundle ensures print formats, lists,
    and legacy reporting reflect the exact returned serials and batch.
    """
    if not doc.get("is_return"):
        return

    for item in doc.get("items", []):
        bundle = item.get("serial_and_batch_bundle")
        if not bundle:
            continue

        try:
            from erpnext.stock.serial_batch_bundle import get_serial_nos, get_batches_from_bundle

            bundle_serials = get_serial_nos(bundle)
            if bundle_serials:
                serial_str = "\n".join(bundle_serials)
                item.serial_no = serial_str
                item.db_set("serial_no", serial_str, update_modified=False)

            bundle_batches = get_batches_from_bundle(bundle)
            if bundle_batches and not item.get("batch_no"):
                first_batch = next(iter(bundle_batches.keys()))
                item.batch_no = first_batch
                item.db_set("batch_no", first_batch, update_modified=False)
        except Exception as e:
            frappe.logger().debug(f"Failed syncing serials from bundle {bundle}: {e}")
