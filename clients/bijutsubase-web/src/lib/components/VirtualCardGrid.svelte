<script lang="ts">
	import { VList } from 'virtua/svelte';
	import type { VListHandle } from 'virtua/svelte';
	import IconImageOffOutline from '~icons/mdi/image-off-outline';
	import { onMount } from 'svelte';

	type LoadPage<T> = (skip: number, limit: number) => Promise<T[]>;

	let {
		loadPage,
		getTitle,
		getImageUrl,
		getSubtitle,
		onItemClick,
		loadingText = 'Loading...',
		emptyTitle = 'No items found',
		emptySubtitle,
		limit = 50,
		containerClass = 'lg:px-16 lg:py-4 md:px-8 md:py-4 p-4'
	}: {
		loadPage: LoadPage<unknown>;
		getTitle: (item: unknown) => string;
		getImageUrl: (item: unknown) => string | null | undefined;
		getSubtitle?: (item: unknown) => string | null | undefined;
		onItemClick: (item: unknown) => void;
		loadingText?: string;
		emptyTitle?: string;
		emptySubtitle?: string;
		limit?: number;
		containerClass?: string;
	} = $props();

	let items = $state<unknown[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let fetching = $state(false);
	let hasMore = $state(true);
	let skip = $state(0);

	let itemsPerRow = $state(6);
	let vlistRef: VListHandle | undefined = $state();

	let rows = $derived.by(() => {
		const result: unknown[][] = [];
		for (let i = 0; i < items.length; i += itemsPerRow) {
			result.push(items.slice(i, i + itemsPerRow));
		}
		return result;
	});

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
		} else if (width < 3840) {
			itemsPerRow = 6; // desktop
		} else {
			itemsPerRow = 8; // 4k+
		}
	}

	export async function refresh() {
		await fetchInitialResults();
	}

	async function fetchInitialResults() {
		loading = true;
		error = null;
		items = [];
		skip = 0;
		hasMore = true;

		try {
			const newItems = await loadPage(0, limit);
			items = newItems;
			if (newItems.length < limit) {
				hasMore = false;
			}
			skip += newItems.length;
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
			const newItems = await loadPage(skip, limit);
			if (newItems.length > 0) {
				items = [...items, ...newItems];
				skip += newItems.length;
			}
			if (newItems.length < limit) {
				hasMore = false;
			}
		} catch (err) {
			console.error('Failed to fetch more items:', err);
		} finally {
			fetching = false;
		}
	}

	async function handleScroll() {
		if (!vlistRef) return;

		const count = items.length;
		const endRowIndex = vlistRef.findEndIndex();
		const lastVisibleItemIndex = (endRowIndex + 1) * itemsPerRow;

		// Trigger when we're 2 rows away from end
		if (lastVisibleItemIndex >= count - itemsPerRow * 2 && hasMore && !fetching) {
			await fetchMoreItems();
		}
	}

	onMount(() => {
		updateItemsPerRow();
	});

	$effect(() => {
		if (typeof window === 'undefined') return;
		window.addEventListener('resize', updateItemsPerRow);
		return () => {
			window.removeEventListener('resize', updateItemsPerRow);
		};
	});

	$effect(() => {
		// refetch when loader changes
		loadPage;
		fetchInitialResults();
	});
</script>

<div class="flex flex-1 flex-col overflow-hidden">
	{#if loading}
		<div class="flex flex-1 items-center justify-center">
			<div class="text-center">
				<div class="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600 dark:border-gray-600 dark:border-t-primary-400"></div>
				<p class="text-gray-600 dark:text-gray-400">{loadingText}</p>
			</div>
		</div>
	{/if}

	{#if error}
		<div class="m-4 rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
			<p class="text-red-800 dark:text-red-400">Error: {error}</p>
		</div>
	{/if}

	{#if !loading && !error && items.length === 0}
		<div class="flex flex-1 items-center justify-center">
			<div class="text-center text-gray-600 dark:text-gray-400">
				<IconImageOffOutline class="mx-auto mb-4 h-16 w-16 opacity-50" />
				<p class="text-xl font-medium">{emptyTitle}</p>
				{#if emptySubtitle}
					<p class="mt-2 text-sm">{emptySubtitle}</p>
				{/if}
			</div>
		</div>
	{/if}

	{#if !loading && !error && items.length > 0}
		<VList
			bind:this={vlistRef}
			data={rows}
			class={`flex-1 min-h-0 ${containerClass}`}
			onscroll={handleScroll}
		>
			{#snippet children(row, rowIndex)}
				<div class="grid gap-4 pb-4" style="grid-template-columns: repeat({itemsPerRow}, minmax(0, 1fr));">
					{#each row as item}
						{@const title = getTitle(item)}
						{@const img = getImageUrl(item)}
						<button
							onclick={() => onItemClick(item)}
							class="group relative flex flex-col overflow-hidden rounded-lg border border-gray-200 bg-white text-left shadow-sm transition-all hover:-translate-y-1 hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
						>
							<!-- Thumbnail -->
							<div class="aspect-square w-full overflow-hidden bg-gray-100 dark:bg-gray-900">
								{#if img}
									<img
										src={img}
										alt={title}
										class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
									/>
								{:else}
									<div class="flex h-full w-full items-center justify-center text-gray-300 dark:text-gray-600">
										<IconImageOffOutline class="h-16 w-16" />
									</div>
								{/if}
							</div>

							<!-- Info -->
							<div class="p-3">
								<h3 class="truncate text-sm font-semibold text-gray-900 dark:text-white" title={title}>
									{title}
								</h3>
								{#if getSubtitle}
									{@const subtitle = getSubtitle(item)}
									{#if subtitle}
										<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>
									{/if}
								{/if}
							</div>
						</button>
					{/each}
				</div>

				{#if rowIndex === rows.length - 1 && fetching && hasMore}
					<div class="flex justify-center py-8">
						<div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600 dark:border-gray-600 dark:border-t-primary-400"></div>
					</div>
				{/if}
			{/snippet}
		</VList>
	{/if}
</div>

