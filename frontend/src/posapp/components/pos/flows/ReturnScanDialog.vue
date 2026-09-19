<template>
	<v-dialog v-model="dialogVisible" max-width="850px" persistent scrollable>
		<v-card class="return-scan-dialog">
			<v-card-title class="d-flex align-center justify-space-between py-3 px-4 bg-primary text-white">
				<div class="d-flex align-center">
					<v-icon icon="mdi-barcode-scan" class="mr-2" />
					<div>
						<div class="text-h6 font-weight-bold">{{ __("Scan Return Items & Serials") }}</div>
						<div class="text-caption text-white-darken-1">
							{{ __("Invoice") }}: {{ returnDoc?.name }} | {{ __("Customer") }}: {{ returnDoc?.customer_name || returnDoc?.customer }}
						</div>
					</div>
				</div>
				<v-btn icon="mdi-close" variant="text" size="small" @click="cancel" />
			</v-card-title>

			<!-- Scan Input Bar -->
			<div class="px-4 pt-4 pb-2 bg-surface">
				<v-row no-gutters align="center">
					<v-col>
						<v-text-field
							ref="scanInputRef"
							v-model="scanInput"
							:placeholder="__('Scan or type serial number / barcode, then press Enter...')"
							prepend-inner-icon="mdi-barcode"
							variant="outlined"
							density="compact"
							hide-details
							autofocus
							@keydown.enter.prevent="handleScan"
						/>
					</v-col>
					<v-col cols="auto" class="ml-2">
						<v-btn color="primary" variant="flat" prepend-icon="mdi-magnify" @click="handleScan">
							{{ __("Match") }}
						</v-btn>
					</v-col>
				</v-row>

				<!-- Feedback Alerts -->
				<v-alert
					v-if="feedbackMessage"
					:type="feedbackType"
					density="compact"
					variant="tonal"
					class="mt-2 mb-0"
					closable
					@click:close="feedbackMessage = ''"
				>
					{{ feedbackMessage }}
				</v-alert>
			</div>

			<v-divider />

			<!-- Items List -->
			<v-card-text class="pa-4" style="max-height: 500px;">
				<div v-if="!returnDoc?.items || !returnDoc.items.length" class="text-center py-6 text-medium-emphasis">
					{{ __("No items found on this invoice.") }}
				</div>

				<v-card
					v-for="item in returnDoc?.items || []"
					:key="getItemKey(item)"
					variant="outlined"
					class="mb-3 return-item-card"
					:class="{ 'return-item-card--active': getSelectedItemQty(item) > 0 }"
				>
					<v-card-item class="py-3 px-4">
						<div class="d-flex justify-space-between align-start">
							<div>
								<div class="font-weight-bold text-subtitle-1">{{ item.item_name || item.item_code }}</div>
								<div class="text-caption text-medium-emphasis">
									{{ item.item_code }}
									<span v-if="item.batch_no" class="ml-2">
										<v-chip size="x-small" color="info" label>
											<v-icon icon="mdi-package-variant-closed" start size="x-small" />
											{{ __("Batch") }}: {{ item.batch_no }}
										</v-chip>
									</span>
								</div>
							</div>

							<!-- Qty summary & controls -->
							<div class="text-right">
								<div class="text-subtitle-2">
									{{ __("Return Qty") }}:
									<span class="font-weight-bold text-primary">{{ getSelectedItemQty(item) }}</span> / {{ item.qty }}
								</div>

								<!-- Non-serialized qty stepper -->
								<div v-if="!item.has_serial_no" class="d-flex align-center justify-end mt-1">
									<v-btn
										icon="mdi-minus"
										size="x-small"
										variant="outlined"
										:disabled="getSelectedItemQty(item) <= 0"
										@click="decrementQty(item)"
									/>
									<span class="mx-3 font-weight-bold">{{ getSelectedItemQty(item) }}</span>
									<v-btn
										icon="mdi-plus"
										size="x-small"
										variant="outlined"
										:disabled="getSelectedItemQty(item) >= item.qty"
										@click="incrementQty(item)"
									/>
								</div>
							</div>
						</div>

						<!-- Serial Numbers Selection Section -->
						<div v-if="item.has_serial_no" class="mt-3 pt-2 border-t">
							<div class="d-flex align-center justify-space-between mb-1">
								<div class="text-caption font-weight-medium text-medium-emphasis">
									<v-icon icon="mdi-numeric" start size="small" />
									{{ __("Returnable Serial Numbers (Click or scan to select):") }}
								</div>
								<div class="text-caption">
									<span :class="getSelectedItemQty(item) > 0 ? 'text-success font-weight-bold' : 'text-medium-emphasis'">
										{{ getSelectedSerials(item).length }} {{ __("selected") }}
									</span>
								</div>
							</div>

							<div class="d-flex flex-wrap gap-2 mt-1">
								<v-chip
									v-for="serial in getReturnableSerials(item)"
									:key="serial"
									size="small"
									:color="isSerialSelected(item, serial) ? 'success' : 'default'"
									:variant="isSerialSelected(item, serial) ? 'flat' : 'outlined'"
									class="mr-2 mb-2 serial-chip"
									@click="toggleSerial(item, serial)"
								>
									<v-icon
										:icon="isSerialSelected(item, serial) ? 'mdi-check-circle' : 'mdi-circle-outline'"
										start
										size="x-small"
									/>
									{{ serial }}
								</v-chip>
							</div>
						</div>
					</v-card-item>
				</v-card>
			</v-card-text>

			<v-divider />

			<!-- Bottom Actions -->
			<v-card-actions class="py-3 px-4 bg-surface-variant d-flex justify-space-between align-center">
				<div class="d-flex align-center">
					<v-btn size="small" variant="text" prepend-icon="mdi-checkbox-multiple-marked-outline" @click="selectAll">
						{{ __("Select All (Full Return)") }}
					</v-btn>
					<v-btn size="small" variant="text" prepend-icon="mdi-close-box-multiple-outline" @click="clearAll">
						{{ __("Clear") }}
					</v-btn>
				</div>

				<div class="d-flex align-center">
					<v-btn variant="text" @click="cancel">{{ __("Cancel") }}</v-btn>
					<v-btn
						color="primary"
						variant="flat"
						:disabled="totalSelectedItemsCount === 0"
						prepend-icon="mdi-cart-arrow-down"
						@click="confirmSelection"
					>
						{{ __("Proceed with Return ({0})", [totalSelectedUnits]) }}
					</v-btn>
				</div>
			</v-card-actions>
		</v-card>
	</v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";

const props = withDefaults(
	defineProps<{
		modelValue: boolean;
		returnDoc: any | null;
	}>(),
	{
		returnDoc: null,
	},
);

const emit = defineEmits<{
	"update:modelValue": [value: boolean];
	confirm: [payload: { selectedItems: any[]; returnDoc: any }];
}>();

const __ = (window as any).__ || ((text: string, args?: any[]) => {
	if (!args || !args.length) return text;
	return text.replace(/\{(\d+)\}/g, (_, index) => String(args[Number(index)] ?? ""));
});

const scanInput = ref("");
const scanInputRef = ref<any>(null);
const feedbackMessage = ref("");
const feedbackType = ref<"success" | "error" | "warning">("success");

const selectedSerialsMap = ref<Record<string, string[]>>({});
const nonSerializedQtyMap = ref<Record<string, number>>({});

const dialogVisible = computed({
	get: () => props.modelValue,
	set: (val: boolean) => emit("update:modelValue", val),
});

const getItemKey = (item: any): string => {
	return item.name || item.sales_invoice_item || item.pos_invoice_item || item.item_code;
};

const getReturnableSerials = (item: any): string[] => {
	if (Array.isArray(item.returnable_serial_nos) && item.returnable_serial_nos.length) {
		return item.returnable_serial_nos.map((s: any) => String(s).trim()).filter(Boolean);
	}
	if (item.serial_no) {
		return String(item.serial_no)
			.split("\n")
			.map((s) => s.trim())
			.filter(Boolean);
	}
	return [];
};

const getSelectedSerials = (item: any): string[] => {
	const key = getItemKey(item);
	return selectedSerialsMap.value[key] || [];
};

const isSerialSelected = (item: any, serial: string): boolean => {
	const selected = getSelectedSerials(item);
	return selected.includes(serial);
};

const getSelectedItemQty = (item: any): number => {
	const key = getItemKey(item);
	if (item.has_serial_no) {
		return (selectedSerialsMap.value[key] || []).length;
	}
	return nonSerializedQtyMap.value[key] || 0;
};

const totalSelectedItemsCount = computed(() => {
	const items = props.returnDoc?.items || [];
	return items.filter((item: any) => getSelectedItemQty(item) > 0).length;
});

const totalSelectedUnits = computed(() => {
	const items = props.returnDoc?.items || [];
	return items.reduce((sum: number, item: any) => sum + getSelectedItemQty(item), 0);
});

const playScanSound = (type: "success" | "error" = "success") => {
	if (typeof window === "undefined") return;
	try {
		const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
		if (!AudioCtx) return;
		const ctx = new AudioCtx();
		const now = ctx.currentTime;
		const duration = type === "success" ? 0.15 : 0.35;
		const osc = ctx.createOscillator();
		const gain = ctx.createGain();
		osc.type = "sine";
		osc.frequency.value = type === "success" ? 880 : 220;
		gain.gain.setValueAtTime(type === "success" ? 0.18 : 0.28, now);
		gain.gain.exponentialRampToValueAtTime(0.001, now + duration);
		osc.connect(gain);
		gain.connect(ctx.destination);
		osc.start(now);
		osc.stop(now + duration);
	} catch (e) {
		// Ignore audio context errors
	}
};

const handleScan = () => {
	const raw = String(scanInput.value || "").trim();
	if (!raw) return;

	const cleanCode = raw.toLowerCase();
	const items = props.returnDoc?.items || [];

	// 1. Try matching against returnable serial numbers
	for (const item of items) {
		if (!item.has_serial_no) continue;
		const returnables = getReturnableSerials(item);
		const matchedSerial = returnables.find((s) => s.toLowerCase() === cleanCode);

		if (matchedSerial) {
			const key = getItemKey(item);
			const current = selectedSerialsMap.value[key] || [];

			if (current.includes(matchedSerial)) {
				playScanSound("error");
				feedbackType.value = "warning";
				feedbackMessage.value = __("Serial {0} has already been scanned.", [matchedSerial]);
				scanInput.value = "";
				return;
			}

			// Add serial
			selectedSerialsMap.value = {
				...selectedSerialsMap.value,
				[key]: [...current, matchedSerial],
			};

			playScanSound("success");
			feedbackType.value = "success";
			feedbackMessage.value = __("Serial {0} matched for {1}", [
				matchedSerial,
				item.item_name || item.item_code,
			]);
			scanInput.value = "";
			return;
		}
	}

	// 2. Try matching against barcode or item_code of non-serialized items
	for (const item of items) {
		if (item.has_serial_no) continue;
		const match =
			String(item.item_code || "").toLowerCase() === cleanCode ||
			String(item.barcode || "").toLowerCase() === cleanCode;

		if (match) {
			const key = getItemKey(item);
			const currentQty = nonSerializedQtyMap.value[key] || 0;
			if (currentQty < item.qty) {
				nonSerializedQtyMap.value = {
					...nonSerializedQtyMap.value,
					[key]: currentQty + 1,
				};
				playScanSound("success");
				feedbackType.value = "success";
				feedbackMessage.value = __("Added 1 unit of {0}", [item.item_name || item.item_code]);
			} else {
				playScanSound("error");
				feedbackType.value = "warning";
				feedbackMessage.value = __("Maximum quantity reached for {0}", [item.item_name || item.item_code]);
			}
			scanInput.value = "";
			return;
		}
	}

	// 3. Not found
	playScanSound("error");
	feedbackType.value = "error";
	feedbackMessage.value = __("Code {0} does not match any returnable serial or item on this invoice.", [raw]);
	scanInput.value = "";
};

const toggleSerial = (item: any, serial: string) => {
	const key = getItemKey(item);
	const current = selectedSerialsMap.value[key] || [];

	if (current.includes(serial)) {
		selectedSerialsMap.value = {
			...selectedSerialsMap.value,
			[key]: current.filter((s) => s !== serial),
		};
	} else {
		selectedSerialsMap.value = {
			...selectedSerialsMap.value,
			[key]: [...current, serial],
		};
	}
};

const incrementQty = (item: any) => {
	const key = getItemKey(item);
	const current = nonSerializedQtyMap.value[key] || 0;
	if (current < item.qty) {
		nonSerializedQtyMap.value = {
			...nonSerializedQtyMap.value,
			[key]: current + 1,
		};
	}
};

const decrementQty = (item: any) => {
	const key = getItemKey(item);
	const current = nonSerializedQtyMap.value[key] || 0;
	if (current > 0) {
		nonSerializedQtyMap.value = {
			...nonSerializedQtyMap.value,
			[key]: current - 1,
		};
	}
};

const selectAll = () => {
	const items = props.returnDoc?.items || [];
	const newSerials: Record<string, string[]> = {};
	const newQtys: Record<string, number> = {};

	for (const item of items) {
		const key = getItemKey(item);
		if (item.has_serial_no) {
			newSerials[key] = getReturnableSerials(item);
		} else {
			newQtys[key] = Number(item.qty || 0);
		}
	}

	selectedSerialsMap.value = newSerials;
	nonSerializedQtyMap.value = newQtys;
	feedbackMessage.value = "";
};

const clearAll = () => {
	selectedSerialsMap.value = {};
	nonSerializedQtyMap.value = {};
	feedbackMessage.value = "";
};

const cancel = () => {
	dialogVisible.value = false;
};

const confirmSelection = () => {
	const items = props.returnDoc?.items || [];
	const selectedItems: any[] = [];

	for (const origItem of items) {
		const key = getItemKey(origItem);
		const qtyToReturn = getSelectedItemQty(origItem);
		if (qtyToReturn <= 0) continue;

		const serials = selectedSerialsMap.value[key] || [];
		const itemCopy: any = { ...origItem };

		// Reference original row
		if (props.returnDoc?.doctype === "POS Invoice") {
			itemCopy.pos_invoice_item = origItem.name;
		} else {
			itemCopy.sales_invoice_item = origItem.name;
		}
		delete itemCopy.name;

		// Preserve pricing
		itemCopy.rate = origItem.rate;
		itemCopy.price_list_rate = origItem.price_list_rate;
		itemCopy.discount_percentage = origItem.discount_percentage;
		itemCopy.discount_amount = origItem.discount_amount;
		itemCopy.is_free_item = origItem.is_free_item;
		itemCopy.net_rate = origItem.net_rate;
		itemCopy.locked_price = true;

		// Set exact negative return quantity and amounts
		const conversionFactor = Number(origItem.conversion_factor || 1) || 1;
		itemCopy.qty = -Math.abs(qtyToReturn);
		itemCopy.stock_qty = -Math.abs(qtyToReturn * conversionFactor);
		itemCopy.amount = itemCopy.qty * Number(itemCopy.rate || 0);
		itemCopy.net_amount = itemCopy.qty * Number(itemCopy.net_rate || itemCopy.rate || 0);

		itemCopy.has_serial_no = origItem.has_serial_no || (origItem.serial_no ? 1 : 0);
		itemCopy.has_batch_no = origItem.has_batch_no || (origItem.batch_no ? 1 : 0);
		itemCopy.batch_no = origItem.batch_no || null;

		const returnableList = getReturnableSerials(origItem);
		itemCopy.returnable_serial_nos = [...returnableList];

		if (itemCopy.has_serial_no) {
			itemCopy.serial_no_selected = [...serials];
			itemCopy.serial_no_selected_count = serials.length;
			itemCopy.serial_no = serials.join("\n");
			itemCopy.serial_no_data = returnableList.map((sn) => ({
				serial_no: sn,
				batch_no: origItem.batch_no || null,
				warehouse: origItem.warehouse,
			}));
			itemCopy._batch_serial_assignment_source = "manual";
		}

		selectedItems.push(itemCopy);
	}

	if (!selectedItems.length) return;

	emit("confirm", { selectedItems, returnDoc: props.returnDoc });
	dialogVisible.value = false;
};

// Reset on dialog open
watch(
	() => props.modelValue,
	(open) => {
		if (open) {
			scanInput.value = "";
			feedbackMessage.value = "";
			selectedSerialsMap.value = {};
			nonSerializedQtyMap.value = {};

			nextTick(() => {
				if (scanInputRef.value?.focus) {
					scanInputRef.value.focus();
				}
			});
		}
	},
);
</script>

<style scoped>
.return-scan-dialog {
	border-top: 4px solid var(--pos-primary, #1976d2);
}

.return-item-card {
	transition: all 0.2s ease-in-out;
}

.return-item-card--active {
	border-color: var(--pos-primary, #1976d2) !important;
	background-color: rgba(25, 118, 210, 0.04);
}

.serial-chip {
	cursor: pointer;
	user-select: none;
}
</style>
