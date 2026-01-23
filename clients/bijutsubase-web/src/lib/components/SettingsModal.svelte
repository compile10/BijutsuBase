<script lang="ts">
	import WindowModal from './WindowModal.svelte';
	import { getSettingsContext, type MaxRating } from '$lib/settings.svelte';
	import IconClose from '~icons/mdi/close';

	let { isOpen = $bindable(false) }: { isOpen?: boolean } = $props();

	const settings = getSettingsContext();

	const ratingOptions: { value: MaxRating; label: string; description: string }[] = [
		{
			value: 'safe',
			label: 'Safe',
			description: 'Show only safe content'
		},
		{
			value: 'sensitive',
			label: 'Sensitive',
			description: 'Show safe and sensitive content'
		},
		{
			value: 'questionable',
			label: 'Questionable',
			description: 'Show safe, sensitive, and questionable content'
		},
		{
			value: null,
			label: 'All (including Explicit)',
			description: 'Show all content without filtering'
		}
	];

	function handleRatingChange(value: MaxRating) {
		settings.setMaxRating(value);
	}

	function handleClose() {
		isOpen = false;
	}
</script>

<WindowModal bind:isOpen title="Settings" maxWidth="max-w-3xl" onClose={handleClose}>
	<!-- Header -->
	<div
		class="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700"
	>
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white">Settings</h2>
		<button
			onclick={handleClose}
			class="rounded-lg p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
			aria-label="Close settings"
		>
			<IconClose class="h-6 w-6" />
		</button>
	</div>

	<!-- Content -->
	<div class="overflow-y-auto px-6 py-6">
		<!-- General Section -->
		<div class="mb-8">
			<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">General</h3>

			<!-- Rating Filter -->
			<div class="space-y-3">
				<div class="block text-sm font-medium text-gray-700 dark:text-gray-300">
					Content Rating Filter
				</div>
				<p class="text-sm text-gray-600 dark:text-gray-400">
					Control the maximum rating level of content shown in searches. This affects all search
					results across the application.
				</p>

				<div class="space-y-2">
					{#each ratingOptions as option (option.value ?? 'null')}
						<button
							onclick={() => handleRatingChange(option.value)}
							class="flex w-full items-start gap-3 rounded-lg border p-4 text-left transition-all {settings.maxRating ===
							option.value
								? 'border-primary-500 bg-primary-50 dark:border-primary-400 dark:bg-primary-900/20'
								: 'border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-gray-600'}"
						>
							<div
								class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 {settings.maxRating ===
								option.value
									? 'border-primary-500 dark:border-primary-400'
									: 'border-gray-300 dark:border-gray-600'}"
							>
								{#if settings.maxRating === option.value}
									<div
										class="h-2.5 w-2.5 rounded-full bg-primary-500 dark:bg-primary-400"
									></div>
								{/if}
							</div>
							<div class="flex-1">
								<div
									class="font-medium {settings.maxRating === option.value
										? 'text-primary-900 dark:text-primary-100'
										: 'text-gray-900 dark:text-white'}"
								>
									{option.label}
								</div>
								<div
									class="text-sm {settings.maxRating === option.value
										? 'text-primary-700 dark:text-primary-300'
										: 'text-gray-600 dark:text-gray-400'}"
								>
									{option.description}
								</div>
							</div>
						</button>
					{/each}
				</div>
			</div>
		</div>
	</div>

	<!-- Footer -->
	<div
		class="flex items-center justify-end border-t border-gray-200 px-6 py-4 dark:border-gray-700"
	>
		<button
			onclick={handleClose}
			class="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600"
		>
			Done
		</button>
	</div>
</WindowModal>
