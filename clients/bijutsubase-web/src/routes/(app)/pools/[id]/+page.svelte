<script lang="ts">
	import { page } from '$app/state';
	import SearchGrid from '$lib/components/SearchGrid.svelte';
	import AddToPoolByHashModal from '$lib/components/AddToPoolByHashModal.svelte';
	import { getPool, type PoolResponse } from '$lib/api';
	import IconChevronLeft from '~icons/mdi/chevron-left';

	const poolId = $derived(page.params.id ?? '');

	let pool = $state<PoolResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let addByHashOpen = $state(false);
	let grid: ReturnType<typeof SearchGrid> | undefined = $state();

	async function loadPool() {
		if (!poolId) {
			error = 'Pool not found';
			loading = false;
			return;
		}

		loading = true;
		error = null;

		try {
			pool = await getPool(poolId);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load pool';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		loadPool();
	});
</script>

<svelte:head>
	<title>{pool ? `${pool.name} - BijutsuBase` : 'Pool - BijutsuBase'}</title>
</svelte:head>

<div class="flex flex-1 flex-col overflow-hidden">
	<div class="border-b border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-zinc-900">
		<div class="mx-auto flex w-full max-w-5xl flex-col gap-4">
			<div class="flex items-center gap-3 text-sm text-primary-600 dark:text-primary-400">
				<a href="/pools" class="flex items-center gap-1 hover:underline">
					<IconChevronLeft class="h-5 w-5" />
					<span>Back to Pools</span>
				</a>
			</div>
			<div>
				<p class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
					{pool?.category}
				</p>
				<h1 class="text-2xl font-bold text-gray-900 dark:text-white">
					{pool?.name ?? 'Pool'}
				</h1>
				{#if pool?.description}
					<p class="mt-2 text-sm text-gray-600 dark:text-gray-300">
						{pool.description}
					</p>
				{/if}
				{#if pool}
					<div class="mt-3 flex flex-wrap items-center gap-4">
						<p class="text-xs text-gray-500 dark:text-gray-400">
							{pool.member_count} {pool.member_count === 1 ? 'item' : 'items'}
						</p>

						<button
							class="rounded-lg bg-primary-600 px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-primary-500 dark:hover:bg-primary-600"
							onclick={() => (addByHashOpen = true)}
						>
							Add image by hash
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>

	{#if loading}
		<div class="flex flex-1 items-center justify-center">
			<div class="text-center">
				<div class="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600 dark:border-gray-600 dark:border-t-primary-400"></div>
				<p class="text-gray-600 dark:text-gray-400">Loading pool...</p>
			</div>
		</div>
	{:else if error}
		<div class="m-4 rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
			<p class="text-red-800 dark:text-red-400">Error: {error}</p>
			<button
				class="mt-3 rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-primary-500 dark:hover:bg-primary-600"
				onclick={loadPool}
			>
				Try again
			</button>
		</div>
	{:else if pool}
		<div class="flex flex-1 flex-col">
			<SearchGrid
				bind:this={grid}
				tags={`pool:${poolId}`}
				sort="pool_order"
				allowEmptySearch={true}
				hideHeader={true}
				poolId={poolId}
			/>
		</div>
	{/if}
</div>

<AddToPoolByHashModal
	bind:isOpen={addByHashOpen}
	poolId={poolId}
	onFilesAdded={(updatedPool) => {
		pool = updatedPool;
		grid?.refresh();
	}}
/>

