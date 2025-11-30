<script lang="ts">
	import { createPool, PoolCategory, type PoolResponse } from '$lib/api';
	import WindowModal from './WindowModal.svelte';
	import IconClose from '~icons/mdi/close';

	let { 
		isOpen = $bindable(false),
		onPoolCreated
	} = $props<{
		isOpen?: boolean;
		onPoolCreated?: (pool: PoolResponse) => void;
	}>();

	let name = $state('');
	let description = $state('');
	let category = $state<PoolCategory>(PoolCategory.SERIES);
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	function resetForm() {
		name = '';
		description = '';
		category = PoolCategory.SERIES;
		error = null;
	}

	function handleClose() {
		isOpen = false;
		resetForm();
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!name.trim()) return;

		isSubmitting = true;
		error = null;

		try {
			const newPool = await createPool({
				name,
				description: description || undefined,
				category
			});
			
			onPoolCreated?.(newPool);
			handleClose();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to create pool';
		} finally {
			isSubmitting = false;
		}
	}
</script>

<WindowModal bind:isOpen title="Create Pool" maxWidth="max-w-lg" onClose={handleClose}>
	<!-- Header -->
	<div class="flex shrink-0 items-center justify-between border-b border-gray-200 p-6 dark:border-gray-700">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
			Create Pool
		</h2>
		<button
			onclick={handleClose}
			class="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:hover:bg-gray-700 dark:hover:text-gray-300"
			aria-label="Close modal"
		>
			<IconClose class="h-6 w-6" />
		</button>
	</div>

	<!-- Content -->
	<div class="p-6">
		<form id="create-pool-form" onsubmit={handleSubmit} class="space-y-4">
			<div>
				<label for="pool-name" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
					Name <span class="text-red-500">*</span>
				</label>
				<input
					type="text"
					id="pool-name"
					bind:value={name}
					required
					class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400"
					placeholder="Pool name"
				/>
			</div>

			<div>
				<label for="pool-category" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
					Category
				</label>
				<select
					id="pool-category"
					bind:value={category}
					class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
				>
					<option value={PoolCategory.SERIES}>Series</option>
					<option value={PoolCategory.COLLECTION}>Collection</option>
				</select>
			</div>

			<div>
				<label for="pool-description" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
					Description
				</label>
				<textarea
					id="pool-description"
					bind:value={description}
					rows="3"
					class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400"
					placeholder="Optional description"
				></textarea>
			</div>

			{#if error}
				<div class="rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
					{error}
				</div>
			{/if}
		</form>
	</div>

	<!-- Footer -->
	<div class="flex justify-end gap-3 border-t border-gray-200 p-6 dark:border-gray-700">
		<button
			type="button"
			onclick={handleClose}
			class="rounded-lg border border-gray-300 bg-white px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
		>
			Cancel
		</button>
		<button
			type="submit"
			form="create-pool-form"
			disabled={!name.trim() || isSubmitting}
			class="rounded-lg bg-primary-600 px-4 py-2 font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
		>
			{isSubmitting ? 'Creating...' : 'Create Pool'}
		</button>
	</div>
</WindowModal>

