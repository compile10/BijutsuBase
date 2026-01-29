<script lang="ts">
	import WindowModal from './WindowModal.svelte';
	import SearchInput from './SearchInput.svelte';
	import SortDropdown from './SortDropdown.svelte';
	import IconSearch from '~icons/mdi/magnify';
	import IconClose from '~icons/mdi/close';

	let {
		isOpen = $bindable(false),
		searchQuery = $bindable(''),
		sortOption = $bindable('date_desc'),
		onSearch
	} = $props<{
		isOpen?: boolean;
		searchQuery?: string;
		sortOption?: string;
		onSearch?: (event: Event) => void;
	}>();

	function handleSubmit(event: Event) {
		event.preventDefault();
		if (onSearch) {
			onSearch(event);
		}
		isOpen = false;
	}

	function handleClose() {
		isOpen = false;
	}
</script>

<WindowModal bind:isOpen title="Search" maxWidth="max-w-lg" onClose={handleClose}>
	<div class="flex flex-col">
		<!-- Header -->
		<div class="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Search</h2>
			<button
				onclick={handleClose}
				class="rounded-lg p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200"
				aria-label="Close"
			>
				<IconClose class="h-5 w-5" />
			</button>
		</div>

		<!-- Content -->
		<form onsubmit={handleSubmit} class="flex flex-col gap-4 p-4">
			<div>
				<label for="search-input" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
					Tags
				</label>
				<SearchInput
					bind:value={searchQuery}
					placeholder="Enter tags..."
					class="w-full"
					inputClass="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder-gray-500 
					focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-800 
					dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-400 dark:focus:ring-primary-400"
				/>
			</div>

			<div>
				<label for="sort-option" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
					Sort by
				</label>
				<SortDropdown
					bind:value={sortOption}
					class="w-full"
				/>
			</div>

			<button
				type="submit"
				class="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:bg-primary-500 dark:hover:bg-primary-600 dark:focus:ring-primary-400 dark:focus:ring-offset-gray-900"
			>
				<IconSearch class="h-5 w-5" />
				Search
			</button>
		</form>
	</div>
</WindowModal>
