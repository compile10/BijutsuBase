<script lang="ts">
	import { goto } from '$app/navigation';
	import VirtualCardGrid from '$lib/components/VirtualCardGrid.svelte';
	import { getTagsByCategory, type TagBrowseItem } from '$lib/api';
	import { getSettingsContext } from '$lib/settings.svelte';
	import { humanizeTag } from '$lib/utils';

	const settings = getSettingsContext();

	// Create a reactive loadPage function that captures current maxRating
	let loadPage = $derived((skip: number, limit: number): Promise<TagBrowseItem[]> => {
		return getTagsByCategory('character', skip, limit, settings.maxRating ?? undefined);
	});

	function onCharacterClick(character: TagBrowseItem) {
		goto(`/search?tags=${encodeURIComponent(character.name)}`);
	}
</script>

<svelte:head>
	<title>Characters - BijutsuBase</title>
</svelte:head>

<div class="flex flex-1 flex-col overflow-hidden">
	<div class="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-zinc-900">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Characters</h1>
	</div>

	<VirtualCardGrid
		loadPage={loadPage}
		getTitle={(c) => humanizeTag((c as TagBrowseItem).name)}
		getImageUrl={(c) => (c as TagBrowseItem).thumbnail_url}
		onItemClick={(c) => onCharacterClick(c as TagBrowseItem)}
		loadingText="Loading characters..."
		emptyTitle="No characters found"
	/>
</div>

