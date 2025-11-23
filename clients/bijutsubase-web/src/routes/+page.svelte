<script lang="ts">
	import { goto } from '$app/navigation';
	import SortDropdown from '$lib/components/SortDropdown.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';

	let searchQuery = $state('');
	let sortOption = $state('date_desc');

	function handleSearch(event: Event) {
		event.preventDefault();
		if (searchQuery.trim()) {
			goto(`/search?tags=${encodeURIComponent(searchQuery.trim())}&sort=${sortOption}`);
		}
	}
</script>

<div class="flex min-h-screen items-center justify-center px-4">
	<div class="w-full max-w-2xl">
		<h1 class="mb-8 text-center text-4xl font-bold text-gray-900 dark:text-white">
			BijutsuBase
		</h1>
		<p class="mb-8 text-center text-lg text-gray-600 dark:text-gray-400">
			Search your anime fanart collection
		</p>
		
		<form onsubmit={handleSearch} class="flex flex-col gap-2 sm:flex-row">
			<SearchInput
				bind:value={searchQuery}
				placeholder="Enter space-separated tags..."
				class="flex-1"
				inputClass="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 placeholder-gray-500 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400"
			/>
			
			<SortDropdown
				bind:value={sortOption}
				class="py-3!"
			/>

			<button
				type="submit"
				class="rounded-lg bg-primary-600 px-6 py-3 font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:bg-primary-500 dark:hover:bg-primary-600 dark:focus:ring-primary-400 dark:focus:ring-offset-gray-900"
			>
				Search
			</button>
		</form>
	</div>
</div>
