<script lang="ts">
	import { fade } from 'svelte/transition';
	import IconClose from '~icons/mdi/close';
	import IconDelete from '~icons/mdi/trash-can-outline';
	import IconPencil from '~icons/mdi/pencil';
	import IconFolderPlus from '~icons/mdi/folder-plus-outline';
	import IconFolderMinus from '~icons/mdi/folder-minus-outline';
	import IconSwapVertical from '~icons/mdi/swap-vertical';
	import DeleteConfirmationModal from '$lib/components/DeleteConfirmationModal.svelte';
	import BulkEditModal from '$lib/components/BulkEditModal.svelte';
	import SelectPoolModal from '$lib/components/SelectPoolModal.svelte';
	import RemoveFromPoolConfirmationModal from '$lib/components/RemoveFromPoolConfirmationModal.svelte';
	import ReorderPoolModal from '$lib/components/ReorderPoolModal.svelte';
	import {
		deleteFile,
		addFilesToPool,
		removeFileFromPool,
		reorderPoolFiles,
		type PoolSimple
	} from '$lib/api';

	let {
		isSelectMode = $bindable(),
		selectedFiles,
		onBulkEdit,
		onFilesDeleted,
		onReorder,
		poolId
	}: {
		isSelectMode: boolean;
		selectedFiles: Set<string>;
		onBulkEdit: (changes: { removedTags: Set<string> }) => void;
		onFilesDeleted: (deletedHashes: Set<string>) => void;
		onReorder?: () => void;
		poolId?: string;
	} = $props();

	let deleteModalOpen = $state(false);
	let bulkEditModalOpen = $state(false);
	let selectPoolModalOpen = $state(false);
	let removeFromPoolModalOpen = $state(false);
	let reorderModalOpen = $state(false);

	function exitSelectMode() {
		isSelectMode = false;
		selectedFiles.clear();
	}

	async function handleDeleteConfirm() {
		const filesToDelete = Array.from(selectedFiles);

		try {
			await Promise.all(filesToDelete.map((hash) => deleteFile(hash)));

			// Notify parent to remove from local state
			onFilesDeleted(selectedFiles);

			exitSelectMode();
		} catch (err) {
			console.error('Failed to delete files:', err);
			// Ideally show a toast here
			alert('Failed to delete some files');
		}
	}

	async function handlePoolSelected(pool: PoolSimple) {
		const files = Array.from(selectedFiles);
		try {
			await addFilesToPool(pool.id, files);
			exitSelectMode();
		} catch (err) {
			console.error('Failed to add files to pool:', err);
		}
	}

	async function handleRemoveFromPoolConfirm() {
		if (!poolId) return;

		const filesToRemove = Array.from(selectedFiles);

		try {
			await Promise.all(filesToRemove.map((hash) => removeFileFromPool(poolId, hash)));
			onFilesDeleted(selectedFiles);
			exitSelectMode();
		} catch (err) {
			console.error('Failed to remove files from pool:', err);
			alert('Failed to remove some files from the pool');
		}
	}

	async function handleReorderConfirm(position: number) {
		if (!poolId) return;

		const filesToReorder = Array.from(selectedFiles);

		try {
			// Convert 1-indexed position to 0-indexed after_order
			await reorderPoolFiles(poolId, filesToReorder, position - 1);

			// Notify parent to refresh
			if (onReorder) {
				onReorder();
			}

			exitSelectMode();
		} catch (err) {
			console.error('Failed to reorder files in pool:', err);
			alert('Failed to reorder files in the pool');
		}
	}
</script>

{#if isSelectMode}
	<div
		class="select-action-bar z-20 border-t border-primary-200 bg-primary-50 shadow-lg backdrop-blur-sm dark:border-primary-800 dark:bg-primary-900/90"
		transition:fade={{ duration: 200 }}
	>
		<div
			class="mx-auto flex max-w-7xl items-center justify-between gap-3 overflow-x-auto px-4 py-3 scrollbar-none [&::-webkit-scrollbar]:hidden"
		>
			<div class="flex items-center gap-4">
				<button
					onclick={exitSelectMode}
					class="rounded-full p-1 text-gray-500 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-700"
				>
					<IconClose class="h-6 w-6" />
				</button>
				<span class="font-semibold text-primary-900 dark:text-primary-100">
					{selectedFiles.size} selected
				</span>
			</div>
			<div class="flex gap-2">
				{#if poolId}
					<button
						onclick={() => (reorderModalOpen = true)}
						class="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-purple-500 dark:hover:bg-purple-600"
					>
						<IconSwapVertical class="h-5 w-5" />
						Reorder
					</button>
					<button
						onclick={() => (removeFromPoolModalOpen = true)}
						class="flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-amber-500 dark:bg-amber-500 dark:hover:bg-amber-600"
					>
						<IconFolderMinus class="h-5 w-5" />
						Remove from Pool
					</button>
				{/if}
				<button
					onclick={() => (selectPoolModalOpen = true)}
					class="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-primary-500 dark:hover:bg-primary-600"
				>
					<IconFolderPlus class="h-5 w-5" />
					Add to Pool
				</button>
				<button
					onclick={() => (bulkEditModalOpen = true)}
					class="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-primary-500 dark:hover:bg-primary-600"
				>
					<IconPencil class="h-5 w-5" />
					Edit
				</button>
				<button
					onclick={() => (deleteModalOpen = true)}
					class="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 dark:bg-red-500 dark:hover:bg-red-600"
				>
					<IconDelete class="h-5 w-5" />
					Delete
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Delete Confirmation Modal -->
<DeleteConfirmationModal
	bind:isOpen={deleteModalOpen}
	count={selectedFiles.size}
	onConfirm={handleDeleteConfirm}
/>

<!-- Bulk Edit Modal -->
<BulkEditModal bind:isOpen={bulkEditModalOpen} {selectedFiles} onChange={onBulkEdit} />

<!-- Select Pool Modal -->
<SelectPoolModal bind:isOpen={selectPoolModalOpen} onPoolSelected={handlePoolSelected} />

<!-- Remove from Pool Confirmation Modal -->
{#if poolId}
	<RemoveFromPoolConfirmationModal
		bind:isOpen={removeFromPoolModalOpen}
		count={selectedFiles.size}
		onConfirm={handleRemoveFromPoolConfirm}
	/>
{/if}

<!-- Reorder Pool Modal -->
{#if poolId}
	<ReorderPoolModal
		bind:isOpen={reorderModalOpen}
		count={selectedFiles.size}
		onConfirm={handleReorderConfirm}
	/>
{/if}

<style>
	/* Docked full-width bar, or a floating pill on iOS/iPadOS (not macOS Safari). */
	.select-action-bar {
		position: fixed;
		inset-inline: 0;
		bottom: 0;
		padding-inline: env(safe-area-inset-left) env(safe-area-inset-right);
		padding-bottom: env(safe-area-inset-bottom);

		@supports (-webkit-touch-callout: none) {
			@media (any-pointer: coarse) {
				inset-inline: 1rem;
				bottom: calc(env(safe-area-inset-bottom) + 0.75rem);
				padding: 0.375rem 0.75rem;
				border-radius: 9999px;
				border-top-width: 0;
				border-width: 1px;
				box-shadow:
					0 10px 15px -3px rgb(0 0 0 / 0.12),
					0 4px 6px -4px rgb(0 0 0 / 0.1);

				& > :first-child {
					padding: 0.125rem 0.25rem;
				}
			}
		}
	}
</style>
