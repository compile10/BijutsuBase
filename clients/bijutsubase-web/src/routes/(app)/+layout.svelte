<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import SortDropdown from '$lib/components/SortDropdown.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import { getAppState } from '$lib/state.svelte';
	import IconSearch from '~icons/mdi/magnify';
	import IconMenu from '~icons/mdi/menu';
	import IconUpload from '~icons/mdi/image-plus';

	let { children } = $props();
	const appState = getAppState();

	// Get tags and sort from URL params
	let tags = $derived(page.url.searchParams.get('tags') || '');
	let currentSort = $derived(page.url.searchParams.get('sort') || 'date_desc');
	
	let searchQuery = $state('');
	let sortOption = $state('date_desc');

	// Handle search form submission
	function handleSearch(event: Event) {
		event.preventDefault();
		const query = searchQuery.trim();
		if (query) {
			goto(`/search?tags=${encodeURIComponent(query)}&sort=${sortOption}`);
		}
	}

	// Handle sort change
	function handleSortChange() {
		if (searchQuery.trim()) {
			goto(`/search?tags=${encodeURIComponent(searchQuery.trim())}&sort=${sortOption}`);
		}
	}

	// Sync URL params with local state
	$effect(() => {
		searchQuery = tags;
		sortOption = currentSort;
	});
</script>

<div class="flex h-screen flex-col">
	<!-- Top Bar -->
	<div class="shrink-0 border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-zinc-900">
		<div class="px-4 py-3 sm:px-6 lg:px-8">
			<div class="flex items-center justify-between gap-4">
				<!-- Left Side: Menu & Logo -->
				<div class="flex items-center gap-3 shrink-0">
					<button
						onclick={() => (appState.isSidebarOpen = true)}
						class="p-1.5 text-gray-700 transition-transform hover:scale-110 focus:outline-none dark:text-gray-200"
						aria-label="Open menu"
					>
						<IconMenu class="h-6 w-6" />
					</button>

					<a
						href="/"
						class="text-lg font-bold text-gray-900 hover:text-primary-600 dark:text-white dark:hover:text-primary-400"
					>
						BijutsuBase
					</a>
				</div>

				<!-- Center: Search Form -->
				<form onsubmit={handleSearch} class="flex max-w-2xl flex-1 gap-2">
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

				<!-- Right Side: Upload Button -->
				<div class="flex shrink-0 justify-end" style="width: 100px">
					<button
						onclick={() => (appState.isUploadModalOpen = true)}
						class="rounded-full bg-primary-600 p-2 text-white shadow-lg transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:bg-primary-500 dark:hover:bg-primary-600"
						aria-label="Upload file"
					>
						<IconUpload class="h-5 w-5" />
					</button>
				</div>
			</div>
		</div>
	</div>

	{@render children()}
</div>

<style>
	:global(body) {
		overflow: hidden;
	}
</style>

