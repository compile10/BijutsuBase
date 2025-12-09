<script lang="ts">
	import WindowModal from './WindowModal.svelte';
	import IconAlert from '~icons/mdi/alert-circle-outline';

	let {
		isOpen = $bindable(false),
		count = 0,
		onConfirm
	} = $props<{
		isOpen: boolean;
		count: number;
		onConfirm: () => Promise<void>;
	}>();

	let isRemoving = $state(false);

	async function handleConfirm() {
		isRemoving = true;
		try {
			await onConfirm();
		} finally {
			isOpen = false;
			isRemoving = false;
		}
	}

	function handleClose() {
		if (!isRemoving) {
			isOpen = false;
		}
	}
</script>

<WindowModal bind:isOpen title="Remove from Pool" maxWidth="max-w-md" onClose={handleClose}>
	<div class="p-6">
		<div class="mb-6 flex flex-col items-center text-center">
			<div class="mb-4 rounded-full bg-amber-100 p-3 dark:bg-amber-900/30">
				<IconAlert class="h-8 w-8 text-amber-600 dark:text-amber-400" />
			</div>
			<h3 class="mb-2 text-xl font-semibold text-gray-900 dark:text-white">
				Remove {count} {count === 1 ? 'File' : 'Files'} from Pool?
			</h3>
			<p class="text-gray-500 dark:text-gray-400">
				Are you sure you want to remove the selected files from this pool? Originals remain, but they'll no longer be in this pool.
			</p>
		</div>

		<div class="flex justify-end gap-3">
			<button
				onclick={handleClose}
				disabled={isRemoving}
				class="rounded-lg border border-gray-300 bg-white px-4 py-2 font-semibold text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
			>
				Cancel
			</button>
			<button
				onclick={handleConfirm}
				disabled={isRemoving}
				class="rounded-lg bg-amber-600 px-4 py-2 font-semibold text-white hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-amber-500 disabled:opacity-50 dark:bg-amber-500 dark:hover:bg-amber-600"
			>
				{isRemoving ? 'Removing...' : 'Remove'}
			</button>
		</div>
	</div>
</WindowModal>

