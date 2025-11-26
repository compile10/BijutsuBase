<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { VList } from 'virtua/svelte';
	import type { VListHandle } from 'virtua/svelte';
	import { searchFiles, type FileThumb } from '$lib/api';
	import Lightbox from '$lib/components/Lightbox.svelte';
	import SortDropdown from '$lib/components/SortDropdown.svelte';
	import SelectionManager from '$lib/components/SelectionManager.svelte';
	import { longpress } from '$lib/actions/longpress';
	import IconCheckCircle from '~icons/mdi/check-circle';
	import IconCircleOutline from '~icons/mdi/checkbox-blank-circle-outline';
	import SearchInput from '$lib/components/SearchInput.svelte';

	let thumbnails = $state<FileThumb[]>([]);
	let loading = $state(true); // Full page loading state
	let error = $state<string | null>(null);
	let itemsPerRow = $state(6);
	let lightboxOpen = $state(false);
	let lightboxIndex = $state(0);
	
	// Pagination state
	let fetching = $state(false); // Fetching more items for page (non-blocking)
	let nextCursor = $state<string | null>(null);
	let hasMore = $state(false);
	let fetchedCountRef = $state(-1);
	let vlistRef: VListHandle | undefined = $state();
	
	// Selection Mode State
	let isSelectMode = $state(false);
	let selectedFiles = $state(new Set<string>());

	// Get tags and sort from URL params
	let tags = $derived(page.url.searchParams.get('tags') || '');
	let currentSort = $derived(page.url.searchParams.get('sort') || 'date_desc');
	
	let searchQuery = $state('');
	let sortOption = $state('date_desc');

	// Group thumbnails into rows for VList
	let rows = $derived.by(() => {
		const result: FileThumb[][] = [];
		for (let i = 0; i < thumbnails.length; i += itemsPerRow) {
			result.push(thumbnails.slice(i, i + itemsPerRow));
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
		} else{
			itemsPerRow = 8; // desktop
		}
	}

	// Fetch initial results (first page)
	async function fetchInitialResults() {
		if (!tags) {
			loading = false;
			thumbnails = [];
			nextCursor = null;
			hasMore = false;
			fetchedCountRef = -1;
			return;
		}

		loading = true;
		error = null;
		thumbnails = [];
		nextCursor = null;
		hasMore = false;
		fetchedCountRef = -1;

		try {
			const response = await searchFiles(tags, currentSort);
			thumbnails = response.items;
			nextCursor = response.next_cursor;
			hasMore = response.has_more;
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred';
		} finally {
			loading = false;
		}
	}

	// Fetch more items for infinite scroll
	async function fetchMoreItems() {
		if (!tags || fetching || !hasMore || !nextCursor) {
			return;
		}

		fetching = true;

		try {
			const response = await searchFiles(tags, currentSort, nextCursor);
			thumbnails = [...thumbnails, ...response.items];
			nextCursor = response.next_cursor;
			hasMore = response.has_more;
		} catch (err) {
			console.error('Failed to fetch more items:', err);
		} finally {
			fetching = false;
		}
	}

	// Handle scroll events for infinite scrolling
	// Mimics React example: if (fetchedCountRef.current < count && ref.current.findItemIndex(ref.current.scrollOffset + ref.current.viewportSize) + 50 > count)
	async function handleScroll() {
		if (!vlistRef) return;
		
		const count = thumbnails.length;
		
		// Find the last visible row index and convert to item index
		// endRowIndex gives us which row is at the bottom, multiply by itemsPerRow to get approximate item index
		const endRowIndex = vlistRef.findEndIndex();
		const lastVisibleItemIndex = (endRowIndex + 1) * itemsPerRow; // +1 because we want items up to and including this row
		
		// Check if we should fetch more:
		// 1. fetchedCountRef < count (haven't fetched for current count yet)
		// 2. lastVisibleItemIndex >= count (at the end)
		if (fetchedCountRef < count && lastVisibleItemIndex >= count && hasMore && !fetching) {
			fetchedCountRef = count;
			await fetchMoreItems();
		}
	}

	// Open lightbox at specific index
	function openLightbox(index: number) {
		lightboxIndex = index;
		lightboxOpen = true;
	}

	// Handle search form submission
	function handleSearch(event: Event) {
		event.preventDefault();
		const query = searchQuery.trim();
		if (query) {
			// Check if parameters are the same as current URL
			if (query === tags && sortOption === currentSort) {
				fetchInitialResults();
			} else {
				goto(`/search?tags=${encodeURIComponent(query)}&sort=${sortOption}`);
			}
		}
	}

	// Handle sort change
	function handleSortChange() {
		if (searchQuery.trim()) {
			goto(`/search?tags=${encodeURIComponent(searchQuery.trim())}&sort=${sortOption}`);
		}
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
		thumbnails = thumbnails.filter(t => !deletedHashes.has(t.sha256_hash));
	}

	function handleBulkEdit(changes: { removedTags: Set<string> }) {
		const currentSearchTags = tags.split(' ').filter(t => t.trim());
		const hasConflict = currentSearchTags.some(t => changes.removedTags.has(t));

		if (hasConflict) {
			// Remove selected files from thumbnails as they no longer match the search
			thumbnails = thumbnails.filter(t => !selectedFiles.has(t.sha256_hash));
		}
		
		// Always clear selection and exit select mode
		selectedFiles = new Set();
		isSelectMode = false;
	}

	// Run on mount and when tags/sort change
	$effect(() => {
		searchQuery = tags;
		sortOption = currentSort;
		fetchInitialResults();
	});

	// Update items per row on window resize
	$effect(() => {
		if (typeof window === 'undefined') return;
		
		updateItemsPerRow();
		window.addEventListener('resize', updateItemsPerRow);
		
		return () => {
			window.removeEventListener('resize', updateItemsPerRow);
		};
	});
</script>

<svelte:head>
	<title>{tags ? `${tags} - BijutsuBase` : 'Search - BijutsuBase'}</title>
</svelte:head>

<div class="flex h-screen flex-col">
	<!-- Top Bar -->
	<div class="shrink-0 border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-zinc-900">
		<div class="mx-auto max-w-7xl px-4 py-4">
			<div class="flex items-center gap-4">
				<a
					href="/"
					class="shrink-0 text-lg font-bold text-gray-900 hover:text-primary-600 dark:text-white dark:hover:text-primary-400"
				>
					BijutsuBase
				</a>
				<form onsubmit={handleSearch} class="flex flex-1 gap-2">
					<SearchInput
						bind:value={searchQuery}
						placeholder="Enter space-separated tags..."
						class="flex-1"
						inputClass="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 placeholder-gray-500 
						focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-800 
						dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400"
					/>
					
					<SortDropdown
						bind:value={sortOption}
						onchange={handleSortChange}
					/>

					<button
						type="submit"
						class="rounded-lg bg-primary-600 px-6 py-2 text-sm font-semibold text-white hover:bg-primary-700 focus:outline-none 
						focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:bg-primary-500 dark:hover:bg-primary-600 dark:focus:ring-primary-400 dark:focus:ring-offset-gray-900"
					>
						Search
					</button>
				</form>
			</div>
		</div>
	</div>

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
		{#if !loading && !error && thumbnails.length === 0}
			<div class="flex flex-1 items-center justify-center">
				<p class="text-xl text-gray-600 dark:text-gray-400">
					{tags ? 'No results found' : 'Enter tags to search'}
				</p>
			</div>
		{/if}

		<!-- Results Grid with VList -->
		{#if !loading && !error && thumbnails.length > 0}
			<VList bind:this={vlistRef} data={rows} class="flex-1 min-h-0 lg:px-16 md:px-8" onscroll={handleScroll}>
				{#snippet children(row, rowIndex)}
					{#if rowIndex === 0}
						<div class="mb-2 pb-2 text-sm text-gray-600 dark:text-gray-400 pt-4">
							Found {thumbnails.length}{hasMore ? '+' : ''} {thumbnails.length === 1 ? 'result' : 'results'}
							for <span class="font-mono font-semibold">{tags}</span>
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
</div>

<!-- Lightbox -->
<Lightbox bind:isOpen={lightboxOpen} bind:currentIndex={lightboxIndex} files={thumbnails} />
