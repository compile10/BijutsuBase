<script lang="ts">
	import { getCommonTags, bulkAssociateTag, bulkDissociateTag, bulkUpdateFileMetadata } from '$lib/api';
	import type { TagResponse } from '$lib/api';
	import WindowModal from './WindowModal.svelte';
	import TagSection from '$lib/components/TagSection.svelte';
	import IconPencil from '~icons/mdi/pencil';
	import IconClose from '~icons/mdi/close';

	let { 
		isOpen = $bindable(false),
		selectedFiles,
		onChange
	} = $props<{
		isOpen: boolean;
		selectedFiles: Set<string>;
		onChange: (changes: { removedTags: Set<string> }) => void;
	}>();

	let commonTags = $state<TagResponse[]>([]);
	let isUpdatingTags = $state(false);
	let isUpdatingMetadata = $state(false);
	let hasChanges = $state(false);
	let error = $state<string | null>(null);
	let removedTags = $state(new Set<string>());

	// Metadata selection state
	let selectedRating = $state('no_change');
	let selectedAi = $state('no_change');

	async function fetchCommonTags() {
		if (selectedFiles.size === 0) return;
		isUpdatingTags = true;
		error = null;
		try {
			commonTags = await getCommonTags(Array.from(selectedFiles));
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load tags';
		} finally {
			isUpdatingTags = false;
		}
	}

	$effect(() => {
		if (isOpen) {
			fetchCommonTags();
			selectedRating = 'no_change';
			selectedAi = 'no_change';
			hasChanges = false;
		}
	});

	function handleCloseModal() {
		if (isUpdatingTags || isUpdatingMetadata) return;
		isOpen = false;
		commonTags = [];
		selectedRating = 'no_change';
		selectedAi = 'no_change';
		
		if (hasChanges) {
			onChange({ removedTags });
		}
		hasChanges = false;
		removedTags = new Set();
	}

	async function handleBulkAddTag(name: string, category: string) {
		if (selectedFiles.size === 0) return;
		const hashes = Array.from(selectedFiles) as string[];
		isUpdatingTags = true;
		try {
			await bulkAssociateTag({
				file_hashes: hashes,
				tag_name: name,
				category
			});
			hasChanges = true;
			removedTags.delete(name);
		} catch (err) {
			isUpdatingTags = false;
			error = err instanceof Error ? err.message : 'Failed to add tag';
		}
		try {
			await fetchCommonTags();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to fetch common tags';
		}
		finally {
			isUpdatingTags = false;
		}
	}

	async function handleBulkDeleteTag(name: string) {
		if (selectedFiles.size === 0) return;
		const hashes = Array.from(selectedFiles) as string[];
		isUpdatingTags = true;
		try {
			await bulkDissociateTag({
				file_hashes: hashes,
				tag_name: name
			});
			hasChanges = true;
			removedTags.add(name);
		} catch (err) {
			isUpdatingTags = false;
			error = err instanceof Error ? err.message : 'Failed to delete tag';
		}
		try {
			await fetchCommonTags();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to fetch common tags';
		}
		finally {
			isUpdatingTags = false;
		}
	}

	async function handleMetadataUpdate(updates: { rating?: string; ai_generated?: boolean }) {
		if (selectedFiles.size === 0) return;

		// Filter out 'no_change' or undefined values
		if (updates.rating === 'no_change') delete updates.rating;
		if (updates.ai_generated === undefined) delete updates.ai_generated;
		
		if (Object.keys(updates).length === 0) return;

		const payload = {
			file_hashes: Array.from(selectedFiles) as string[],
			...updates
		};

		isUpdatingMetadata = true;
		error = null;
		try {
			await bulkUpdateFileMetadata(payload);
			hasChanges = true;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to update metadata';
		} finally {
			isUpdatingMetadata = false;
		}
	}
</script>

<WindowModal bind:isOpen title="Edit Files" maxWidth="max-w-2xl" onClose={handleCloseModal}>
	<!-- Header -->
	<div class="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700">
		<div class="flex items-center gap-3">
			<div class="rounded-full bg-primary-100 p-2 dark:bg-primary-900/30">
				<IconPencil class="h-6 w-6 text-primary-600 dark:text-primary-400" />
			</div>
			<h3 class="text-xl font-bold text-gray-900 dark:text-white">
				Edit {selectedFiles.size} {selectedFiles.size === 1 ? 'File' : 'Files'}
			</h3>
		</div>
		<button
			onclick={handleCloseModal}
			disabled={isUpdatingMetadata || isUpdatingTags}
			class="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
		>
			<IconClose class="h-6 w-6" />
		</button>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto p-6">
		{#if error}
			<div class="mb-6 rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
				<p class="text-sm text-red-800 dark:text-red-400">{error}</p>
			</div>
		{/if}

		<div class="grid gap-8 md:grid-cols-2">
			<!-- Metadata Section -->
			<div class="space-y-6">
				<h4 class="border-b border-gray-200 pb-2 text-lg font-semibold text-gray-900 dark:border-gray-700 dark:text-white">
					Metadata
				</h4>
				
				<div class="space-y-4">
					<div>
						<label for="bulk-rating" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
							Rating
						</label>
						<select
							id="bulk-rating"
							bind:value={selectedRating}
							onchange={() => {
								if (selectedRating !== 'no_change') {
									handleMetadataUpdate({ rating: selectedRating });
								}
							}}
							disabled={isUpdatingTags || isUpdatingMetadata}
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						>
							<option value="no_change">No Change</option>
							<option value="safe">Safe</option>
							<option value="sensitive">Sensitive</option>
							<option value="questionable">Questionable</option>
							<option value="explicit">Explicit</option>
						</select>
					</div>

					<div>
						<label for="bulk-ai" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
							AI Generated
						</label>
						<select
							id="bulk-ai"
							bind:value={selectedAi}
							onchange={() => {
								if (selectedAi !== 'no_change') {
									handleMetadataUpdate({ ai_generated: selectedAi === 'true' });
								}
							}}
							disabled={isUpdatingTags || isUpdatingMetadata}
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						>
							<option value="no_change">No Change</option>
							<option value="true">Yes</option>
							<option value="false">No</option>
						</select>
					</div>
				</div>
			</div>

			<!-- Tags Section -->
			<div class="space-y-6">
				<h4 class="border-b border-gray-200 pb-2 text-lg font-semibold text-gray-900 dark:border-gray-700 dark:text-white">
					Common Tags
				</h4>
				
				{#if isUpdatingTags}
					<div class="flex items-center justify-center py-8">
						<div class="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600 dark:border-gray-600 dark:border-t-primary-400"></div>
					</div>
				{:else}
					<TagSection
						tags={commonTags}
						onAddTag={handleBulkAddTag}
						onDeleteTag={handleBulkDeleteTag}
						disabled={isUpdatingMetadata}
					/>
					
					<p class="mt-4 text-xs text-gray-500 dark:text-gray-400">
						Only tags present in ALL selected files are shown. Adding a tag adds it to all selected files. Removing a tag removes it from all selected files.
					</p>
				{/if}
			</div>
		</div>
	</div>

</WindowModal>
