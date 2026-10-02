<template>
	<div class="selection-fields">
		<!-- Sales Person Selection -->
		<v-row class="pb-0 mb-2" align="start">
			<v-col cols="12">
				<p v-if="salesPersons && salesPersons.length > 0" class="mt-1 mb-1 text-subtitle-2">
					{{ salesPersons.length }} {{ $__("sales persons found") }}
				</p>
				<p v-else class="mt-1 mb-1 text-subtitle-2 text-red">{{ $__("No sales persons found") }}</p>
				<v-select
					density="compact"
					clearable
					variant="solo"
					color="primary"
					:label="$frappe._('Sales Person')"
					:model-value="salesPerson"
					:items="salesPersons"
					item-title="title"
					item-value="value"
					class="sleek-field pos-themed-input"
					:no-data-text="$__('Sales Person not found')"
					hide-details
					:disabled="readonly || !!salesPartner"
					@update:model-value="$emit('update:sales-person', $event)"
				></v-select>
			</v-col>
		</v-row>

		<!-- Sales Partner Info Card (when selected) -->
		<v-row v-if="selectedPartnerInfo" class="pb-0 mb-2" align="start">
			<v-col cols="12">
				<v-card
					class="sales-partner-card"
					variant="tonal"
					color="primary"
					density="compact"
				>
					<v-card-text class="pa-3">
						<div class="d-flex align-center justify-space-between">
							<div class="d-flex align-center">
								<v-icon class="mr-2" size="20">mdi-account-tie</v-icon>
								<div>
									<div class="text-subtitle-2 font-weight-bold">
										{{ selectedPartnerInfo.partner_name }}
									</div>
									<div v-if="selectedPartnerInfo.referral_code" class="text-caption">
										{{ $__("Referral Code") }}: <strong>{{ selectedPartnerInfo.referral_code }}</strong>
									</div>
								</div>
							</div>
							<v-btn
								icon
								variant="text"
								size="x-small"
								:disabled="readonly"
								@click="$emit('update:sales-partner', null)"
							>
								<v-icon size="16">mdi-close</v-icon>
							</v-btn>
						</div>
					</v-card-text>
				</v-card>
			</v-col>
		</v-row>

		<!-- Sales Partner Selection -->
		<v-row class="pb-0 mb-2" align="start">
			<v-col cols="12">
				<v-autocomplete
					density="compact"
					clearable
					variant="solo"
					color="primary"
					:label="$frappe._('Sales Partner (Referral Code)')"
					:model-value="salesPartner"
					:items="salesPartners"
					item-title="title"
					item-value="value"
					class="sleek-field pos-themed-input"
					:no-data-text="$__('Sales Partner not found')"
					hide-details
					:disabled="readonly || !!salesPerson"
					@update:model-value="$emit('update:sales-partner', $event)"
				></v-autocomplete>
			</v-col>
		</v-row>
		<!-- Print Format Selection -->
		<v-row v-if="showPrintFormat" class="pb-0 mb-2" align="start">
			<v-col cols="12">
				<v-select
					density="compact"
					clearable
					variant="solo"
					color="primary"
					:label="$frappe._('Print Format')"
					:model-value="printFormat"
					:items="printFormats"
					class="sleek-field pos-themed-input"
					:no-data-text="$__('No Print Formats Found')"
					hide-details
					@update:model-value="$emit('update:print-format', $event)"
				></v-select>
			</v-col>
		</v-row>
	</div>
</template>

<script setup>
import { inject, computed } from "vue";

const props = defineProps({
	salesPersons: {
		type: Array,
		default: () => [],
	},
	salesPerson: {
		type: String,
		default: "",
	},
	salesPartners: {
		type: Array,
		default: () => [],
	},
	salesPartner: {
		type: String,
		default: "",
	},
	readonly: {
		type: Boolean,
		default: false,
	},
	printFormats: {
		type: Array,
		default: () => [],
	},
	printFormat: {
		type: String,
		default: "",
	},
	showPrintFormat: {
		type: Boolean,
		default: true,
	},
});

defineEmits(["update:sales-person", "update:sales-partner", "update:print-format"]);

const $frappe = inject("frappe", window.frappe);
const $__ = inject("__", window.__);

const selectedPartnerInfo = computed(() => {
	if (!props.salesPartner || !props.salesPartners || !props.salesPartners.length) {
		return null;
	}
	const match = props.salesPartners.find((sp) => sp.value === props.salesPartner);
	if (!match) return null;
	return {
		partner_name: match.title?.replace(/ \(.*\)$/, "") || match.value,
		referral_code: match.referral_code || "",
	};
});
</script>

<style scoped>
.pos-themed-input :deep(.v-field__input) {
	font-weight: 500;
}

.sales-partner-card {
	border-left: 4px solid rgb(var(--v-theme-primary));
	transition: all 0.3s ease;
}

.sales-partner-card:hover {
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
</style>
