<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { VList } from 'virtua/svelte';
	import { searchFiles, type FileThumb } from '$lib/api';
	import Lightbox from '$lib/components/Lightbox.svelte';
	import SortDropdown from '$lib/components/SortDropdown.svelte';

	let thumbnails = $state<FileThumb[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let itemsPerRow = $state(6);
	let lightboxOpen = $state(false);
	let lightboxIndex = $state(0);

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

	// Fetch thumbnails from API
	async function fetchThumbnails() {
		if (!tags) {
			loading = false;
			return;
		}

		loading = true;
		error = null;

		try {
			thumbnails = await searchFiles(tags, currentSort);
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred';
		} finally {
			loading = false;
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
		if (searchQuery.trim()) {
			goto(`/search?tags=${encodeURIComponent(searchQuery.trim())}&sort=${sortOption}`);
		}
	}

	// Handle sort change
	function handleSortChange() {
		if (searchQuery.trim()) {
			goto(`/search?tags=${encodeURIComponent(searchQuery.trim())}&sort=${sortOption}`);
		}
	}

	// Run on mount and when tags/sort change
	$effect(() => {
		searchQuery = tags;
		sortOption = currentSort;
		fetchThumbnails();
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

<div class="min-h-screen">
	<!-- Top Bar -->
	<div class="sticky top-0 z-10 border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-zinc-900">
		<div class="mx-auto max-w-7xl px-4 py-4">
			<div class="flex items-center gap-4">
				<a
					href="/"
					class="shrink-0 text-lg font-bold text-gray-900 hover:text-primary-600 dark:text-white dark:hover:text-primary-400"
				>
					BijutsuBase
				</a>
				<form onsubmit={handleSearch} class="flex flex-1 gap-2">
					<input
						type="text"
						bind:value={searchQuery}
						placeholder="Enter space-separated tags..."
						class="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 placeholder-gray-500 
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

	<div class="mx-auto max-w-screen-2xl p-4">

		<!-- Loading State -->
		{#if loading}
			<div class="flex items-center justify-center py-12">
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
			<div class="py-12 text-center">
				<p class="text-xl text-gray-600 dark:text-gray-400">
					{tags ? 'No results found' : 'Enter tags to search'}
				</p>
			</div>
		{/if}

		<!-- Results Grid with VList -->
		{#if !loading && !error && thumbnails.length > 0}
			<div class="mb-4 text-sm text-gray-600 dark:text-gray-400">
				Found {thumbnails.length} {thumbnails.length === 1 ? 'result' : 'results'}
				for <span class="font-mono font-semibold">{tags}</span>
			</div>
			<!-- overflow-y: visible; contain: none may effect performance. but it's necessary to avoid annimation overflow cutoff-->
			<VList data={rows} style="height: calc(100vh - 200px); overflow-y: visible; contain: none;">
				{#snippet children(row, rowIndex)}
					<div
						class="grid gap-3 pb-4"
						style="grid-template-columns: repeat({itemsPerRow}, minmax(0, 1fr));"
					>
						{#each row as thumb, colIndex}
							<button
								onclick={() => openLightbox(rowIndex * itemsPerRow + colIndex)}
								class="group relative aspect-square overflow-hidden rounded-lg border border-gray-200 bg-gray-100 transition-transform hover:scale-105 dark:border-gray-700 dark:bg-gray-800"
							>
								<img
									src={thumb.thumbnail_url}
									alt="Thumbnail"
									class="h-full w-full object-cover"
									loading="lazy"
								/>
								<div class="absolute inset-0 bg-black opacity-0 transition-opacity group-hover:opacity-10"></div>
							</button>
						{/each}
					</div>
				{/snippet}
			</VList>
		{/if}
	</div>
</div>

<!-- Lightbox -->
<Lightbox bind:isOpen={lightboxOpen} bind:currentIndex={lightboxIndex} files={thumbnails} />
