<script lang="ts">
	import { fade } from 'svelte/transition';
	import IconClose from '~icons/mdi/close';
	import IconDelete from '~icons/mdi/trash-can-outline';
	import IconPencil from '~icons/mdi/pencil';
	import IconFolderPlus from '~icons/mdi/folder-plus-outline';
	import DeleteConfirmationModal from '$lib/components/DeleteConfirmationModal.svelte';
	import BulkEditModal from '$lib/components/BulkEditModal.svelte';
	import SelectPoolModal from '$lib/components/SelectPoolModal.svelte';
	import { deleteFile, addFilesToPool, type PoolSimple } from '$lib/api';

	let { 
		isSelectMode = $bindable(), 
		selectedFiles = $bindable(),
		onBulkEdit,
		onFilesDeleted
	}: {
		isSelectMode: boolean;
		selectedFiles: Set<string>;
		onBulkEdit: (changes: { removedTags: Set<string> }) => void;
		onFilesDeleted: (deletedHashes: Set<string>) => void;
	} = $props();

	let deleteModalOpen = $state(false);
	let bulkEditModalOpen = $state(false);
	let selectPoolModalOpen = $state(false);

	function exitSelectMode() {
		isSelectMode = false;
		selectedFiles = new Set();
	}

	async function handleDeleteConfirm() {
		const filesToDelete = Array.from(selectedFiles);
		
		try {
			await Promise.all(filesToDelete.map(hash => deleteFile(hash)));
			
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
</script>

{#if isSelectMode}
	<div 
		class="fixed bottom-0 left-0 right-0 z-20 border-t border-primary-200 bg-primary-50 px-4 py-3 shadow-lg dark:border-primary-800 dark:bg-primary-900/90 backdrop-blur-sm"
		transition:fade={{ duration: 200 }}
	>
		<div class="mx-auto flex max-w-7xl items-center justify-between">
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
				<button
					onclick={() => selectPoolModalOpen = true}
					class="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-primary-500 dark:hover:bg-primary-600"
				>
					<IconFolderPlus class="h-5 w-5" />
					Add to Pool
				</button>
				<button
					onclick={() => bulkEditModalOpen = true}
					class="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-primary-500 dark:hover:bg-primary-600"
				>
					<IconPencil class="h-5 w-5" />
					Edit
				</button>
				<button
					onclick={() => deleteModalOpen = true}
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
<BulkEditModal
	bind:isOpen={bulkEditModalOpen}
	selectedFiles={selectedFiles}
	onChange={onBulkEdit}
/>

<!-- Select Pool Modal -->
<SelectPoolModal
	bind:isOpen={selectPoolModalOpen}
	onPoolSelected={handlePoolSelected}
/>

