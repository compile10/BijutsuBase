<script lang="ts">
	import { goto } from '$app/navigation';
	import VirtualCardGrid from '$lib/components/VirtualCardGrid.svelte';
	import { getTagsByCategory, type TagBrowseItem } from '$lib/api';
	import { humanizeTag } from '$lib/utils';

	function loadPage(skip: number, limit: number): Promise<TagBrowseItem[]> {
		return getTagsByCategory('copyright', skip, limit);
	}

	function onCopyrightClick(copyright: TagBrowseItem) {
		goto(`/search?tags=${encodeURIComponent(copyright.name)}`);
	}
</script>

<svelte:head>
	<title>Copyright - BijutsuBase</title>
</svelte:head>

<div class="flex flex-1 flex-col overflow-hidden">
	<div class="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-zinc-900">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Copyright</h1>
	</div>

	<VirtualCardGrid
		loadPage={loadPage}
		getTitle={(c) => humanizeTag((c as TagBrowseItem).name)}
		getImageUrl={(c) => (c as TagBrowseItem).thumbnail_url}
		onItemClick={(c) => onCopyrightClick(c as TagBrowseItem)}
		loadingText="Loading copyright tags..."
		emptyTitle="No copyright tags found"
	/>
</div>
