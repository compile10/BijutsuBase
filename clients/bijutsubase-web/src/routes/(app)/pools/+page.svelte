<script lang="ts">
	import { VList } from 'virtua/svelte';
	import type { VListHandle } from 'virtua/svelte';
	import { getPools, type PoolSimple, type PoolResponse } from '$lib/api';
	import CreatePoolModal from '$lib/components/CreatePoolModal.svelte';
	import IconPlus from '~icons/mdi/plus';
	import IconFolder from '~icons/mdi/folder-outline';

	let pools = $state<PoolSimple[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let fetching = $state(false);
	let hasMore = $state(true);
	let skip = $state(0);
	const limit = 50;

	let itemsPerRow = $state(6);
	let vlistRef: VListHandle | undefined = $state();
	let createPoolModalOpen = $state(false);

	// Group pools into rows for VList
	let rows = $derived.by(() => {
		const result: PoolSimple[][] = [];
		for (let i = 0; i < pools.length; i += itemsPerRow) {
			result.push(pools.slice(i, i + itemsPerRow));
		}
		return result;
	});

	// Calculate items per row based on window width
	function updateItemsPerRow() {
		if (typeof window === 'undefined') return;
		const width = window.innerWidth;
		if (width < 640) {
			itemsPerRow = 2; // mobile
		} else if (width < 768) {
			itemsPerRow = 3; // small tablet
		} else if (width < 1024) {
			itemsPerRow = 4; // tablet
		} else if (width < 1280) {
			itemsPerRow = 5; // laptop
		} else {
			itemsPerRow = 6; // desktop
		}
	}

	async function fetchInitialResults() {
		loading = true;
		error = null;
		pools = [];
		skip = 0;
		hasMore = true;

		try {
			const newPools = await getPools(0, limit);
			pools = newPools;
			if (newPools.length < limit) {
				hasMore = false;
			}
			skip += newPools.length;
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred';
		} finally {
			loading = false;
		}
	}

	async function fetchMoreItems() {
		if (fetching || !hasMore) return;

		fetching = true;
		try {
			const newPools = await getPools(skip, limit);
			
			if (newPools.length > 0) {
				pools = [...pools, ...newPools];
				skip += newPools.length;
			}

			if (newPools.length < limit) {
				hasMore = false;
			}
		} catch (err) {
			console.error('Failed to fetch more pools:', err);
		} finally {
			fetching = false;
		}
	}

	// Handle scroll events for infinite scrolling
	async function handleScroll() {
		if (!vlistRef) return;
		
		const count = pools.length;
		const endRowIndex = vlistRef.findEndIndex();
		const lastVisibleItemIndex = (endRowIndex + 1) * itemsPerRow;
		
		// Trigger when we're 2 rows away from end
		if (lastVisibleItemIndex >= count - (itemsPerRow * 2) && hasMore && !fetching) {
			await fetchMoreItems();
		}
	}

	function handlePoolCreated(newPool: PoolResponse) {
		// Add to the top of the list
		pools = [newPool, ...pools];
		skip += 1;
	}

	$effect(() => {
		if (typeof window === 'undefined') return;
		updateItemsPerRow();
		window.addEventListener('resize', updateItemsPerRow);
		return () => {
			window.removeEventListener('resize', updateItemsPerRow);
		};
	});

	$effect(() => {
		fetchInitialResults();
	});
</script>

<div class="flex flex-1 flex-col overflow-hidden">
	<!-- Header -->
	<div class="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-zinc-900">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Pools</h1>
		<button
			onclick={() => (createPoolModalOpen = true)}
			class="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:bg-primary-500 dark:hover:bg-primary-600"
		>
			<IconPlus class="h-5 w-5" />
			<span>Create Pool</span>
		</button>
	</div>

	<!-- Loading State -->
	{#if loading}
		<div class="flex flex-1 items-center justify-center">
			<div class="text-center">
				<div class="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600 dark:border-gray-600 dark:border-t-primary-400"></div>
				<p class="text-gray-600 dark:text-gray-400">Loading pools...</p>
			</div>
		</div>
	{/if}

	<!-- Error State -->
	{#if error}
		<div class="m-4 rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
			<p class="text-red-800 dark:text-red-400">Error: {error}</p>
		</div>
	{/if}

	<!-- Empty State -->
	{#if !loading && !error && pools.length === 0}
		<div class="flex flex-1 items-center justify-center">
			<div class="text-center text-gray-600 dark:text-gray-400">
				<IconFolder class="mx-auto mb-4 h-16 w-16 opacity-50" />
				<p class="text-xl font-medium">No pools found</p>
				<p class="mt-2 text-sm">Create a new pool to get started</p>
			</div>
		</div>
	{/if}

	<!-- Results Grid -->
	{#if !loading && !error && pools.length > 0}
		<VList bind:this={vlistRef} data={rows} class="flex-1 min-h-0 lg:px-16 md:px-8 px-4" onscroll={handleScroll}>
			{#snippet children(row, rowIndex)}
				{#if rowIndex === 0}
					<div class="pt-4"></div>
				{/if}
				<div
					class="grid gap-4 pb-4"
					style="grid-template-columns: repeat({itemsPerRow}, minmax(0, 1fr));"
				>
					{#each row as pool}
						<a
							href="/pools/{pool.id}"
							class="group relative flex flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm transition-all hover:-translate-y-1 hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
						>
							<!-- Thumbnail -->
							<div class="aspect-square w-full overflow-hidden bg-gray-100 dark:bg-gray-900">
								{#if pool.thumbnail_url}
									<img
										src={pool.thumbnail_url}
										alt={pool.name}
										class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
									/>
								{:else}
									<div class="flex h-full w-full items-center justify-center text-gray-300 dark:text-gray-600">
										<IconFolder class="h-16 w-16" />
									</div>
								{/if}
							</div>

							<!-- Info -->
							<div class="p-3">
								<h3 class="truncate text-sm font-semibold text-gray-900 dark:text-white" title={pool.name}>
									{pool.name}
								</h3>
								<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
									{pool.member_count} {pool.member_count === 1 ? 'item' : 'items'}
								</p>
							</div>
						</a>
					{/each}
				</div>
				
				<!-- Loading indicator at the end -->
				{#if rowIndex === rows.length - 1 && fetching && hasMore}
					<div class="flex justify-center py-8">
						<div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600 dark:border-gray-600 dark:border-t-primary-400"></div>
					</div>
				{/if}
			{/snippet}
		</VList>
	{/if}
</div>

<CreatePoolModal bind:isOpen={createPoolModalOpen} onPoolCreated={handlePoolCreated} />

