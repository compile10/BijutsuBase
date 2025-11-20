<script lang="ts">
	import { fade, fly } from 'svelte/transition';
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

	let isDeleting = $state(false);

    async function handleConfirm() {
        isDeleting = true;
        try {
            await onConfirm();
        } finally {
			isOpen = false;
            isDeleting = false;
        }
    }

    function handleClose() {
        if (!isDeleting) {
            isOpen = false;
        }
    }
</script>

{#if isOpen}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
		transition:fade={{ duration: 200 }}
        role="presentation"
	>
		<div
			class="relative w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
			transition:fly={{ y: 20, duration: 200 }}
            role="dialog"
            aria-modal="true"
		>
			<div class="mb-6 flex flex-col items-center text-center">
				<div class="mb-4 rounded-full bg-red-100 p-3 dark:bg-red-900/30">
					<IconAlert class="h-8 w-8 text-red-600 dark:text-red-400" />
				</div>
				<h3 class="mb-2 text-xl font-semibold text-gray-900 dark:text-white">
					Delete {count} {count === 1 ? 'File' : 'Files'}?
				</h3>
				<p class="text-gray-500 dark:text-gray-400">
					Are you sure you want to delete the selected files? This action cannot be undone.
				</p>
			</div>

			<div class="flex justify-end gap-3">
				<button
					onclick={handleClose}
                    disabled={isDeleting}
					class="rounded-lg border border-gray-300 bg-white px-4 py-2 font-semibold text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
				>
					Cancel
				</button>
				<button
					onclick={handleConfirm}
                    disabled={isDeleting}
					class="rounded-lg bg-red-600 px-4 py-2 font-semibold text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 dark:bg-red-500 dark:hover:bg-red-600"
				>
					{isDeleting ? 'Deleting...' : 'Delete'}
				</button>
			</div>
		</div>
	</div>
{/if}
