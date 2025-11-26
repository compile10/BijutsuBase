<script lang="ts">
	import { VList } from 'virtua/svelte';
	import type { VListHandle } from 'virtua/svelte';
	import { type FileThumb, searchFiles } from '$lib/api';
	import Lightbox from '$lib/components/Lightbox.svelte';
	import SelectionManager from '$lib/components/SelectionManager.svelte';
	import { longpress } from '$lib/actions/longpress';
	import IconCheckCircle from '~icons/mdi/check-circle';
	import IconCircleOutline from '~icons/mdi/checkbox-blank-circle-outline';

	let {
		tags = '',
		sort = 'date_desc'
	}: {
		tags?: string;
		sort?: string;
	} = $props();

	let files = $state<FileThumb[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let fetching = $state(false);
	let hasMore = $state(false);
	let nextCursor = $state<string | null>(null);

	let itemsPerRow = $state(6);
	let lightboxOpen = $state(false);
	let lightboxIndex = $state(0);
	let vlistRef: VListHandle | undefined = $state();

	// Selection Mode State
	let isSelectMode = $state(false);
	let selectedFiles = $state(new Set<string>());

	// Group thumbnails into rows for VList
	let rows = $derived.by(() => {
		const result: FileThumb[][] = [];
		for (let i = 0; i < files.length; i += itemsPerRow) {
			result.push(files.slice(i, i + itemsPerRow));
		}
		return result;
	});

	// Calculate items per row based on window width
	function updateItemsPerRow() {
		if (typeof window === 'undefined') return;
		const width = window.innerWidth;
		if (width < 640) {
			itemsPerRow = 3; // mobile
		} else if (width < 768) {
			itemsPerRow = 3; // small tablet
		} else if (width < 1024) {
			itemsPerRow = 4; // tablet
		} else if (width < 1280) {
			itemsPerRow = 6; // laptop
		} else {
			itemsPerRow = 8; // desktop
		}
	}
	
	export async function refresh() {
		await fetchInitialResults();
	}

	async function fetchInitialResults() {
		if (!tags) {
			loading = false;
			files = [];
			nextCursor = null;
			hasMore = false;
			return;
		}

		loading = true;
		error = null;
		files = [];
		nextCursor = null;
		hasMore = false;

		try {
			const response = await searchFiles(tags, sort);
			files = response.items;
			nextCursor = response.next_cursor;
			hasMore = response.has_more;
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred';
		} finally {
			loading = false;
		}
	}

	async function fetchMoreItems() {
		if (!tags || fetching || !hasMore || !nextCursor) {
			return;
		}

		fetching = true;

		try {
			const response = await searchFiles(tags, sort, nextCursor);
			files = [...files, ...response.items];
			nextCursor = response.next_cursor;
			hasMore = response.has_more;
		} catch (err) {
			console.error('Failed to fetch more items:', err);
		} finally {
			fetching = false;
		}
	}

	// Handle scroll events for infinite scrolling
	async function handleScroll() {
		if (!vlistRef) return;
		
		const count = files.length;
		const endRowIndex = vlistRef.findEndIndex();
		const lastVisibleItemIndex = (endRowIndex + 1) * itemsPerRow;
		
		// Trigger when we're 2 rows away from end
		if (lastVisibleItemIndex >= count - (itemsPerRow * 2) && hasMore && !fetching) {
			await fetchMoreItems();
		}
	}

	// Open lightbox at specific index
	function openLightbox(index: number) {
		lightboxIndex = index;
		lightboxOpen = true;
	}

	// Selection Mode Handlers
	function handleLongPress(file: FileThumb) {
		if (!isSelectMode) {
			isSelectMode = true;
			selectedFiles = new Set([file.sha256_hash]);
		}
	}

	function toggleSelection(file: FileThumb, index: number) {
		if (isSelectMode) {
			const newSet = new Set(selectedFiles);
			if (newSet.has(file.sha256_hash)) {
				newSet.delete(file.sha256_hash);
			} else {
				newSet.add(file.sha256_hash);
			}
			selectedFiles = newSet;

			if (selectedFiles.size === 0) {
				isSelectMode = false;
			}
		} else {
			openLightbox(index);
		}
	}
	
	function handleFilesDeleted(deletedHashes: Set<string>) {
		files = files.filter(t => !deletedHashes.has(t.sha256_hash));
	}

	function handleBulkEdit(changes: { removedTags: Set<string> }) {
		const currentSearchTags = tags.split(' ').filter(t => t.trim());
		const hasConflict = currentSearchTags.some(t => changes.removedTags.has(t));

		if (hasConflict) {
			// Remove selected files from thumbnails as they no longer match the search
			files = files.filter(t => !selectedFiles.has(t.sha256_hash));
		}
		
		// Always clear selection and exit select mode
		selectedFiles = new Set();
		isSelectMode = false;
	}

	// Update items per row on window resize
	$effect(() => {
		if (typeof window === 'undefined') return;
		
		updateItemsPerRow();
		window.addEventListener('resize', updateItemsPerRow);
		
		return () => {
			window.removeEventListener('resize', updateItemsPerRow);
		};
	});

	// Initial fetch when tags or sort change
	$effect(() => {
		fetchInitialResults();
	});
</script>

<SelectionManager
	bind:isSelectMode
	bind:selectedFiles
	onBulkEdit={handleBulkEdit}
	onFilesDeleted={handleFilesDeleted}
/>

<div class="flex flex-1 flex-col overflow-hidden">
	<!-- Loading State -->
	{#if loading}
		<div class="flex flex-1 items-center justify-center">
			<div class="text-center">
				<div class="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600 dark:border-gray-600 dark:border-t-primary-400"></div>
				<p class="text-gray-600 dark:text-gray-400">Loading...</p>
			</div>
		</div>
	{/if}

	<!-- Error State -->
	{#if error}
		<div class="rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
			<p class="text-red-800 dark:text-red-400">Error: {error}</p>
		</div>
	{/if}

	<!-- Empty State -->
	{#if !loading && !error && files.length === 0}
		<div class="flex flex-1 items-center justify-center">
			<p class="text-xl text-gray-600 dark:text-gray-400">
				{tags ? 'No results found' : 'Enter tags to search'}
			</p>
		</div>
	{/if}

	<!-- Results Grid with VList -->
	{#if !loading && !error && files.length > 0}
		<VList bind:this={vlistRef} data={rows} class="flex-1 min-h-0 lg:px-16 md:px-8 px-4" onscroll={handleScroll}>
			{#snippet children(row, rowIndex)}
				{#if rowIndex === 0}
					<div class="mb-2 pb-2 text-sm text-gray-600 dark:text-gray-400 pt-4">
						Found {files.length}{hasMore ? '+' : ''} {files.length === 1 ? 'result' : 'results'}
						{#if tags}
							for <span class="font-mono font-semibold">{tags}</span>
						{/if}
					</div>
				{/if}
				<div
					class="grid gap-2 pb-2"
					style="grid-template-columns: repeat({itemsPerRow}, minmax(0, 1fr));"
				>
					{#each row as thumb, colIndex}
						{@const index = rowIndex * itemsPerRow + colIndex}
						{@const isSelected = selectedFiles.has(thumb.sha256_hash)}
						<button
							use:longpress={() => handleLongPress(thumb)}
							onclick={() => toggleSelection(thumb, index)}
							class="group relative aspect-square overflow-hidden rounded-lg border bg-gray-100 transition-transform dark:bg-gray-800 
							{isSelectMode && isSelected 
								? 'border-primary-500 ring-2 ring-primary-500 dark:border-primary-400 dark:ring-primary-400' 
								: 'border-gray-200 hover:scale-105 dark:border-gray-700'}"
						>
							<img
								src={thumb.thumbnail_url}
								alt="Thumbnail"
								class="h-full w-full object-cover {isSelectMode && isSelected ? 'opacity-75' : ''}"
							/>
							
							{#if isSelectMode}
								<div class="absolute right-2 top-2 z-10">
									{#if isSelected}
										<IconCheckCircle class="h-6 w-6 text-primary-600 bg-white rounded-full dark:text-primary-400 dark:bg-gray-900" />
									{:else}
										<IconCircleOutline class="h-6 w-6 text-white drop-shadow-md" />
									{/if}
								</div>
							{:else}
								<div class="absolute inset-0 bg-black opacity-0 transition-opacity group-hover:opacity-10"></div>
							{/if}
						</button>
					{/each}
				</div>
				
				<!-- Loading indicator at the end of the list -->
				{#if rowIndex === rows.length - 1 && fetching && hasMore}
					<div class="flex justify-center py-8">
						<div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600 dark:border-gray-600 dark:border-t-primary-400"></div>
					</div>
				{/if}
			{/snippet}
		</VList>
	{/if}
</div>

<!-- Lightbox -->
<Lightbox bind:isOpen={lightboxOpen} bind:currentIndex={lightboxIndex} files={files} />
