<script lang="ts">
	import { debounce } from '$lib/utils';
	import type { PoolSimple } from '$lib/api';
	import WindowModal from './WindowModal.svelte';
	import PoolGrid from './PoolGrid.svelte';
	import IconClose from '~icons/mdi/close';
	import IconSearch from '~icons/mdi/magnify';

	let {
		isOpen = $bindable(false),
		onPoolSelected
	}: {
		isOpen?: boolean;
		onPoolSelected?: (pool: PoolSimple) => void;
	} = $props();

	let inputValue = $state('');
	let query = $state('');

	const debouncedUpdate = debounce(() => {
		query = inputValue;
	}, 300);

	function handleClose() {
		isOpen = false;
		inputValue = '';
		query = '';
	}

	function handleSelect(pool: PoolSimple) {
		onPoolSelected?.(pool);
		handleClose();
	}
</script>

<WindowModal bind:isOpen title="Select Pool" maxWidth="max-w-4xl" onClose={handleClose}>
	<!-- Header -->
	<div class="flex shrink-0 items-center justify-between border-b border-gray-200 p-4 dark:border-gray-700">
		<div class="flex flex-1 items-center gap-4">
			<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
				Add to Pool
			</h2>
			
			<div class="relative flex-1 max-w-sm">
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
			onclick={handleClose}
			class="ml-4 rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:hover:bg-gray-700 dark:hover:text-gray-300"
			aria-label="Close modal"
		>
			<IconClose class="h-6 w-6" />
		</button>
	</div>

	<!-- Content -->
	<div class="flex h-[60vh] flex-col overflow-hidden bg-gray-50 dark:bg-gray-900">
		<PoolGrid 
			{query} 
			hideHeader 
			isModal 
			onSelect={handleSelect}
		/>
	</div>
</WindowModal>

