<script lang="ts">
	import { debounce } from '$lib/utils';
	import CreatePoolModal from '$lib/components/CreatePoolModal.svelte';
	import PoolGrid from '$lib/components/PoolGrid.svelte';
	import { type PoolResponse } from '$lib/api';
	import IconPlus from '~icons/mdi/plus';
	import IconSearch from '~icons/mdi/magnify';

	let inputValue = $state('');
	let query = $state('');
	let createPoolModalOpen = $state(false);
	let grid: ReturnType<typeof PoolGrid> | undefined = $state();

	const debouncedUpdate = debounce(() => {
		query = inputValue;
	}, 300);

	function handlePoolCreated(newPool: PoolResponse) {
		grid?.addPool(newPool);
	}
</script>

<div class="flex flex-1 flex-col overflow-hidden">
	<!-- Header -->
	<div class="flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-zinc-900">
		<div class="flex items-center gap-5 flex-1">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Pools</h1>
			
			<div class="flex-1 max-w-xs relative">
				<div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
					<IconSearch class="h-5 w-5 text-gray-400" />
				</div>
				<input
					type="text"
					class="block w-full rounded-lg border border-gray-300 bg-gray-50 p-2 pl-10 text-sm text-gray-900 focus:border-primary-500 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:focus:border-primary-500 dark:focus:ring-primary-500"
					placeholder="Search pools..."
					bind:value={inputValue}
					oninput={debouncedUpdate}
				/>
			</div>
		</div>

		<button
			onclick={() => (createPoolModalOpen = true)}
			class="flex shrink-0 items-center gap-2 rounded-lg bg-primary-600 p-2 font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:bg-primary-500 dark:hover:bg-primary-600 sm:px-4"
			aria-label="Create Pool"
		>
			<IconPlus class="h-5 w-5" />
			<span class="hidden sm:inline">Create Pool</span>
		</button>
	</div>

	<PoolGrid bind:this={grid} {query} />
</div>

<CreatePoolModal bind:isOpen={createPoolModalOpen} onPoolCreated={handlePoolCreated} />
