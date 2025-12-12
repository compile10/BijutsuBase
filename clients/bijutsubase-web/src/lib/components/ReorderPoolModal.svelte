<script lang="ts">
	import WindowModal from './WindowModal.svelte';
	import IconSwapVertical from '~icons/mdi/swap-vertical';

	let {
		isOpen = $bindable(false),
		count = 0,
		onConfirm
	} = $props<{
		isOpen: boolean;
		count: number;
		onConfirm: (position: number) => Promise<void>;
	}>();

	let position = $state(1);
	let isReordering = $state(false);

	async function handleConfirm() {
		if (position < 1) {
			alert('Position must be at least 1');
			return;
		}

		isReordering = true;
		try {
			await onConfirm(position);
		} finally {
			isOpen = false;
			isReordering = false;
			position = 1; // Reset for next time
		}
	}

	function handleClose() {
		if (!isReordering) {
			isOpen = false;
			position = 1; // Reset on close
		}
	}

</script>

<WindowModal bind:isOpen title="Reorder Pool Members" maxWidth="max-w-md" onClose={handleClose}>
	<div class="p-6">
		<div class="mb-6 flex flex-col items-center text-center">
			<div class="mb-4 rounded-full bg-primary-100 p-3 dark:bg-primary-900">
				<IconSwapVertical class="h-8 w-8 text-primary-600 dark:text-primary-400" />
			</div>
			<h3 class="mb-2 text-xl font-semibold text-gray-900 dark:text-white">
				Reorder {count} {count === 1 ? 'File' : 'Files'}
			</h3>
			<p class="text-gray-500 dark:text-gray-400">
				Enter the position where you want to move the selected files.
			</p>
		</div>

		<div class="mb-6">
			<label for="position-input" class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
				Position
			</label>
			<input
				id="position-input"
				type="number"
				bind:value={position}
				min="1"
				disabled={isReordering}
				class="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-900 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-primary-400 dark:focus:ring-primary-400"
				placeholder="Enter position (e.g. 1 for first)"
			/>
			<p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
				The selected files will be moved to start at this position. Use 1 to move to the beginning.
			</p>
		</div>

		<div class="flex justify-end gap-3">
			<button
				onclick={handleClose}
				disabled={isReordering}
				class="rounded-lg border border-gray-300 bg-white px-4 py-2 font-semibold text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
			>
				Cancel
			</button>
			<button
				onclick={handleConfirm}
				disabled={isReordering}
				class="rounded-lg bg-primary-600 px-4 py-2 font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 dark:bg-primary-500 dark:hover:bg-primary-600"
			>
				{isReordering ? 'Reordering...' : 'Reorder'}
			</button>
		</div>
	</div>
</WindowModal>

