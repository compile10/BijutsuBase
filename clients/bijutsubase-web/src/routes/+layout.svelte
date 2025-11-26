<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import UploadModal from '$lib/components/UploadModal.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import { getAppState } from '$lib/state.svelte';

	let { children } = $props();
	const appState = getAppState();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="min-h-screen">
	<!-- Sidebar -->
	<Sidebar bind:isOpen={appState.isSidebarOpen} />

	<!-- Upload Modal -->
	<UploadModal bind:isOpen={appState.isUploadModalOpen} />

	{@render children()}
</div>
