<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import SortDropdown from '$lib/components/SortDropdown.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import SearchGrid from '$lib/components/SearchGrid.svelte';
	import IconSearch from '~icons/mdi/magnify';

	// Get tags and sort from URL params
	let tags = $derived(page.url.searchParams.get('tags') || '');
	let currentSort = $derived(page.url.searchParams.get('sort') || 'date_desc');
	
	let searchQuery = $state('');
	let sortOption = $state('date_desc');
	let grid: ReturnType<typeof SearchGrid> | undefined = $state();

	// Handle search form submission
	function handleSearch(event: Event) {
		event.preventDefault();
		const query = searchQuery.trim();
		if (query) {
			// Check if parameters are the same as current URL
			if (query === tags && sortOption === currentSort) {
				grid?.refresh();
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

	// Run on mount and when tags/sort change
	$effect(() => {
		searchQuery = tags;
		sortOption = currentSort;
	});
</script>

<svelte:head>
	<title>{tags ? `${tags} - BijutsuBase` : 'Search - BijutsuBase'}</title>
</svelte:head>

<div class="flex h-screen flex-col">
	<!-- Top Bar -->
	<div class="shrink-0 border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-zinc-900">
		<div class="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
				<!-- Logo Link - Centered on mobile to sit between fixed buttons -->
				<div class="flex h-10 items-center justify-center sm:h-auto sm:justify-start">
					<a
						href="/"
						class="text-lg font-bold text-gray-900 hover:text-primary-600 dark:text-white dark:hover:text-primary-400"
					>
						BijutsuBase
					</a>
				</div>

				<!-- Search Form -->
				<form onsubmit={handleSearch} class="flex flex-1 gap-2">
					<SearchInput
						bind:value={searchQuery}
						placeholder="Enter tags..."
						class="flex-1 min-w-0"
						inputClass="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 placeholder-gray-500 
						focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-800 
						dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400"
					/>
					
					<div class="shrink-0">
						<SortDropdown
							bind:value={sortOption}
							onchange={handleSortChange}
						/>
					</div>

					<button
						type="submit"
						class="shrink-0 rounded-lg bg-primary-600 px-3 py-2 text-sm font-semibold text-white hover:bg-primary-700 focus:outline-none 
						focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 sm:px-6 dark:bg-primary-500 dark:hover:bg-primary-600 dark:focus:ring-primary-400 dark:focus:ring-offset-gray-900"
						aria-label="Search"
					>
						<span class="hidden sm:inline">Search</span>
						<IconSearch class="h-6 w-6 sm:hidden" />
					</button>
				</form>
			</div>
		</div>
	</div>

	<SearchGrid
		bind:this={grid}
		{tags}
		sort={currentSort}
	/>
</div>
