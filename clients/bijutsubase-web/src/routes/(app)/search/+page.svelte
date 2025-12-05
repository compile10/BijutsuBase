<script lang="ts">
	import { page } from '$app/state';
	import SearchGrid from '$lib/components/SearchGrid.svelte';

	// Get tags and sort from URL params
	let tags = $derived(page.url.searchParams.get('tags') || '');
	let currentSort = $derived(page.url.searchParams.get('sort') || 'date_desc');
	let currentSeed = $derived(page.url.searchParams.get('seed') || undefined);
	
	let grid: ReturnType<typeof SearchGrid> | undefined = $state();
	
	// Expose refresh method for parent layout if needed
	export function refresh() {
		grid?.refresh();
	}
</script>

<svelte:head>
	<title>{tags ? `${tags} - BijutsuBase` : 'Search - BijutsuBase'}</title>
</svelte:head>

<SearchGrid
	bind:this={grid}
	{tags}
	sort={currentSort}
	seed={currentSeed}
/>
