<script lang="ts">
	import { goto } from '$app/navigation';
	import SortDropdown from '$lib/components/SortDropdown.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import IconSearch from '~icons/mdi/magnify';

	let searchQuery = $state('');
	let sortOption = $state('date_desc');

	function handleSearch(event: Event) {
		event.preventDefault();
		if (searchQuery.trim()) {
			goto(`/search?tags=${encodeURIComponent(searchQuery.trim())}&sort=${sortOption}`);
		}
	}
</script>

<svelte:head>
	<title>BijutsuBase</title>
</svelte:head>

<!-- Added pt-16 to account for fixed buttons on mobile -->
<div class="flex min-h-screen items-center justify-center px-4 pt-16 pb-4">
	<div class="w-full max-w-2xl">
		<h1 class="mb-8 text-center text-4xl font-bold text-gray-900 dark:text-white">
			BijutsuBase
		</h1>
		<p class="mb-8 text-center text-lg text-gray-600 dark:text-gray-400">
			Search your anime fanart collection
		</p>
		
		<form onsubmit={handleSearch} class="flex gap-2">
			<SearchInput
				bind:value={searchQuery}
				placeholder="Enter tags..."
				class="flex-1 min-w-0"
				inputClass="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 placeholder-gray-500 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400"
			/>
			
			<div class="shrink-0">
				<SortDropdown
					bind:value={sortOption}
					class="py-3! h-full"
				/>
			</div>

			<button
				type="submit"
				class="shrink-0 rounded-lg bg-primary-600 px-3 py-3 font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 sm:px-6 dark:bg-primary-500 dark:hover:bg-primary-600 dark:focus:ring-primary-400 dark:focus:ring-offset-gray-900"
				aria-label="Search"
			>
				<span class="hidden sm:inline">Search</span>
				<IconSearch class="h-6 w-6 sm:hidden" />
			</button>
		</form>
	</div>
</div>
