<script lang="ts">
	import { goto } from '$app/navigation';
	import VirtualCardGrid from '$lib/components/VirtualCardGrid.svelte';
	import { getCharacters, type Character } from '$lib/api';

	function normalizeCharacterTag(tag: string): string {
		return tag
			.split('_')
			.filter(Boolean)
			.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}

	function loadPage(skip: number, limit: number): Promise<Character[]> {
		return getCharacters(skip, limit);
	}

	function onCharacterClick(character: Character) {
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
		getTitle={(c) => normalizeCharacterTag((c as Character).name)}
		getImageUrl={(c) => (c as Character).thumbnail_url}
		onItemClick={(c) => onCharacterClick(c as Character)}
		loadingText="Loading characters..."
		emptyTitle="No characters found"
	/>
</div>

