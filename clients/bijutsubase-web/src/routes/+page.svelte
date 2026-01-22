<script lang="ts">
	import { goto } from '$app/navigation';
	import SortDropdown from '$lib/components/SortDropdown.svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';
	import AccountMenu from '$lib/components/AccountMenu.svelte';
	import { getAppState } from '$lib/state.svelte';
	import { getAuthContext } from '$lib/auth.svelte';
	import IconSearch from '~icons/mdi/magnify';
	import IconMenu from '~icons/mdi/menu';
	import IconUpload from '~icons/mdi/image-plus';

	const appState = getAppState();
	const authState = getAuthContext();
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

<!-- Global Menu Button - fixed top left -->
<button
	onclick={() => (appState.isSidebarOpen = true)}
	class="fixed left-4 top-4 z-40 p-1.5 text-gray-700 transition-transform hover:scale-110 focus:outline-none sm:p-2 md:p-2 dark:text-gray-200"
	aria-label="Open menu"
>
	<IconMenu class="h-6 w-6 shadow-sm" />
</button>

<!-- Top Right Actions - fixed -->
<div class="fixed right-4 top-4 z-40 flex items-center gap-3">
	{#if authState.isAuthenticated}
		<button
			onclick={() => (appState.isUploadModalOpen = true)}
			class="rounded-full bg-primary-600 p-1.5 text-white shadow-lg transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 sm:p-2 md:p-2 dark:bg-primary-500 dark:hover:bg-primary-600"
			aria-label="Upload file"
		>
			<IconUpload class="h-4 w-4 sm:h-5 sm:w-5 md:h-6 md:w-6" />
		</button>
	{/if}
	<AccountMenu />
</div>

<div class="flex min-h-screen items-center justify-center px-4 pb-4">
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
