<script lang="ts">
	import SearchGrid from '$lib/components/SearchGrid.svelte';
</script>

<svelte:head>
	<title>Latest Images - BijutsuBase</title>
</svelte:head>

<SearchGrid
	tags=""
	sort="date_desc"
	allowEmptySearch={true}
	hideHeader={true}
/>
